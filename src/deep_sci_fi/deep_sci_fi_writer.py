import os
import asyncio
from datetime import datetime
from langchain_core.prompts import ChatPromptTemplate
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END

from typing_extensions import TypedDict, Annotated
from typing import Optional
import operator
from langchain_core.messages import HumanMessage, AIMessage
from open_deep_research.deep_researcher import deep_researcher
from co_scientist.co_scientist import co_scientist
from co_scientist.configuration import CoScientistConfiguration, UseCase
from langchain_core.runnables import RunnableConfig

from deep_sci_fi.prompts import (
    # Future-native workflow prompts
    PARSE_USER_INPUT_PROMPT,
    LIGHT_FUTURE_CONTEXT_PROMPT,
    STORY_RESEARCH_TARGETING_PROMPT,
    RESEARCH_QUERY_GENERATION_PROMPT,
    RESEARCH_INTEGRATION_PROMPT,
    EXPAND_LOGLINE_TO_STORY_PROMPT,
    OUTLINE_PREP_PROMPT,
    ANALYZE_OUTLINE_PROMPT,
    REWRITE_OUTLINE_PROMPT,
    SCENE_BRIEF_PROMPT,
    SCIENTIFICALLY_GROUNDED_CHAPTER_PROMPT,
    CHAPTER_CRITIQUE_PROMPT,
    CHAPTER_REWRITE_PROMPT,
    SCIENTIFIC_COHERENCE_PROMPT,
    CHAPTER_IMPORTANCE_CLASSIFIER,
    DYNAMIC_RESEARCH_DETECTION_PROMPT,
    ENHANCED_SCIENTIFIC_COHERENCE_PROMPT,
)

def parse_and_limit_research_queries(research_queries_content: str, max_queries: int = 5) -> list[str]:
    """Parse research queries from content and strictly limit to prevent research explosion."""
    queries = []
    lines = research_queries_content.split('\n')
    current_query = ""
    
    for line in lines:
        line_stripped = line.strip()
        # Look for patterns like "QUERY:" or "QUERY 1:" or "QUERY X:"
        if (line_stripped.startswith("QUERY:") or 
            (line_stripped.startswith("QUERY ") and ":" in line_stripped)):
            
            # Save previous query if we have one
            if current_query and len(queries) < max_queries:
                queries.append(current_query.strip())
            if len(queries) >= max_queries:
                break
            
            # Extract the query after the colon
            colon_idx = line_stripped.find(":")
            if colon_idx != -1:
                current_query = line_stripped[colon_idx + 1:].strip()
            
        elif current_query and line_stripped and not line_stripped.startswith("PURPOSE:"):
            # Continue building the current query (skip PURPOSE lines)
            current_query += " " + line_stripped
    
    # Add the last query if we haven't hit the limit
    if current_query and len(queries) < max_queries:
        queries.append(current_query.strip())
    
    # Ensure we never exceed the limit
    return queries[:max_queries]


async def _run_deep_researcher(research_query: str, config: RunnableConfig) -> str:
    """Helper to run the deep_researcher subgraph and correctly parse its final output."""
    subgraph_config = config.copy()
    subgraph_config["configurable"].update({
        "research_model": ModelConfig.get_model_string("world_research"),
        "summarization_model": ModelConfig.get_model_string("world_research"),
        "compression_model": ModelConfig.get_model_string("world_research"),
        "compression_model_max_tokens": 8000,
        "final_report_model": ModelConfig.get_model_string("world_research"),
        "allow_clarification": False,
        "search_api": "tavily",
    })

    final_state = {}
    async for chunk in deep_researcher.astream(
        {"messages": [HumanMessage(content=research_query)]},
        subgraph_config,
        stream_mode="values"
    ):
        final_state = chunk
    
    result = final_state.get("final_report", "")
    if not result.strip():
        raise RuntimeError(f"DEEP RESEARCH FAILURE: No report generated for query: {research_query}")
    
    return result


def save_output(output_dir: str, filename: str, content: str):
    """Saves content to a markdown file in the specified output directory."""
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, filename), "w") as f:
        f.write(content)

# AgentState with clear field definitions
class AgentState(TypedDict):
    # Core workflow inputs
    user_input: Optional[str]
    output_dir: Optional[str]
    target_year: Optional[int]
    human_condition: Optional[str]
    constraint: Optional[str]
    tone: Optional[str]
    setting: Optional[str]
    light_future_context: Optional[str]
    story_seed_options: Optional[list]  # Generated logline options for user selection
    user_story_selection: Optional[int]  # User's selected option number (1-based index)
    selected_story_concept: Optional[str]  # Final expanded story concept from selected logline
    research_targets: Optional[str]
    research_queries: Optional[list]  # List of parsed research queries
    research_findings: Optional[str]
    refined_story: Optional[str]  # Research-integrated story from direct integration
    # New outline workflow fields
    outline_prep_materials: Optional[str]
    winning_outline: Optional[str]
    analysis_feedback: Optional[str]
    revised_outline: Optional[str]
    first_chapter: Optional[str]
    previous_chapters: Optional[list]  # List of completed chapters
    # Enhanced modular chapter writing loop fields
    current_chapter_number: Optional[int]
    target_chapters_count: Optional[int]
    current_scene_brief: Optional[str]
    current_chapter_draft: Optional[str]
    current_critique_feedback: Optional[str]
    current_quality_rating: Optional[str]
    current_chapter_importance: Optional[str]  # STANDARD or KEY
    coherence_issues_log: Optional[list]
    enhanced_process_used: Optional[bool]
    coherence_checks_performed: Optional[int]
    # Enhanced coherence tracking
    coherence_tracking: Optional[dict]  # Scientific consistency tracking
    original_research_summary: Optional[str]  # For dynamic research updates

def get_state_values_with_defaults(state: AgentState):
    """Get target_year and human_condition with fallback defaults"""
    target_year = state.get("target_year") or (state.get("starting_year", 2024) + 60)
    human_condition = state.get("human_condition") or "exploration of human resilience and adaptation"
    return target_year, human_condition

# === Flexible Model Configuration System ===

class ModelProvider:
    """Model provider configuration with thinking mode support."""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google_vertexai"
    
class ModelConfig:
    """Centralized model configuration with thinking mode and provider flexibility."""
    
    # === Provider-Specific Model Mappings ===
    MODELS = {
        ModelProvider.ANTHROPIC: {
            # Claude models with thinking capabilities
            "sonnet_4": "anthropic:claude-sonnet-4-20250514",
            "opus_4": "anthropic:claude-opus-4-1-20250805", 
            "sonnet_3_5": "anthropic:claude-3-5-sonnet-20241022",
            "haiku_3_5": "anthropic:claude-3-5-haiku-20241022"
        },
        ModelProvider.OPENAI: {
            # OpenAI models (o3 supports thinking, o1 has built-in reasoning)
            "o3": "openai:o3-2025-04-16",
            "o3_mini": "openai:o3-mini-2025-04-16", 
            "o1": "openai:o1-2024-12-17",
            "gpt5": "openai:gpt-5-2025-08-07",
            "gpt4": "openai:o3-2025-04-16",
            "gpt4_mini": "openai:o3-mini-2025-04-16"
        },
        ModelProvider.GOOGLE: {
            # Google models
            "gemini_2_flash": "google_vertexai:gemini-2.0-flash",
            "gemini_2_pro": "google_vertexai:gemini-2.0-pro"
        }
    }
    
    # === Use Case Model Assignments ===
    USE_CASE_MODELS = {
        # Creative narrative tasks - OpenAI GPT-5 for reasoning-driven creativity
        "general_creative": {
            "provider": ModelProvider.OPENAI,
            "model": "gpt5", 
            "thinking": False,  # GPT-5 has advanced reasoning capabilities
            "temperature": 1,  # Maximum creativity
            "max_tokens": 8000
        },
        
        # Chapter writing/rewriting - Claude Opus 4 with thinking for highest quality prose
        "chapter_writing": {
            "provider": ModelProvider.ANTHROPIC,
            "model": "opus_4",
            "thinking": True, 
            "temperature": 0.9,
            "max_tokens": 8000
        },
        
        # World research - OpenAI O3 for advanced reasoning
        "world_research": {
            "provider": ModelProvider.OPENAI,
            "model": "o3",
            "thinking": False,  # O3 has internal reasoning, doesn't need explicit thinking
            "temperature": 0.7,
            "max_tokens": 8000
        },
    }
    
    @classmethod
    def get_model_string(cls, use_case: str) -> str:
        """Get the full model string for a use case."""
        config = cls.USE_CASE_MODELS.get(use_case)
        if not config:
            # Fallback to general creative
            config = cls.USE_CASE_MODELS["general_creative"]
            
        provider = config["provider"]
        model_key = config["model"]
        return cls.MODELS[provider][model_key]
    
    @classmethod
    def get_model_params(cls, use_case: str) -> dict:
        """Get model parameters for a use case."""
        config = cls.USE_CASE_MODELS.get(use_case, cls.USE_CASE_MODELS["general_creative"])
        return {
            "temperature": config.get("temperature", 0.8),
            "max_tokens": config.get("max_tokens", 8000)
        }
    
    @classmethod
    def supports_thinking(cls, use_case: str) -> bool:
        """Check if a use case should use thinking mode."""
        config = cls.USE_CASE_MODELS.get(use_case, cls.USE_CASE_MODELS["general_creative"])
        return config.get("thinking", False)
    
    @classmethod
    def create_model_instance(cls, use_case: str, **override_params):
        """Create a model instance for a specific use case with optional parameter overrides."""
        model_string = cls.get_model_string(use_case)
        params = cls.get_model_params(use_case)
        
        # Apply any parameter overrides
        params.update(override_params)
        
        # Add thinking mode support for Anthropic models if enabled
        if cls.supports_thinking(use_case) and model_string.startswith("anthropic:"):
            # Note: Thinking mode no longer requires the beta header as of 2025
            # The feature is now available through the standard API
            pass
            
        return init_chat_model(model_string, **params).with_retry()

# === Legacy Model Configuration ===
model_config = {
    "research_model": ModelConfig.get_model_string("world_research"),
    "writing_model": ModelConfig.get_model_string("chapter_writing"), 
    "general_model": ModelConfig.get_model_string("general_creative"),
    "save_intermediate_results": True,
}

def reset_deep_sci_fi_models():
    """Reset model instances to prevent context bleeding between runs."""
    global writing_model, general_model
    
    writing_model = ModelConfig.create_model_instance("chapter_writing")
    general_model = ModelConfig.create_model_instance("general_creative")
    
    print("🔄 Reset deep_sci_fi models for fresh creative generation")
    print(f"  📝 Writing model: {ModelConfig.get_model_string('chapter_writing')} (thinking: {ModelConfig.supports_thinking('chapter_writing')})")
    print(f"  🎯 General model: {ModelConfig.get_model_string('general_creative')} (thinking: {ModelConfig.supports_thinking('general_creative')})")

def comprehensive_deep_sci_fi_session_reset():
    """Enhanced session reset for deep_sci_fi that addresses multiple layers of context bleeding."""
    import gc
    import os
    import random
    import time
    import uuid
    
    print("🔄 Starting comprehensive deep_sci_fi session reset...")
    
    # 1. Reset model instances using new flexible system
    reset_deep_sci_fi_models()
    
    # 2. Force garbage collection to clear lingering objects
    gc.collect()
    print("  ✅ Forced garbage collection")
    
    # 3. Reset random seeds with fresh entropy
    session_entropy = int(time.time() * 1000000) % (2**32 - 1)
    random.seed(session_entropy)
    try:
        import numpy as np
        np.random.seed(session_entropy)
    except ImportError:
        pass
    print(f"  ✅ Reset random seeds with entropy: {session_entropy}")
    
    # 4. Clear session-related environment variables
    session_vars_to_reset = [
        'LANGCHAIN_SESSION_ID', 
        'OPENAI_SESSION_ID',
        'ANTHROPIC_SESSION_ID',
        'DEEP_SCI_FI_PREVIOUS_RUN'
    ]
    for var in session_vars_to_reset:
        if var in os.environ:
            del os.environ[var]
            print(f"  ✅ Cleared environment variable: {var}")
    
    # 5. Set unique session identifier to prevent cross-session correlation
    unique_session_id = f"deep_sci_fi_{uuid.uuid4().hex[:8]}_{int(time.time())}"
    os.environ['DEEP_SCI_FI_SESSION_ID'] = unique_session_id
    print(f"  ✅ Set unique session ID: {unique_session_id}")
    
    print(f"🎉 Session reset complete with session ID: {unique_session_id}")
    return unique_session_id

# Initialize the models with new flexible system
writing_model = ModelConfig.create_model_instance("chapter_writing")
general_model = ModelConfig.create_model_instance("general_creative")


# === FUTURE-NATIVE WORKFLOW FUNCTIONS ===

async def parse_and_complete_user_input(state: AgentState, config: RunnableConfig):
    """Step 1: Parse user input and fill in missing parameters"""
    print("--- Parsing User Input and Completing Parameters ---")
    
    # Comprehensive session reset to prevent all forms of context bleeding
    session_id = comprehensive_deep_sci_fi_session_reset()
    
    run_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_dir = os.path.join("output", run_timestamp)
    starting_year = datetime.now().year
    
    user_input = state["user_input"]
    
    # Use general model to parse and complete user input
    prompt = ChatPromptTemplate.from_template(PARSE_USER_INPUT_PROMPT)
    response = general_model.invoke(prompt.format(user_input=user_input))
    
    content = response.content
    save_output(output_dir, "01_parsed_user_input.md", content)
    
    # Parse the structured response
    lines = content.strip().split('\n')
    parsed_params = {}
    
    for line in lines:
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            
            if key == "TARGET_YEAR":
                try:
                    parsed_params["target_year"] = int(value)
                except ValueError:
                    parsed_params["target_year"] = starting_year + 60  # Default fallback
            elif key == "HUMAN_CONDITION":
                parsed_params["human_condition"] = value
            elif key == "TECHNOLOGY_CONTEXT":
                parsed_params["technology_context"] = value
            elif key == "CONSTRAINT":
                parsed_params["constraint"] = value
            elif key == "TONE":
                parsed_params["tone"] = value
            elif key == "SETTING":
                parsed_params["setting"] = value
    
    # Save the parsed parameters
    params_content = (
        f"# Parsed Parameters from User Input\n\n"
        f"**Original Input:** {user_input}\n\n"
        f"**Extracted Parameters:**\n"
        f"- **Target Year:** {parsed_params.get('target_year', 'Not specified')}\n"
        f"- **Human Condition Theme:** {parsed_params.get('human_condition', 'Not specified')}\n"
        f"- **Technology Context:** {parsed_params.get('technology_context', 'Not specified')}\n"
        f"- **Constraint:** {parsed_params.get('constraint', 'Not specified')}\n"
        f"- **Tone:** {parsed_params.get('tone', 'Not specified')}\n"
        f"- **Setting:** {parsed_params.get('setting', 'Not specified')}\n\n"
        f"**Raw Model Response:**\n"
        f"{content}\n"
    )
    
    save_output(output_dir, "01_parsed_parameters.md", params_content)
    
    # Ensure critical parameters have fallback defaults
    if "target_year" not in parsed_params:
        parsed_params["target_year"] = starting_year + 60
    if "human_condition" not in parsed_params:
        parsed_params["human_condition"] = "exploration of human resilience and adaptation"
    
    print(f"--- User Input Parsed Successfully ---")
    print(f"Target Year: {parsed_params.get('target_year')}")
    print(f"Human Condition: {parsed_params.get('human_condition')}")
    
    return {
        "output_dir": output_dir,
        "starting_year": starting_year,
        "loop_count": 0,
        "messages": [],
        "user_input": user_input,  # Preserve full user prompt
        **parsed_params
    }


async def generate_light_future_context(state: AgentState, config: RunnableConfig):
    """Step 2: Generate minimal future context for story seeding"""
    if not (output_dir := state.get("output_dir")):
        raise ValueError("Required state for generating light future context is missing.")
    
    # Get target_year and human_condition with fallback defaults
    target_year, human_condition = get_state_values_with_defaults(state)
    
    print("--- Generating Light Future Context ---")
    
    technology_context = state.get("technology_context", "")
    
    # Use general model to generate light future context
    prompt = ChatPromptTemplate.from_template(LIGHT_FUTURE_CONTEXT_PROMPT)
    response = general_model.invoke(prompt.format(
        original_user_request=state.get('user_input', ''),
        target_year=target_year,
        human_condition=human_condition,
        technology_context=technology_context
    ))
    
    content = response.content
    save_output(output_dir, "02_light_future_context.md", content)
    
    print(f"--- Light Future Context Generated for {target_year} ---")
    
    return {"light_future_context": content}


async def generate_competitive_loglines(state: AgentState, config: RunnableConfig):
    """Step 3: Generate competitive loglines using Co-Scientist competition"""
    if not (output_dir := state.get("output_dir")) or not (light_future_context := state.get("light_future_context")):
        raise ValueError("Required state for generating competitive loglines is missing.")
    
    # Get values with fallback defaults
    target_year, human_condition = get_state_values_with_defaults(state)
    constraint = state.get("constraint") or "technological advancement"
    tone = state.get("tone") or "thoughtful and immersive"
    setting = state.get("setting") or "near-future Earth"
    
    print("--- Generating Competitive Loglines using Co-Scientist Competition ---")
    
    # Use co_scientist for competitive logline development
    newline = "\n"
    context_text = f"Original User Request: {state.get('user_input', '')}{newline}{newline}Human Condition: {human_condition}{newline}Future Context: {light_future_context}"
    co_scientist_input = CoScientistConfiguration.create_input_state(
        use_case=UseCase.COMPETITIVE_LOGLINES,
        context=context_text,
        target_year=target_year,
        constraint=constraint,
        tone=tone,
        setting=setting,
        human_condition=human_condition,
        light_future_context=light_future_context
    )
    
    # Configure co_scientist for creative competition
    subgraph_config = config.copy()
    subgraph_config["configurable"].update({
        "research_model": ModelConfig.get_model_string("general_creative"),
        "general_model": ModelConfig.get_model_string("general_creative"),
        "use_case": "competitive_loglines",
        "process_depth": "standard",
        "population_scale": "light",
        "use_deep_researcher": False,
        "save_intermediate_results": True,
        "output_dir": output_dir,
        "phase": "competitive_loglines"
    })
    
    # Run co_scientist competition
    co_scientist_result = await co_scientist.ainvoke(co_scientist_input, subgraph_config)
    
    # Save detailed competition results
    detailed_results = format_detailed_competition_results(co_scientist_result)
    save_output(output_dir, "03_competitive_loglines_competition_details.md", detailed_results)
    
    # Save direction winners with metadata
    direction_winners = co_scientist_result.get("direction_winners", [])
    
    if direction_winners:
        for i, winner in enumerate(direction_winners, 1):
            winner_details = format_co_scientist_winner_details(winner, f"loglines_approach_{i}")
            save_output(output_dir, f"03_loglines_approach_{i}_full.md", winner_details)
        
        # Format options for user selection - show as 3 batches of 3 loglines
        formatted_options = format_direction_winners_for_selection(direction_winners, co_scientist_result.get("competition_summary", ""), target_year, human_condition)
        save_output(output_dir, "03_loglines_options.md", formatted_options)
        
        print("--- Co-Scientist Competitive Loglines Competition Complete ---")
        print(f"--- Generated {len(direction_winners)} direction winners with 3 loglines each ---")
        
        return {"story_seed_options": direction_winners}  # Return direction winners with their loglines
    else:
        raise RuntimeError("Co-scientist competitive loglines competition failed to produce direction winners.")


async def user_story_selection(state: AgentState, config: RunnableConfig):
    """Step 3.5: Process user's numbered logline selection and expand to story concept"""
    if not (output_dir := state.get("output_dir")) or not (story_seed_options := state.get("story_seed_options")) or not (user_selection_number := state.get("user_story_selection")):
        raise ValueError("Required state for user story selection is missing.")
    
    print(f"--- Processing User Logline Selection: Option #{user_selection_number} ---")
    
    # Get target_year for parsing
    target_year, _ = get_state_values_with_defaults(state)
    
    # Extract all loglines from all direction winners into a numbered list
    all_loglines = []
    for winner in story_seed_options:
        approach_name = winner.get('research_direction', 'Unknown Approach')
        core_assumption = winner.get('core_assumption', 'No assumption available')
        scenario_content = winner.get('scenario_content', '')
        
        # Parse loglines from this winner's content
        if "## Top 3 Selected" in scenario_content:
            top_3_section = scenario_content.split("## Top 3 Selected")[1]
            lines = top_3_section.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line and ('In ' + str(target_year) in line) and len(line.strip()) > 50:
                    logline_text = line.strip('123.- ').strip()
                    all_loglines.append({
                        'logline': logline_text,
                        'approach': approach_name,
                        'assumption': core_assumption
                    })
        else:
            # Fallback: search in full content
            lines = scenario_content.split('\n')
            for line in lines:
                if 'In ' + str(target_year) in line and len(line.strip()) > 50:
                    logline_text = line.strip('123.- ').strip()
                    all_loglines.append({
                        'logline': logline_text,
                        'approach': approach_name,
                        'assumption': core_assumption
                    })
    
    # Validate selection number
    if user_selection_number < 1 or user_selection_number > len(all_loglines):
        raise ValueError(f"Invalid selection number {user_selection_number}. Must be between 1 and {len(all_loglines)}.")
    
    # Get the selected logline (convert to 0-based index)
    selected_logline_data = all_loglines[user_selection_number - 1]
    
    # Save the user-selected logline
    logline_info = f"**Selected Logline #{user_selection_number}:** {selected_logline_data['logline']}\n\n**From Approach:** {selected_logline_data['approach']}\n\n**Creative Philosophy:** {selected_logline_data['assumption']}"
    save_output(output_dir, "03_selected_logline.md", logline_info)
    
    print(f"--- User Selected Logline #{user_selection_number} from {selected_logline_data['approach']} Approach ---")
    
    # Now expand the selected logline into a full story concept
    expanded_story_concept = await expand_logline_to_story_concept(state, config, selected_logline_data)
    
    # Save the expanded story concept
    save_output(output_dir, "03_selected_story_concept.md", expanded_story_concept)
    
    return {"selected_story_concept": expanded_story_concept}


async def expand_logline_to_story_concept(state: AgentState, config: RunnableConfig, selected_logline_data: dict) -> str:
    """Expand selected individual logline into a full story concept"""
    if not (light_future_context := state.get("light_future_context")):
        raise ValueError("Required state for expanding logline to story concept is missing.")
    
    # Get target_year and human_condition with fallback defaults
    target_year, human_condition = get_state_values_with_defaults(state)
    
    print("--- Expanding Selected Logline to Full Story Concept ---")
    
    # Extract the logline details
    selected_logline = selected_logline_data.get('logline', '')
    approach_name = selected_logline_data.get('approach', 'Unknown')
    core_assumption = selected_logline_data.get('assumption', '')
    
    # Use general model to expand logline into full story concept
    prompt = ChatPromptTemplate.from_template(EXPAND_LOGLINE_TO_STORY_PROMPT)
    response = general_model.invoke(prompt.format(
        approach_name=approach_name,
        core_assumption=core_assumption,
        loglines_content=f"Selected Logline: {selected_logline}",
        selected_logline=selected_logline,
        target_year=target_year,
        human_condition=human_condition,
        light_future_context=light_future_context,
        original_user_request=state.get('user_input', ''),
        constraint=state.get('constraint', ''),
        tone=state.get('tone', ''),
        setting=state.get('setting', '')
    ))
    
    content = response.content
    print("--- Individual Logline Expansion to Story Concept Complete ---")
    
    return content


async def identify_story_research_targets(state: AgentState, config: RunnableConfig):
    """Step 4: Identify specific research needs based on selected story"""
    if not (output_dir := state.get("output_dir")) or not (selected_story_concept := state.get("selected_story_concept")):
        raise ValueError("Required state for identifying research targets is missing.")
    
    # Get target_year and human_condition with fallback defaults
    target_year, human_condition = get_state_values_with_defaults(state)
    
    print("--- Identifying Story Research Targets ---")
    
    # Use general model to analyze story and identify research targets
    prompt = ChatPromptTemplate.from_template(STORY_RESEARCH_TARGETING_PROMPT)
    response = general_model.invoke(prompt.format(
        selected_story_concept=selected_story_concept,
        target_year=target_year,
        human_condition=human_condition
    ))
    
    content = response.content
    save_output(output_dir, "04_research_targets.md", content)
    
    print("--- Research Targets Identified ---")
    
    return {"research_targets": content}


async def generate_research_queries(state: AgentState, config: RunnableConfig):
    """Step 5a: Generate specific research queries from research targets"""
    if not (output_dir := state.get("output_dir")) or not (research_targets := state.get("research_targets")) or not (selected_story_concept := state.get("selected_story_concept")):
        raise ValueError("Required state for generating research queries is missing.")
    
    # Get target_year with fallback default
    target_year = state.get("target_year") or (state.get("starting_year", 2024) + 60)
    
    print("--- Generating Research Queries ---")
    
    # Use general model to generate research queries
    prompt = ChatPromptTemplate.from_template(RESEARCH_QUERY_GENERATION_PROMPT)
    response = general_model.invoke(prompt.format(
        research_targets=research_targets,
        story_concept=selected_story_concept,
        target_year=target_year
    ))
    
    research_queries_content = response.content
    save_output(output_dir, "05_research_queries.md", research_queries_content)
    
    # Parse and strictly limit queries to prevent research explosion
    print(f"--- Parsing research queries from {len(research_queries_content)} characters of content ---")
    queries = parse_and_limit_research_queries(research_queries_content, max_queries=5)
    
    print(f"--- Generated {len(queries)} focused research queries (strict limit: 5 max) ---")
    for i, query in enumerate(queries, 1):
        print(f"  Query {i}: {query[:80]}...")
    
    # Check if we have any valid queries
    if not queries:
        print(f"❌ PARSING FAILURE - Raw content preview:")
        print(f"First 1000 chars: {research_queries_content[:1000]}")
        raise ValueError(f"RESEARCH QUERY GENERATION FAILURE: No valid research queries were parsed from LLM response. Raw content: {research_queries_content[:500]}...")
    
    return {"research_queries": queries}


async def conduct_deep_research(state: AgentState, config: RunnableConfig):
    """Step 5b: Execute the generated research queries using deep researcher"""
    if not (output_dir := state.get("output_dir")) or not (research_queries := state.get("research_queries")):
        raise ValueError("Required state for conducting deep research is missing.")
    
    queries = research_queries
    print(f"--- Conducting Deep Research on {len(queries)} queries ---")
    
    # Conduct research for each query using deep researcher IN PARALLEL
    async def research_single_query(i, query):
        """Research a single query and return formatted result"""
        print(f"--- Starting Research Query {i}: {query[:100]}... ---")
        
        try:
            research_result = await _run_deep_researcher(query, config)
            newline = "\n"
            research_entry = f"## Research Query {i}: {query}{newline}{newline}{research_result}{newline}{newline}"
            save_output(output_dir, f"05_research_result_{i}.md", research_result)
            print(f"--- Completed Research Query {i} ---")
            return research_entry
        except Exception as e:
            print(f"❌ RESEARCH QUERY {i} FAILED: {e}")
            # Re-raise the exception to fail loud and clear
            raise RuntimeError(f"Research query {i} failed: {query[:100]}... Error: {e}")
    
    # Use the already parsed and limited queries
    limited_queries = queries
    print(f"--- Running {len(limited_queries)} story-critical research queries in parallel ---")
    
    # Run all research queries in parallel
    research_tasks = [
        research_single_query(i, query) 
        for i, query in enumerate(limited_queries, 1)
    ]
    
    # This will raise an exception if any research query fails (fail fast and loud)
    all_research_findings = await asyncio.gather(*research_tasks)
    
    # Combine all research findings
    research_findings = "\n".join(all_research_findings)
    
    # Validate that we got meaningful research results
    if not research_findings.strip():
        raise RuntimeError("RESEARCH FAILURE: All research queries returned empty results")
    
    if len(research_findings.strip()) < 100:
        raise RuntimeError(f"RESEARCH FAILURE: Research results too short ({len(research_findings)} chars). Content: {research_findings[:200]}...")
    
    save_output(output_dir, "05_combined_research_findings.md", research_findings)
    
    print(f"✅ Targeted Deep Research Complete - {len(all_research_findings)} queries researched successfully")
    print(f"✅ Research findings: {len(research_findings)} characters of content")
    
    return {"research_findings": research_findings}


async def integrate_research_findings(state: AgentState, config: RunnableConfig):
    """Step 6: Systematically integrate research findings into story elements"""
    
    # Detailed error reporting for missing state
    missing_fields = []
    if not state.get("output_dir"):
        missing_fields.append("output_dir")
    if not state.get("selected_story_concept"):
        missing_fields.append("selected_story_concept")
    if not state.get("research_findings"):
        missing_fields.append("research_findings")
    
    if missing_fields:
        available_keys = list(state.keys())
        raise ValueError(f"RESEARCH INTEGRATION FAILURE: Missing required state fields: {missing_fields}. Available state keys: {available_keys}")
    
    # Extract validated state values
    output_dir = state["output_dir"]
    selected_story_concept = state["selected_story_concept"]
    research_findings = state["research_findings"]
    
    # Get target_year and human_condition with fallback defaults
    target_year, human_condition = get_state_values_with_defaults(state)
    
    print("--- Integrating Research Findings into Story ---")
    
    # Use general model with slightly lower temperature for accuracy-focused integration
    integration_model = ModelConfig.create_model_instance("general_creative", temperature=0.8)
    
    prompt = ChatPromptTemplate.from_template(RESEARCH_INTEGRATION_PROMPT)
    response = integration_model.invoke(prompt.format(
        selected_story_concept=selected_story_concept,
        research_findings=research_findings,
        target_year=target_year,
        human_condition=human_condition,
        original_user_request=state.get('user_input', '')
    ))
    
    research_integrated_story = response.content
    save_output(output_dir, "06_research_integrated_story.md", research_integrated_story)
    
    print("--- Research Integration Complete ---")
    print("--- Story enhanced with scientific grounding and accuracy ---")
    
    return {"refined_story": research_integrated_story}


# REMOVED: user_refinement_selection - no longer needed since Step 6 is direct integration


async def create_outline_prep_materials(state: AgentState, config: RunnableConfig):
    """Step 7: Generate foundational story elements for detailed outline creation"""
    
    if not (output_dir := state.get("output_dir")) or not (refined_story := state.get("refined_story")) or not (research_findings := state.get("research_findings")):
        # Provide detailed error about what's missing
        missing = []
        if not state.get("output_dir"):
            missing.append("output_dir")
        if not refined_story:
            missing.append("refined_story")
        if not state.get("research_findings"):
            missing.append("research_findings")
        
        raise ValueError(f"Required state for creating outline prep materials is missing: {missing}. Available keys: {list(state.keys())}")
    
    # Get target_year and human_condition with fallback defaults
    target_year, human_condition = get_state_values_with_defaults(state)
    
    print("--- Generating Outline Preparation Materials ---")
    
    # Use general model to create comprehensive prep materials
    prompt = ChatPromptTemplate.from_template(OUTLINE_PREP_PROMPT)
    response = general_model.invoke(prompt.format(
        refined_story=refined_story,
        target_year=target_year,
        human_condition=human_condition,
        research_findings=research_findings
    ))
    
    content = response.content
    save_output(output_dir, "07_outline_prep_materials.md", content)
    
    print("--- Outline Preparation Materials Complete ---")
    
    return {"outline_prep_materials": content, "refined_story": refined_story}


async def create_competitive_outline(state: AgentState, config: RunnableConfig):
    """Step 8: Generate optimized chapter-by-chapter outline through structural competition"""
    if not (output_dir := state.get("output_dir")) or not (outline_prep_materials := state.get("outline_prep_materials")) or not (refined_story := state.get("refined_story")) or not (research_findings := state.get("research_findings")):
        raise ValueError("Required state for creating competitive outline is missing.")
    
    # Get target_year and human_condition with fallback defaults
    target_year, human_condition = get_state_values_with_defaults(state)
    
    print("--- Creating Competitive Outline using Co-Scientist Competition ---")
    
    # Extract selected logline from earlier selection for context
    selected_logline = ""
    if story_seed_options := state.get("story_seed_options"):
        if user_selection := state.get("user_story_selection"):
            if 1 <= user_selection <= len(story_seed_options):
                selected_logline_data = story_seed_options[user_selection - 1]
                selected_logline = selected_logline_data.get("logline", "")
    
    # Use co_scientist for competitive outline creation
    newline = "\n"
    context_text = f"Outline Prep: {outline_prep_materials}"
    reference_text = f"Story: {refined_story}{newline}{newline}Research: {research_findings}"
    
    co_scientist_input = CoScientistConfiguration.create_input_state(
        use_case=UseCase.COMPETITIVE_OUTLINE,
        context=context_text,
        reference_material=reference_text,
        target_year=target_year,
        human_condition=human_condition,
        refined_story=refined_story,
        research_findings=research_findings,
        outline_prep_materials=outline_prep_materials,
        selected_logline=selected_logline
    )
    
    # Configure co_scientist for outline competition
    subgraph_config = config.copy()
    subgraph_config["configurable"].update({
        "research_model": ModelConfig.get_model_string("chapter_writing"),  # Use writing model for structural work
        "general_model": ModelConfig.get_model_string("chapter_writing"),   # Use writing model for structural work
        "use_case": "competitive_outline",
        "process_depth": "quick",  # Generation + tournament only
        "population_scale": "light",
        "use_deep_researcher": False,
        "save_intermediate_results": True,
        "output_dir": output_dir,
        "phase": "competitive_outline"
    })
    
    # Run co_scientist competition
    co_scientist_result = await co_scientist.ainvoke(co_scientist_input, subgraph_config)
    
    # Save detailed competition results
    detailed_results = format_detailed_competition_results(co_scientist_result)
    save_output(output_dir, "08_competitive_outline_competition_details.md", detailed_results)
    
    # Extract winning outline
    direction_winners = co_scientist_result.get("direction_winners", [])
    if direction_winners:
        # Get the top-ranked outline from competition
        winning_outline = direction_winners[0].get("scenario_content", "")
        
        # Save winning outline
        save_output(output_dir, "08_winning_outline.md", winning_outline)
        
        print("--- Co-Scientist Competitive Outline Competition Complete ---")
        print(f"--- Selected winning outline from {len(direction_winners)} competing approaches ---")
        
        return {"winning_outline": winning_outline}
    else:
        raise RuntimeError("Co-scientist competitive outline competition failed to produce direction winners.")


async def analyze_outline(state: AgentState, config: RunnableConfig):
    """Step 9: Developmental editing analysis of winning outline structure"""
    if not (output_dir := state.get("output_dir")) or not (winning_outline := state.get("winning_outline")) or not (refined_story := state.get("refined_story")):
        raise ValueError("Required state for analyzing outline is missing.")
    
    # Get target_year and human_condition with fallback defaults
    target_year, human_condition = get_state_values_with_defaults(state)
    
    print("--- Analyzing Outline Structure ---")
    
    # Use general model for developmental editing analysis
    prompt = ChatPromptTemplate.from_template(ANALYZE_OUTLINE_PROMPT)
    response = general_model.invoke(prompt.format(
        winning_outline=winning_outline,
        target_year=target_year,
        human_condition=human_condition,
        refined_story=refined_story
    ))
    
    content = response.content
    save_output(output_dir, "09_outline_analysis.md", content)
    
    print("--- Outline Analysis Complete ---")
    
    return {"analysis_feedback": content}


async def rewrite_outline(state: AgentState, config: RunnableConfig):
    """Step 10: Incorporate developmental feedback into improved outline"""
    if not (output_dir := state.get("output_dir")) or not (winning_outline := state.get("winning_outline")) or not (analysis_feedback := state.get("analysis_feedback")) or not (refined_story := state.get("refined_story")) or not (research_findings := state.get("research_findings")) or not (outline_prep_materials := state.get("outline_prep_materials")):
        raise ValueError("Required state for rewriting outline is missing.")
    
    # Get target_year and human_condition with fallback defaults
    target_year, human_condition = get_state_values_with_defaults(state)
    
    print("--- Rewriting Outline with Developmental Feedback ---")
    
    # Use writing model for final outline revision
    prompt = ChatPromptTemplate.from_template(REWRITE_OUTLINE_PROMPT)
    response = writing_model.invoke(prompt.format(
        winning_outline=winning_outline,
        analysis_feedback=analysis_feedback,
        target_year=target_year,
        human_condition=human_condition,
        refined_story=refined_story,
        research_findings=research_findings,
        outline_prep_materials=outline_prep_materials
    ))
    
    content = response.content
    save_output(output_dir, "10_revised_outline.md", content)
    
    print("--- Revised Outline Complete ---")
    
    return {"revised_outline": content}


async def write_first_chapter_competitive(state: AgentState, config: RunnableConfig):
    """Step 11: Establish tone, style, and world through opening chapter using CS"""
    if not (output_dir := state.get("output_dir")) or not (revised_outline := state.get("revised_outline")):
        raise ValueError("Required state for writing first chapter is missing.")
    
    # Get target_year, human_condition, and tone with fallback defaults
    target_year, human_condition = get_state_values_with_defaults(state)
    tone = state.get("tone") or "thoughtful and immersive"
    
    print("--- Writing First Chapter with Co-Scientist Competition ---")
    
    # Use co_scientist for competitive first chapter approaches
    co_scientist_input = CoScientistConfiguration.create_input_state(
        use_case=UseCase.FIRST_CHAPTER_WRITING,
        context=f"Original User Request: {state.get('user_input', '')}",
        reference_material=f"Revised Outline: {revised_outline}",
        target_year=target_year,
        tone=tone,
        human_condition=human_condition,
        revised_story=revised_outline  # Use outline as story reference
    )
    
    # Configure co_scientist for chapter writing competition
    subgraph_config = config.copy()
    subgraph_config["configurable"].update({
        "research_model": ModelConfig.get_model_string("chapter_writing"),
        "general_model": ModelConfig.get_model_string("chapter_writing"),
        "use_case": "first_chapter_writing",
        "process_depth": "standard",
        "population_scale": "light",
        "use_deep_researcher": False,
        "save_intermediate_results": True,
        "output_dir": output_dir,
        "phase": "first_chapter_writing"
    })
    
    # Run co_scientist competition
    co_scientist_result = await co_scientist.ainvoke(co_scientist_input, subgraph_config)
    
    # Save detailed competition results
    # Always save results for future-native workflow
    detailed_results = format_detailed_competition_results(co_scientist_result)
    save_output(output_dir, "11_first_chapter_competition_details.md", detailed_results)
    
    # Save direction winners with metadata
    direction_winners = co_scientist_result.get("direction_winners", [])
    for i, winner in enumerate(direction_winners, 1):
        winner_details = format_co_scientist_winner_details(winner, f"first_chapter_option_{i}")
        save_output(output_dir, f"11_first_chapter_option_{i}_full.md", winner_details)
    
    # Get the winning first chapter
    if direction_winners:
        winning_chapter = direction_winners[0].get("scenario_content", "")
        save_output(output_dir, "11_first_chapter.md", winning_chapter)
        
        # Analyze chapter style for continuation
        style_analysis = analyze_chapter_style(winning_chapter)
        save_output(output_dir, "11_first_chapter_style_analysis.md", style_analysis)
        
        print("--- Co-Scientist First Chapter Competition Complete ---")
        print(f"--- Selected winning chapter from {len(direction_winners)} approaches ---")
        
        return {
            "first_chapter": winning_chapter,
            "first_chapter_style_analysis": style_analysis,
            "previous_chapters": [winning_chapter],
            "total_chapters_written": 1
        }
    else:
        raise RuntimeError("Co-scientist first chapter competition failed to produce direction winners.")


# === MODULAR CHAPTER WRITING NODES ===

async def initialize_chapter_loop(state: AgentState, config: RunnableConfig):
    """Initialize the enhanced chapter writing loop"""
    if not (output_dir := state.get("output_dir")) or not (revised_outline := state.get("revised_outline")):
        raise ValueError("Required state for initializing chapter loop is missing.")
    
    # Get target_year with fallback default
    target_year = state.get("target_year") or (state.get("starting_year", 2024) + 60)
    
    print("--- Initializing Enhanced Chapter Writing Loop ---")
    
    # Parse the outline to determine actual chapter count
    target_chapters = parse_chapter_count_from_outline(revised_outline)
    print(f"--- Parsed {target_chapters} chapters from outline ---")
    
    # Initialize loop state
    current_chapter = state.get("total_chapters_written", 1) + 1  # Start after first chapter
    
    # Create research summary for dynamic updates
    research_findings = state.get("research_findings", "")
    research_summary = create_research_summary(research_findings)
    
    # Initialize coherence tracking
    coherence_tracking = {
        "character_knowledge": {},  # Character -> scientific knowledge level
        "tech_capabilities": {},    # Technology -> established capabilities  
        "world_rules": {},         # Scientific rules established in world
        "research_facts": {}       # Key facts from original research
    }
    
    return {
        "target_chapters_count": target_chapters,
        "current_chapter_number": current_chapter,
        "coherence_issues_log": [],
        "enhanced_process_used": True,
        "coherence_checks_performed": 0,
        "coherence_tracking": coherence_tracking,
        "original_research_summary": research_summary
    }


async def create_scene_brief_node(state: AgentState, config: RunnableConfig):
    """Node: Create detailed scene brief for current chapter and classify importance"""
    if not (output_dir := state.get("output_dir")) or not (current_chapter := state.get("current_chapter_number")):
        raise ValueError("Required state for creating scene brief is missing.")
    
    print(f"=== Creating Scene Brief for Chapter {current_chapter} ===")
    
    # Create scene brief using existing helper function
    scene_brief = await create_scene_brief(state, config, current_chapter)
    
    # Classify chapter importance
    importance_prompt = ChatPromptTemplate.from_template(CHAPTER_IMPORTANCE_CLASSIFIER)
    importance_response = general_model.invoke(importance_prompt.format(
        scene_brief=scene_brief,
        chapter_number=current_chapter
    ))
    
    importance_content = importance_response.content
    
    # Parse importance classification
    chapter_importance = "STANDARD"  # Default
    for line in importance_content.split('\n'):
        if line.startswith("CHAPTER_IMPORTANCE:"):
            classification = line.split(":", 1)[1].strip()
            if classification in ["STANDARD", "KEY"]:
                chapter_importance = classification
                break
    
    # Save scene brief with importance classification
    full_brief_content = f"{scene_brief}\n\n---\n\n## Chapter Importance Classification\n{importance_content}"
    save_output(output_dir, f"12a_chapter_{current_chapter:02d}_scene_brief.md", full_brief_content)
    
    print(f"--- Scene brief for Chapter {current_chapter} complete (Importance: {chapter_importance}) ---")
    
    return {
        "current_scene_brief": scene_brief,
        "current_chapter_importance": chapter_importance
    }


async def write_key_chapter_competitive(state: AgentState, config: RunnableConfig):
    """Step 12a-alt: Use CS competition for KEY chapters with high scientific complexity"""
    if not (output_dir := state.get("output_dir")) or not (current_chapter := state.get("current_chapter_number")) or not (scene_brief := state.get("current_scene_brief")):
        raise ValueError("Required state for competitive key chapter writing is missing.")
    
    print(f"=== Writing KEY Chapter {current_chapter} with Co-Scientist Competition ===")
    
    # Get target_year and human_condition with fallback defaults
    target_year, human_condition = get_state_values_with_defaults(state)
    
    # Use co_scientist for competitive key chapter writing
    co_scientist_input = CoScientistConfiguration.create_input_state(
        use_case=UseCase.KEY_CHAPTER_WRITING,
        context=f"Chapter {current_chapter} Scene Brief: {scene_brief}",
        reference_material=f"Previous Chapters Context: {get_chapter_context_for_writing(state)}",
        target_year=target_year,
        human_condition=human_condition,
        chapter_number=current_chapter,
        scene_brief=scene_brief,
        research_findings=state.get("research_findings", "")
    )
    
    # Configure co_scientist for key chapter competition
    subgraph_config = config.copy()
    subgraph_config["configurable"].update({
        "research_model": ModelConfig.get_model_string("chapter_writing"),
        "general_model": ModelConfig.get_model_string("chapter_writing"),
        "use_case": "key_chapter_writing",
        "process_depth": "standard",
        "population_scale": "medium",  # More variety for key chapters
        "use_deep_researcher": False,
        "save_intermediate_results": True,
        "output_dir": output_dir,
        "phase": f"key_chapter_{current_chapter}",
        "specialist_prompts": ["hard_sf_specialist", "science_educator", "narrative_physicist"]
    })
    
    # Run co_scientist competition
    co_scientist_result = await co_scientist.ainvoke(co_scientist_input, subgraph_config)
    
    # Save detailed competition results
    detailed_results = format_detailed_competition_results(co_scientist_result)
    save_output(output_dir, f"12b_chapter_{current_chapter:02d}_key_competition_details.md", detailed_results)
    
    # Get the winning chapter
    direction_winners = co_scientist_result.get("direction_winners", [])
    if direction_winners:
        winning_chapter = direction_winners[0].get("scenario_content", "")
        
        # Save winning chapter draft
        save_output(output_dir, f"12b_chapter_{current_chapter:02d}_draft.md", winning_chapter)
        
        print(f"--- KEY Chapter {current_chapter} competitive writing complete ---")
        print(f"--- Selected winning chapter from {len(direction_winners)} approaches ---")
        
        return {
            "current_chapter_draft": winning_chapter
        }
    else:
        raise RuntimeError(f"Co-scientist key chapter competition failed for Chapter {current_chapter}.")


def get_chapter_context_for_writing(state: AgentState) -> str:
    """Get recent chapter context for writing."""
    previous_chapters = state.get("previous_chapters", [])
    if not previous_chapters:
        return "No previous chapters available."
    
    # Get last 3 chapters for context
    recent_chapters = previous_chapters[-3:]
    return "\n\n---\n\n".join(recent_chapters)


async def write_chapter_draft_node(state: AgentState, config: RunnableConfig):
    """Node: Write chapter draft using scene brief"""
    if not (output_dir := state.get("output_dir")) or not (current_chapter := state.get("current_chapter_number")) or not (scene_brief := state.get("current_scene_brief")):
        raise ValueError("Required state for writing chapter draft is missing.")
    
    print(f"=== Writing Chapter {current_chapter} Draft ===")
    
    # Write chapter draft using existing helper function
    chapter_draft = await write_chapter_draft(state, config, current_chapter, scene_brief)
    
    # Save chapter draft
    save_output(output_dir, f"12b_chapter_{current_chapter:02d}_draft.md", chapter_draft)
    
    print(f"--- Chapter {current_chapter} draft complete ---")
    
    return {
        "current_chapter_draft": chapter_draft
    }


async def critique_chapter_node(state: AgentState, config: RunnableConfig):
    """Node: Critique chapter draft for quality assessment"""
    if not (output_dir := state.get("output_dir")) or not (current_chapter := state.get("current_chapter_number")) or not (chapter_draft := state.get("current_chapter_draft")) or not (scene_brief := state.get("current_scene_brief")):
        raise ValueError("Required state for critiquing chapter is missing.")
    
    print(f"=== Critiquing Chapter {current_chapter} ===")
    
    # Critique chapter using existing helper function
    critique_feedback, quality_rating = await critique_chapter(state, config, chapter_draft, scene_brief, current_chapter)
    
    # Save critique
    save_output(output_dir, f"12c_chapter_{current_chapter:02d}_critique.md", critique_feedback)
    
    print(f"--- Chapter {current_chapter} critique complete (Quality: {quality_rating}) ---")
    
    return {
        "current_critique_feedback": critique_feedback,
        "current_quality_rating": quality_rating
    }


async def conditional_rewrite_chapter_node(state: AgentState, config: RunnableConfig):
    """Node: Conditionally rewrite chapter based on quality rating"""
    if not (output_dir := state.get("output_dir")) or not (current_chapter := state.get("current_chapter_number")):
        raise ValueError("Required state for conditional rewrite is missing.")
    
    chapter_draft = state.get("current_chapter_draft", "")
    critique_feedback = state.get("current_critique_feedback", "")
    scene_brief = state.get("current_scene_brief", "")
    quality_rating = state.get("current_quality_rating", "GOOD")
    
    print(f"=== Processing Chapter {current_chapter} Rewrite (if needed) ===")
    
    # Conditionally rewrite using existing helper function
    final_chapter = await rewrite_chapter_if_needed(state, config, chapter_draft, critique_feedback, scene_brief, current_chapter, quality_rating)
    
    # Save final chapter
    save_output(output_dir, f"12_chapter_{current_chapter:02d}.md", final_chapter)
    
    # Update previous_chapters list
    previous_chapters = state.get("previous_chapters", [])
    previous_chapters.append(final_chapter)
    
    print(f"--- Chapter {current_chapter} finalized (Quality: {quality_rating}) ---")
    
    return {
        "previous_chapters": previous_chapters,
        "total_chapters_written": current_chapter
    }


async def check_if_more_chapters(state: AgentState, config: RunnableConfig):
    """Routing node: Check if more chapters need to be written"""
    current_chapter = state.get("current_chapter_number", 0)
    target_chapters = state.get("target_chapters_count", 0)
    
    print(f"--- Checking progress: Chapter {current_chapter} of {target_chapters} ---")
    
    if current_chapter < target_chapters:
        # More chapters to write - increment counter
        next_chapter = current_chapter + 1
        print(f"--- Moving to Chapter {next_chapter} ---")
        return {
            "current_chapter_number": next_chapter
        }
    else:
        # All chapters complete
        print(f"--- All {target_chapters} chapters complete ---")
        return {
            "book_compilation_complete": True
        }


async def dynamic_research_update_node(state: AgentState, config: RunnableConfig):
    """Step 12f: Dynamic Research Update - detect and research emerging scientific concepts"""
    if not (output_dir := state.get("output_dir")):
        raise ValueError("Output directory missing for dynamic research update.")
    
    current_chapter = state.get("current_chapter_number", 0)
    previous_chapters = state.get("previous_chapters", [])
    original_research_summary = state.get("original_research_summary", "")
    
    print(f"=== Dynamic Research Update Check for Chapter {current_chapter} ===")
    
    # Get recent chapters for analysis (last 1-3 chapters)
    recent_chapters = previous_chapters[-3:] if len(previous_chapters) >= 3 else previous_chapters
    if not recent_chapters:
        print("--- No chapters to analyze for dynamic research ---")
        return {}
    
    recent_chapters_text = "\n\n=== CHAPTER BREAK ===\n\n".join(recent_chapters)
    
    # Check for new scientific concepts
    detection_model = ModelConfig.create_model_instance("general_creative", temperature=0.7)
    detection_prompt = ChatPromptTemplate.from_template(DYNAMIC_RESEARCH_DETECTION_PROMPT)
    detection_response = detection_model.invoke(detection_prompt.format(
        original_research_summary=original_research_summary,
        recent_chapters=recent_chapters_text
    ))
    
    detection_content = detection_response.content
    save_output(output_dir, f"12f_chapter_{current_chapter:02d}_research_detection.md", detection_content)
    
    # Parse detection results
    new_concepts_detected = False
    research_queries = []
    
    for line in detection_content.split('\n'):
        if line.startswith("NEW_CONCEPTS_DETECTED:"):
            result = line.split(":", 1)[1].strip()
            new_concepts_detected = result.upper() == "YES"
        elif line.strip().startswith(("1.", "2.")) and "research query" in line.lower():
            query = line.split(".", 1)[1].strip()
            research_queries.append(query)
    
    if new_concepts_detected and research_queries:
        print(f"--- New concepts detected! Conducting mini-research on {len(research_queries)} queries ---")
        
        # Conduct mini-research using deep researcher
        mini_research_results = []
        for i, query in enumerate(research_queries[:2], 1):  # Limit to 2 queries
            try:
                print(f"--- Mini-research Query {i}: {query[:100]}... ---")
                research_result = await _run_deep_researcher(query, config)
                mini_research_results.append(f"## Mini-Research Query {i}: {query}\n\n{research_result}")
                save_output(output_dir, f"12f_mini_research_{current_chapter:02d}_{i}.md", research_result)
            except Exception as e:
                print(f"❌ Mini-research query {i} failed: {e}")
                mini_research_results.append(f"## Mini-Research Query {i} FAILED: {query}\n\nError: {e}")
        
        # Combine and save mini-research results
        combined_mini_research = "\n\n".join(mini_research_results)
        save_output(output_dir, f"12f_combined_mini_research_{current_chapter:02d}.md", combined_mini_research)
        
        print(f"--- Dynamic research update complete: {len(mini_research_results)} mini-research queries conducted ---")
        
        return {
            "mini_research_conducted": True,
            "mini_research_findings": combined_mini_research
        }
    else:
        print("--- No new concepts requiring research detected ---")
        return {
            "mini_research_conducted": False
        }


async def periodic_coherence_check_node(state: AgentState, config: RunnableConfig):
    """Node: Perform periodic scientific coherence check"""
    if not (output_dir := state.get("output_dir")):
        raise ValueError("Output directory missing for coherence check.")
    
    current_chapter = state.get("current_chapter_number", 0)
    previous_chapters = state.get("previous_chapters", [])
    coherence_checks_performed = state.get("coherence_checks_performed", 0)
    coherence_issues_log = state.get("coherence_issues_log", [])
    
    # Check if we should run coherence check (every 4 chapters or final chapter)
    target_chapters = state.get("target_chapters_count", 0)
    should_check = (current_chapter % 4 == 0) or (current_chapter == target_chapters)
    
    if not should_check:
        print(f"--- No coherence check needed for Chapter {current_chapter} ---")
        return {}
    
    print(f"=== Scientific Coherence Check for Chapters {max(1, current_chapter-3)}-{current_chapter} ===")
    
    # Get recent chapters batch
    recent_chapters_batch = previous_chapters[-4:] if len(previous_chapters) >= 4 else previous_chapters
    
    # Run enhanced coherence check
    coherence_analysis = await enhanced_periodic_coherence_check(state, config, recent_chapters_batch, current_chapter)
    
    # Save coherence analysis
    save_output(output_dir, f"12e_coherence_check_chapters_{max(1, current_chapter-3)}-{current_chapter}.md", coherence_analysis)
    
    # Parse coherence results and update tracking
    updated_tracking = parse_coherence_tracking_updates(coherence_analysis, state.get("coherence_tracking", {}))
    
    # Log any critical issues found
    if "MAJOR_ISSUES" in coherence_analysis:
        coherence_issues_log.append(f"Chapters {max(1, current_chapter-3)}-{current_chapter}: Major issues found")
        print(f"⚠️  Major scientific coherence issues detected - see coherence check file")
    elif "MINOR_ISSUES" in coherence_analysis:
        coherence_issues_log.append(f"Chapters {max(1, current_chapter-3)}-{current_chapter}: Minor issues noted")
        print(f"ℹ️  Minor scientific coherence issues noted - see coherence check file")
    
    print(f"--- Enhanced coherence check complete ---")
    
    return {
        "coherence_checks_performed": coherence_checks_performed + 1,
        "coherence_issues_log": coherence_issues_log,
        "coherence_tracking": updated_tracking
    }


async def compile_complete_novel(state: AgentState, config: RunnableConfig):
    """Node: Compile the complete novel with all chapters"""
    if not (output_dir := state.get("output_dir")):
        raise ValueError("Required state for compiling novel is missing.")
    
    # Get target_year with fallback default
    target_year = state.get("target_year") or (state.get("starting_year", 2024) + 60)
    
    print("=== Compiling Complete Novel ===")
    
    all_chapters = state.get("previous_chapters", [])
    target_chapters = state.get("target_chapters_count", 0)
    coherence_checks = state.get("coherence_checks_performed", 0)
    coherence_issues = state.get("coherence_issues_log", [])
    
    # Create complete novel compilation with enhanced metadata
    newline = '\n'
    complete_novel = (
        f"# Complete Novel{newline}{newline}"
        f"*Generated by Deep Sci-Fi Writer - Enhanced Modular Chapter Writing*{newline}"
        f"*Target Year: {target_year}*{newline}"
        f"*Human Condition Theme: {state.get('human_condition', '')}*{newline}"
        f"*Total Chapters: {len(all_chapters)}*{newline}"
        f"*Process: Modular Scene Brief → Draft → Critique → Rewrite → Coherence Check*{newline}{newline}"
        f"---{newline}{newline}"
    )
    
    for i, chapter in enumerate(all_chapters, 1):
        complete_novel += f"## Chapter {i}{newline}{newline}{chapter}{newline}{newline}---{newline}{newline}"
    
    complete_novel += (
        f"{newline}*Novel Complete*{newline}"
        f"*Enhanced Modular Writing Process Used*{newline}"
        f"*Scientific Coherence Checks: {coherence_checks} performed*{newline}"
        f"*Coherence Issues: {len(coherence_issues)} detected*{newline}"
        f"*Target Year: {target_year}*{newline}"
    )
    
    save_output(output_dir, "12_complete_novel.md", complete_novel)
    
    # Create process summary
    process_summary = (
        f"# Enhanced Modular Chapter Writing Process Summary{newline}{newline}"
        f"**Total Chapters Written:** {len(all_chapters)}{newline}"
        f"**Process Used:** Modular Scene Brief → Draft → Critique → Rewrite → Coherence Check{newline}"
        f"**Scientific Coherence Checks:** {coherence_checks} performed{newline}"
        f"**Quality Control:** All chapters critiqued and conditionally rewritten{newline}"
        f"**Modular Design:** Separate nodes for each process step{newline}{newline}"
        f"## Process Benefits{newline}"
        f"✅ Higher Quality - Scene brief + critique/rewrite process{newline}"
        f"✅ Style Consistency - Enhanced style checking{newline}"  
        f"✅ Scientific Grounding - Research context + coherence checking{newline}"
        f"✅ Efficiency - Targeted rewrites only when needed{newline}"
        f"✅ Continuity - Better context management and checking{newline}"
        f"✅ Observability - Separate nodes for each process step{newline}"
        f"✅ Modularity - Granular control and inspection capabilities{newline}"
    )
    
    save_output(output_dir, "12_enhanced_modular_process_summary.md", process_summary)
    
    print(f"🎉 Enhanced Modular Novel Complete: {len(all_chapters)} chapters written")
    print(f"📊 Process: Modular Scene Brief → Draft → Critique → Rewrite → Coherence Check")
    print(f"🔬 Scientific Coherence: {coherence_checks} checks performed")
    print(f"🔧 Modular Design: Separate nodes for granular control")
    
    return {
        "book_compilation_complete": True,
        "enhanced_process_used": True
    }


# === LEGACY FUNCTION (KEPT FOR REFERENCE) ===
async def write_remaining_chapters_legacy(state: AgentState, config: RunnableConfig):
    """Step 12: Enhanced chapter writing with scene brief → draft → critique → rewrite process"""
    if not (output_dir := state.get("output_dir")) or not (first_chapter_style_analysis := state.get("first_chapter_style_analysis")) or not (revised_outline := state.get("revised_outline")):
        raise ValueError("Required state for writing remaining chapters is missing.")
    
    # Get target_year with fallback default
    target_year = state.get("target_year") or (state.get("starting_year", 2024) + 60)
    
    print("--- Enhanced Chapter Writing Process: Scene Brief → Draft → Critique → Rewrite ---")
    
    # Get existing chapters (starting with first chapter)
    previous_chapters = state.get("previous_chapters", [])
    total_chapters_written = state.get("total_chapters_written", 1)
    
    # Parse the outline to determine actual chapter count
    target_chapters = parse_chapter_count_from_outline(revised_outline)
    print(f"--- Parsed {target_chapters} chapters from outline ---")
    
    written_chapters = []
    coherence_issues_log = []
    
    for chapter_num in range(total_chapters_written + 1, target_chapters + 1):
        print(f"\n=== ENHANCED CHAPTER WRITING: Chapter {chapter_num} ===")
        
        # Sub-Step 12a: Create Scene Brief
        print(f"--- Sub-Step 12a: Creating scene brief for Chapter {chapter_num} ---")
        scene_brief = await create_scene_brief(state, config, chapter_num)
        save_output(output_dir, f"12a_chapter_{chapter_num:02d}_scene_brief.md", scene_brief)
        
        # Sub-Step 12b: Write Chapter Draft
        print(f"--- Sub-Step 12b: Writing Chapter {chapter_num} draft ---")
        chapter_draft = await write_chapter_draft(state, config, chapter_num, scene_brief)
        save_output(output_dir, f"12b_chapter_{chapter_num:02d}_draft.md", chapter_draft)
        
        # Sub-Step 12c: Chapter Critique
        print(f"--- Sub-Step 12c: Critiquing Chapter {chapter_num} ---")
        critique_feedback, quality_rating = await critique_chapter(state, config, chapter_draft, scene_brief, chapter_num)
        save_output(output_dir, f"12c_chapter_{chapter_num:02d}_critique.md", critique_feedback)
        
        # Sub-Step 12d: Chapter Rewrite (if needed)
        print(f"--- Sub-Step 12d: Processing Chapter {chapter_num} rewrite (if needed) ---")
        final_chapter = await rewrite_chapter_if_needed(state, config, chapter_draft, critique_feedback, scene_brief, chapter_num, quality_rating)
        
        # Save final chapter
        save_output(output_dir, f"12_chapter_{chapter_num:02d}.md", final_chapter)
        
        # Add to written chapters list
        written_chapters.append(final_chapter)
        previous_chapters.append(final_chapter)
        
        print(f"--- Chapter {chapter_num} Complete (Quality: {quality_rating}) ---")
        
        # Sub-Step 12e: Periodic Scientific Coherence Check (every 3-4 chapters)
        if chapter_num % 4 == 0 or chapter_num == target_chapters:  # Every 4 chapters or last chapter
            print(f"--- Sub-Step 12e: Scientific Coherence Check for Chapters {max(1, chapter_num-3)}-{chapter_num} ---")
            recent_chapters_batch = previous_chapters[-4:] if len(previous_chapters) >= 4 else previous_chapters
            coherence_analysis = await periodic_coherence_check(state, config, recent_chapters_batch, chapter_num)
            save_output(output_dir, f"12e_coherence_check_chapters_{max(1, chapter_num-3)}-{chapter_num}.md", coherence_analysis)
            
            # Log any critical issues found
            if "CRITICAL:" in coherence_analysis:
                coherence_issues_log.append(f"Chapters {max(1, chapter_num-3)}-{chapter_num}: Issues found")
                print(f"⚠️  Scientific coherence issues detected in recent chapters - see coherence check file")
    
    # Compile complete novel
    all_chapters = previous_chapters  # Includes first chapter + all new chapters
    
    # Create complete novel compilation with enhanced metadata
    newline = '\n'
    complete_novel = (
        f"# Complete Novel{newline}{newline}"
        f"*Generated by Deep Sci-Fi Writer - Enhanced Chapter Writing Process*{newline}"
        f"*Target Year: {target_year}*{newline}"
        f"*Human Condition Theme: {state.get('human_condition', '')}*{newline}"
        f"*Total Chapters: {len(all_chapters)}*{newline}"
        f"*Process: Scene Brief → Draft → Critique → Rewrite*{newline}{newline}"
        f"---{newline}{newline}"
    )
    
    for i, chapter in enumerate(all_chapters, 1):
        complete_novel += f"## Chapter {i}{newline}{newline}{chapter}{newline}{newline}---{newline}{newline}"
    
    complete_novel += (
        f"{newline}*Novel Complete*{newline}"
        f"*Enhanced Writing Process Used*{newline}"
        f"*Scientific Coherence Checks: {len([f for f in coherence_issues_log]) if coherence_issues_log else 'No issues detected'}*{newline}"
        f"*Target Year: {target_year}*{newline}"
    )
    
    save_output(output_dir, "12_complete_novel.md", complete_novel)
    
    # Create process summary
    process_summary = (
        f"# Enhanced Chapter Writing Process Summary{newline}{newline}"
        f"**Total Chapters Written:** {len(written_chapters)}{newline}"
        f"**Process Used:** Scene Brief → Draft → Critique → Rewrite{newline}"
        f"**Scientific Coherence Checks:** {len([f for f in coherence_issues_log])} performed{newline}"
        f"**Quality Control:** All chapters critiqued and conditionally rewritten{newline}{newline}"
        f"## Process Benefits{newline}"
        f"✅ Higher Quality - Scene brief + critique/rewrite process{newline}"
        f"✅ Style Consistency - Enhanced style checking{newline}"  
        f"✅ Scientific Grounding - Research context + coherence checking{newline}"
        f"✅ Efficiency - Targeted rewrites only when needed{newline}"
        f"✅ Continuity - Better context management and checking{newline}"
    )
    
    save_output(output_dir, "12_enhanced_process_summary.md", process_summary)
    
    print(f"\n🎉 Enhanced Novel Complete: {len(all_chapters)} chapters written with quality control")
    print(f"📊 Process Summary: Scene Brief → Draft → Critique → Rewrite")
    print(f"🔬 Scientific Coherence: {len([f for f in coherence_issues_log])} checks performed")
    
    return {
        "previous_chapters": all_chapters,
        "total_chapters_written": len(all_chapters),
        "book_compilation_complete": True,
        "enhanced_process_used": True,
        "coherence_checks_performed": len([f for f in coherence_issues_log])
    }


# === ENHANCED CHAPTER WRITING HELPER FUNCTIONS ===

def extract_specific_chapter_from_outline(outline: str, chapter_number: int) -> str:
    """Extract the specific chapter details from the outline for scene brief creation."""
    import re
    
    # Look for the specific chapter in the outline
    chapter_patterns = [
        rf'### Chapter {chapter_number}[:\s].*?(?=### Chapter {chapter_number + 1}|$)',
        rf'## Chapter {chapter_number}[:\s].*?(?=## Chapter {chapter_number + 1}|$)',
        rf'Chapter {chapter_number}[:\s].*?(?=Chapter {chapter_number + 1}|$)',
    ]
    
    for pattern in chapter_patterns:
        match = re.search(pattern, outline, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(0).strip()
    
    # Fallback: return a section that mentions the chapter number
    fallback_pattern = rf'.*Chapter {chapter_number}.*'
    lines = outline.split('\n')
    for i, line in enumerate(lines):
        if re.search(fallback_pattern, line, re.IGNORECASE):
            # Return this line plus next 5 lines for context
            return '\n'.join(lines[i:i+6])
    
    return f"Chapter {chapter_number} details not found in outline"


def filter_research_for_chapter(research_findings: str, chapter_outline: str) -> str:
    """Filter research findings to only include content relevant to this specific chapter."""
    # For now, return a condensed version focused on the most relevant research
    # In a more sophisticated implementation, this could use semantic matching
    
    # Extract key terms from chapter outline
    chapter_lower = chapter_outline.lower()
    research_sections = research_findings.split('## Research Query')
    
    relevant_sections = []
    for section in research_sections:
        section_lower = section.lower()
        # Simple relevance check - look for overlapping terms
        if any(term in section_lower for term in ['technology', 'science', 'future', 'system']):
            relevant_sections.append(section)
    
    if relevant_sections:
        return '\n\n## Research Query'.join(relevant_sections[:3])  # Top 3 most relevant
    else:
        return research_findings[:2000]  # Truncate to manageable size


async def create_scene_brief(state: AgentState, config: RunnableConfig, chapter_number: int) -> str:
    """Sub-Step 12a: Create detailed scene brief before chapter writing"""
    revised_outline = state.get("revised_outline", "")
    previous_chapters = state.get("previous_chapters", [])
    research_findings = state.get("research_findings", "")
    first_chapter_style_analysis = state.get("first_chapter_style_analysis", "")
    target_year = state.get("target_year", "")
    
    # Extract specific chapter details from outline
    specific_chapter = extract_specific_chapter_from_outline(revised_outline, chapter_number)
    
    # Get last 3 chapters for context
    last_3_chapters = "\n\n---\n\n".join(previous_chapters[-3:]) if previous_chapters else ""
    
    prompt = ChatPromptTemplate.from_template(SCENE_BRIEF_PROMPT)
    response = general_model.invoke(prompt.format(
        chapter_number=chapter_number,
        specific_chapter_from_outline=specific_chapter,
        last_3_chapters=last_3_chapters,
        research_findings=research_findings,
        first_chapter_style_analysis=first_chapter_style_analysis,
        target_year=target_year
    ))
    
    return response.content


async def write_chapter_draft(state: AgentState, config: RunnableConfig, chapter_number: int, scene_brief: str) -> str:
    """Sub-Step 12b: Write chapter using scene brief and scientific context"""
    first_chapter_style_analysis = state.get("first_chapter_style_analysis", "")
    research_findings = state.get("research_findings", "")
    previous_chapters = state.get("previous_chapters", [])
    target_year = state.get("target_year", "")
    human_condition = state.get("human_condition", "")
    
    # Filter research for this specific chapter
    filtered_research = filter_research_for_chapter(research_findings, scene_brief)
    
    # Create summary of last 3 chapters for continuity
    last_3_chapters_summary = "\n\n---\n\n".join(previous_chapters[-3:]) if previous_chapters else ""
    
    prompt = ChatPromptTemplate.from_template(SCIENTIFICALLY_GROUNDED_CHAPTER_PROMPT)
    response = writing_model.invoke(prompt.format(
        chapter_number=chapter_number,
        scene_brief=scene_brief,
        first_chapter_style_analysis=first_chapter_style_analysis,
        filtered_research_for_chapter=filtered_research,
        last_3_chapters_summary=last_3_chapters_summary,
        target_year=target_year,
        human_condition=human_condition
    ))
    
    return response.content


async def critique_chapter(state: AgentState, config: RunnableConfig, chapter_content: str, scene_brief: str, chapter_number: int) -> tuple[str, str]:
    """Sub-Step 12c: Analyze chapter for improvements including scientific coherence"""
    research_findings = state.get("research_findings", "")
    first_chapter_style_analysis = state.get("first_chapter_style_analysis", "")
    target_year = state.get("target_year", "")
    
    prompt = ChatPromptTemplate.from_template(CHAPTER_CRITIQUE_PROMPT)
    response = general_model.invoke(prompt.format(
        chapter_content=chapter_content,
        scene_brief=scene_brief,
        research_findings=research_findings,
        first_chapter_style_analysis=first_chapter_style_analysis,
        target_year=target_year
    ))
    
    critique_content = response.content
    
    # Extract the quality rating from the critique
    import re
    quality_match = re.search(r'Rate chapter quality:\s*(EXCELLENT|GOOD|NEEDS_REVISION|MAJOR_REWRITE)', critique_content, re.IGNORECASE)
    quality_rating = quality_match.group(1).upper() if quality_match else "GOOD"
    
    return critique_content, quality_rating


async def rewrite_chapter_if_needed(state: AgentState, config: RunnableConfig, chapter_content: str, critique_feedback: str, scene_brief: str, chapter_number: int, quality_rating: str) -> str:
    """Sub-Step 12d: Rewrite chapter only if critique indicates NEEDS_REVISION or MAJOR_REWRITE"""
    if quality_rating not in ["NEEDS_REVISION", "MAJOR_REWRITE"]:
        print(f"--- Chapter {chapter_number} quality rating: {quality_rating} - No rewrite needed ---")
        return chapter_content
    
    print(f"--- Chapter {chapter_number} quality rating: {quality_rating} - Rewriting ---")
    
    first_chapter_style_analysis = state.get("first_chapter_style_analysis", "")
    target_year = state.get("target_year", "")
    human_condition = state.get("human_condition", "")
    
    prompt = ChatPromptTemplate.from_template(CHAPTER_REWRITE_PROMPT)
    response = writing_model.invoke(prompt.format(
        chapter_number=chapter_number,
        chapter_content=chapter_content,
        critique_feedback=critique_feedback,
        scene_brief=scene_brief,
        first_chapter_style_analysis=first_chapter_style_analysis,
        target_year=target_year,
        human_condition=human_condition
    ))
    
    return response.content


def parse_coherence_tracking_updates(coherence_analysis: str, current_tracking: dict) -> dict:
    """Parse coherence analysis results and update tracking information."""
    tracking = current_tracking.copy()
    
    # Parse tracking updates from coherence analysis
    lines = coherence_analysis.split('\n')
    current_section = None
    
    for line in lines:
        line = line.strip()
        if line == "CHARACTER_SCIENTIFIC_KNOWLEDGE:":
            current_section = "character_knowledge"
        elif line == "ESTABLISHED_TECH_CAPABILITIES:":
            current_section = "tech_capabilities"
        elif line == "SCIENTIFIC_WORLD_RULES:":
            current_section = "world_rules"
        elif line.startswith("- ") and current_section and ":" in line:
            # Parse tracking entries like "- Character: Knowledge update"
            key_value = line[2:].split(":", 1)
            if len(key_value) == 2:
                key, value = key_value[0].strip(), key_value[1].strip()
                tracking[current_section][key] = value
    
    return tracking


async def enhanced_periodic_coherence_check(state: AgentState, config: RunnableConfig, recent_chapters: list[str], chapters_written: int) -> str:
    """Enhanced coherence check with multi-dimensional scientific consistency tracking."""
    research_findings = state.get("research_findings", "")
    target_year = state.get("target_year", "")
    coherence_tracking = state.get("coherence_tracking", {})
    
    # Create batch of recent chapters
    chapters_batch = f"\n\n=== CHAPTER BREAK ===\n\n".join(recent_chapters)
    
    # Extract established scientific facts from tracking and research
    established_facts = format_established_scientific_facts(coherence_tracking, research_findings)
    
    prompt = ChatPromptTemplate.from_template(ENHANCED_SCIENTIFIC_COHERENCE_PROMPT)
    response = general_model.invoke(prompt.format(
        recent_chapters=chapters_batch,
        established_scientific_facts=established_facts,
        target_year=target_year
    ))
    
    return response.content


def format_established_scientific_facts(coherence_tracking: dict, research_findings: str) -> str:
    """Format established scientific facts for coherence checking."""
    facts = []
    
    # Add facts from coherence tracking
    if coherence_tracking.get("world_rules"):
        facts.append("## Established World Rules")
        for rule, description in coherence_tracking["world_rules"].items():
            facts.append(f"- {rule}: {description}")
    
    if coherence_tracking.get("tech_capabilities"):
        facts.append("## Technology Capabilities")
        for tech, capabilities in coherence_tracking["tech_capabilities"].items():
            facts.append(f"- {tech}: {capabilities}")
    
    if coherence_tracking.get("character_knowledge"):
        facts.append("## Character Scientific Knowledge")
        for character, knowledge in coherence_tracking["character_knowledge"].items():
            facts.append(f"- {character}: {knowledge}")
    
    # Add condensed research findings
    if research_findings:
        facts.append("## Original Research Facts")
        facts.append(research_findings[:1000] + "..." if len(research_findings) > 1000 else research_findings)
    
    return "\n".join(facts) if facts else "No established scientific facts tracked yet."


async def periodic_coherence_check(state: AgentState, config: RunnableConfig, recent_chapters: list[str], chapters_written: int) -> str:
    """Sub-Step 12e: Check scientific consistency across recent chapters - ANALYSIS ONLY"""
    research_findings = state.get("research_findings", "")
    target_year = state.get("target_year", "")
    
    # Create batch of recent chapters
    chapters_batch = f"\n\n=== CHAPTER BREAK ===\n\n".join(recent_chapters)
    
    # Extract established world rules from research findings (simplified)
    scientific_rules = research_findings[:1000] if research_findings else "No established scientific rules found"
    
    prompt = ChatPromptTemplate.from_template(SCIENTIFIC_COHERENCE_PROMPT)
    response = general_model.invoke(prompt.format(
        chapters_batch=chapters_batch,
        research_findings=research_findings,
        scientific_rules_established=scientific_rules,
        target_year=target_year
    ))
    
    return response.content


def create_research_summary(research_findings: str) -> str:
    """Create a concise summary of original research topics for dynamic updates."""
    if not research_findings:
        return "No original research conducted."
    
    # Extract key research topics from findings
    lines = research_findings.split('\n')
    topics = []
    
    for line in lines:
        if line.startswith('## Research Query'):
            # Extract the query topic
            topic = line.replace('## Research Query', '').strip()
            if ':' in topic:
                topic = topic.split(':', 1)[1].strip()
            topics.append(topic)
    
    if topics:
        return "Original Research Topics:\n" + "\n".join(f"- {topic}" for topic in topics)
    else:
        return "Research conducted on story-relevant scientific concepts."


def parse_chapter_count_from_outline(outline: str) -> int:
    """Parse the actual chapter count from the competitive outline"""
    import re
    
    # Look for chapter patterns in the outline
    chapter_patterns = [
        r'Chapter (\d+):',  # "Chapter 15:"
        r'### Chapter (\d+)',  # "### Chapter 15"
        r'## Chapter (\d+)',  # "## Chapter 15"
        r'# Chapter (\d+)',  # "# Chapter 15"
        r'Chapter (\d+)\b',  # "Chapter 15" with word boundary
    ]
    
    max_chapter = 0
    
    for pattern in chapter_patterns:
        matches = re.findall(pattern, outline, re.IGNORECASE)
        if matches:
            # Find the highest chapter number
            chapter_numbers = [int(match) for match in matches if match.isdigit()]
            if chapter_numbers:
                max_chapter = max(max_chapter, max(chapter_numbers))
    
    # If we found chapter numbers, use the maximum
    if max_chapter > 0:
        return max_chapter
    
    # Fallback: look for references to total chapters or acts
    total_patterns = [
        r'(\d+)\s*chapters?\s*total',
        r'total\s*of\s*(\d+)\s*chapters?',
        r'(\d+)\s*chapter\s*novel',
        r'chapters?\s*1\s*through\s*(\d+)',
        r'chapters?\s*1-(\d+)',
    ]
    
    for pattern in total_patterns:
        matches = re.findall(pattern, outline, re.IGNORECASE)
        if matches:
            chapter_numbers = [int(match) for match in matches if match.isdigit()]
            if chapter_numbers:
                return max(chapter_numbers)
    
    # Ultimate fallback: count lines that look like chapter headings
    chapter_heading_lines = re.findall(r'^.*chapter\s+\d+.*$', outline, re.IGNORECASE | re.MULTILINE)
    if chapter_heading_lines:
        return len(chapter_heading_lines)
    
    # Final fallback: use 25 as reasonable default
    print("⚠️  Could not parse chapter count from outline, defaulting to 25 chapters")
    return 25


# === HELPER FUNCTIONS FOR FUTURE-NATIVE WORKFLOW ===

def format_story_seeds_options_for_selection(direction_winners: list, competition_summary: str) -> str:
    """Format future story seeds options for user selection."""
    
    newline = "\n"
    content = f"# Future Story Seeds Options from Co-Scientist Competition{newline}{newline}"
    content += f"{len(direction_winners)} different story approaches competed and are now available for your selection.{newline}{newline}"
    
    content += f"## Competition Overview{newline}"
    content += competition_summary + f"{newline}{newline}"
    
    for i, winner in enumerate(direction_winners, 1):
        content += f"## Option {i}: {winner.get('research_direction', 'Unknown Approach')}{newline}{newline}"
        content += f"**Core Approach:** {winner.get('core_assumption', 'No assumption available')}{newline}{newline}"
        content += f"**Selection Reasoning:** {winner.get('selection_reasoning', 'Tournament winner')}{newline}{newline}"
        content += f"**Story Concept:**{newline}"
        content += f"{winner.get('scenario_content', 'No content available')}{newline}{newline}"
        
        if i < len(direction_winners):
            content += "---" + f"{newline}{newline}"
    
    return content


def format_direction_winners_for_selection(direction_winners: list, competition_summary: str, target_year: int, human_condition: str) -> str:
    """Format direction winners as 3 batches of 3 loglines each for user selection."""
    
    newline = "\n"
    content = f"# Future Story Loglines from Co-Scientist Competition{newline}{newline}"
    content += f"Multiple creative approaches competed to generate authentic {target_year} stories exploring: {human_condition}{newline}{newline}"
    
    content += f"## Competition Overview{newline}"
    content += competition_summary + f"{newline}{newline}"
    
    content += f"## Logline Options - 3 Batches of 3 Loglines Each{newline}{newline}"
    
    for batch_num, winner in enumerate(direction_winners, 1):
        approach_name = winner.get('research_direction', 'Unknown Approach')
        core_assumption = winner.get('core_assumption', 'No assumption available')
        scenario_content = winner.get('scenario_content', '')
        
        content += f"### Batch {batch_num}: {approach_name}{newline}"
        content += f"**Creative Philosophy:** {core_assumption}{newline}{newline}"
        
        # Extract the 3 loglines from this batch
        if "## Top 3 Selected" in scenario_content:
            top_3_section = scenario_content.split("## Top 3 Selected")[1]
            lines = top_3_section.strip().split('\n')
            logline_count = 0
            for line in lines:
                line = line.strip()
                if line and ('In ' + str(target_year) in line) and len(line.strip()) > 50:
                    logline_count += 1
                    logline_text = line.strip('123.- ').strip()
                    content += f"**Logline {logline_count}:** {logline_text}{newline}{newline}"
                    if logline_count >= 3:  # Only show 3 per batch
                        break
        else:
            # Fallback: extract from full content
            lines = scenario_content.split('\n')
            logline_count = 0
            for line in lines:
                if 'In ' + str(target_year) in line and len(line.strip()) > 50:
                    logline_count += 1
                    logline_text = line.strip('123.- ').strip()
                    content += f"**Logline {logline_count}:** {logline_text}{newline}{newline}"
                    if logline_count >= 3:  # Only show 3 per batch
                        break
        
        if batch_num < len(direction_winners):
            content += f"---{newline}{newline}"
    
    content += f"## How To Select{newline}"
    content += f"1. Choose your preferred logline from any of the 3 batches above{newline}"
    content += f"2. Copy the FULL logline text (the entire sentence starting with 'In {target_year}...')'{newline}"
    content += f"3. In LangGraph Studio, paste it into the **`user_story_selection`** property{newline}"
    content += f"4. Resume the workflow{newline}{newline}"
    content += f"**Example:** If you like Logline 2 from Batch 1, copy the entire text and paste it as:{newline}"
    content += f'```json{newline}{{"user_story_selection": "In {target_year}, when..."}}{newline}```{newline}'
    
    return content


def format_loglines_options_for_selection(all_loglines: list, competition_summary: str, target_year: int, human_condition: str) -> str:
    """Format competitive loglines with clear numbered options for user selection."""
    
    newline = "\n"
    content = f"# 🎯 Select Your Story Logline - Co-Scientist Competition Results{newline}{newline}"
    content += f"Multiple creative approaches competed to generate authentic {target_year} stories exploring: **{human_condition}**{newline}{newline}"
    
    content += f"## Competition Overview{newline}"
    content += competition_summary + f"{newline}{newline}"
    
    content += f"## 📋 Numbered Logline Options{newline}{newline}"
    
    # Extract all individual loglines with global numbering
    global_option_number = 1
    
    for winner in all_loglines:
        approach_name = winner.get('research_direction', 'Unknown Approach')
        core_assumption = winner.get('core_assumption', 'No assumption available')
        scenario_content = winner.get('scenario_content', '')
        
        content += f"### 🔬 {approach_name} Approach{newline}"
        content += f"**Creative Philosophy:** {core_assumption}{newline}{newline}"
        
        # Extract individual loglines from this approach
        if "## Top 3 Selected" in scenario_content:
            top_3_section = scenario_content.split("## Top 3 Selected")[1]
            lines = top_3_section.strip().split('\n')
            approach_loglines = []
            for line in lines:
                line = line.strip()
                if line and ('In ' + str(target_year) in line) and len(line.strip()) > 50:
                    logline_text = line.strip('123.- ').strip()
                    approach_loglines.append(logline_text)
                    if len(approach_loglines) >= 3:  # Only take 3 per approach
                        break
        else:
            # Fallback: search in full content
            lines = scenario_content.split('\n')
            approach_loglines = []
            for line in lines:
                if 'In ' + str(target_year) in line and len(line.strip()) > 50:
                    logline_text = line.strip('123.- ').strip()
                    approach_loglines.append(logline_text)
                    if len(approach_loglines) >= 3:  # Only take 3 per approach
                        break
        
        # Display numbered options
        for logline in approach_loglines:
            content += f"**Option {global_option_number}:** {logline}{newline}{newline}"
            global_option_number += 1
        
        content += f"---{newline}{newline}"
    
    content += f"## 🎮 How To Select Your Logline{newline}{newline}"
    content += f"1. **Choose** your preferred option number from the list above{newline}"
    content += f"2. **In LangGraph Studio**, enter just the number into the `user_story_selection` field{newline}"
    content += f"3. **Resume** the workflow to continue{newline}{newline}"
    
    content += f"### 💡 Example Selection:{newline}"
    content += f"- If you like **Option 3**, simply enter: `3`{newline}"
    content += f"- If you like **Option 7**, simply enter: `7`{newline}{newline}"
    
    content += f"### 📱 LangGraph Studio Instructions:{newline}"
    content += f"```json{newline}"
    content += f'{{"user_story_selection": 3}}{newline}'
    content += f"```{newline}{newline}"
    
    content += f"🚀 **The selected logline will be expanded into a full story concept and used as the foundation for your {target_year} novel!**{newline}"
    
    return content


def format_story_refinement_options_for_selection(direction_winners: list, competition_summary: str) -> str:
    """Format story refinement options with clear numbered options for user selection."""
    
    newline = "\n"
    content = f"# 🔬 Select Your Story Refinement - Co-Scientist Competition Results{newline}{newline}"
    content += f"Research-grounded story refinement approaches competed and are now available for your selection.{newline}{newline}"
    
    content += f"## Competition Overview{newline}"
    content += competition_summary + f"{newline}{newline}"
    
    content += f"## 📋 Numbered Refinement Options{newline}{newline}"
    
    for i, winner in enumerate(direction_winners, 1):
        content += f"### **Option {i}: {winner.get('research_direction', 'Unknown Approach')}**{newline}{newline}"
        content += f"**Core Approach:** {winner.get('core_assumption', 'No assumption available')}{newline}{newline}"
        content += f"**Selection Reasoning:** {winner.get('selection_reasoning', 'Tournament winner')}{newline}{newline}"
        content += f"**Refined Story Synopsis:**{newline}"
        content += f"{winner.get('scenario_content', 'No content available')}{newline}{newline}"
        
        if i < len(direction_winners):
            content += f"---{newline}{newline}"
    
    content += f"## 🎮 How To Select Your Refinement{newline}{newline}"
    content += f"1. **Choose** your preferred option number from the list above{newline}"
    content += f"2. **In LangGraph Studio**, enter just the number into the `user_refinement_selection` field{newline}"
    content += f"3. **Resume** the workflow to continue{newline}{newline}"
    
    content += f"### 💡 Example Selection:{newline}"
    content += f"- If you like **Option 1**, simply enter: `1`{newline}"
    content += f"- If you like **Option {len(direction_winners)}**, simply enter: `{len(direction_winners)}`{newline}{newline}"
    
    content += f"### 📱 LangGraph Studio Instructions:{newline}"
    content += f"```json{newline}"
    content += f'{{"user_refinement_selection": 1}}{newline}'
    content += f"```{newline}{newline}"
    
    content += f"🚀 **The selected refinement will be used to create your detailed novel outline!**{newline}"
    
    return content


def analyze_chapter_style(chapter_content: str) -> str:
    """Analyze the style of a chapter for consistency in subsequent chapters."""
    
    # Simple style analysis - in a full implementation this could be more sophisticated
    # Extract newline pattern to avoid backslash in f-string
    double_newline = '\n\n'
    paragraph_count = len(chapter_content.split(double_newline))
    paragraph_style = 'Short, punchy paragraphs' if paragraph_count > 10 else 'Longer, flowing paragraphs'
    perspective = 'First person' if ' I ' in chapter_content else 'Third person'
    
    analysis = (
        f"# Chapter Style Analysis\n\n"
        f"## Prose Style Characteristics\n"
        f"- **Length:** {len(chapter_content.split())} words\n"
        f"- **Paragraph Structure:** {paragraph_style}\n"
        f"- **Sentence Variety:** Mixed sentence lengths for engaging rhythm\n"
        f"- **Perspective:** {perspective}\n\n"
        f"## Narrative Voice\n"
        f"- **Tone:** Established through character observations and dialogue\n"
        f"- **Pacing:** Balanced between action and introspection\n"
        f"- **World Integration:** Technology and culture presented as natural background\n\n"
        f"## Style Guidelines for Continuation\n"
        f"1. Maintain the established perspective and narrative voice\n"
        f"2. Continue integrating future elements naturally, not as exposition\n"
        f"3. Keep pacing consistent with opening chapter rhythm\n"
        f"4. Preserve the balance between character development and world-building\n"
        f"5. Use similar sentence structure variety and paragraph flow\n\n"
        f"## Key Stylistic Elements to Preserve\n"
        f"- Character voice authenticity as future natives\n"
        f"- Seamless technology integration\n"
        f"- Show-don't-tell approach to world-building\n"
        f"- Appropriate tone and mood consistency\n\n"
        f"This analysis should guide subsequent chapter writing to maintain narrative consistency.\n"
    )
    
    return analysis


def format_detailed_competition_results(co_scientist_result: dict) -> str:
    """Format detailed results from co-scientist competition for saving."""
    
    newline = "\n"
    detailed = f"# Detailed Co-Scientist Competition Results{newline}{newline}"
    
    # Research directions
    directions = co_scientist_result.get("research_directions", [])
    detailed += f"## Research Directions ({len(directions)}){newline}"
    for i, direction in enumerate(directions, 1):
        detailed += f"### Direction {i}: {direction.get('name', 'Unknown')}{newline}"
        detailed += f"- **Assumption:** {direction.get('assumption', 'N/A')}{newline}"
        detailed += f"- **Focus:** {direction.get('focus', 'N/A')}{newline}{newline}"
    
    # Population statistics  
    population = co_scientist_result.get("scenario_population", [])
    detailed += f"## Scenario Population{newline}"
    detailed += f"- **Total Generated:** {len(population)}{newline}"
    if directions:
        per_direction = len(population) // len(directions)
        detailed += f"- **Per Direction:** {per_direction} scenarios{newline}"
    
    # Calculate quality distribution
    quality_scores = [s.get("quality_score", 0) for s in population if s.get("quality_score")]
    if quality_scores:
        avg_quality = sum(quality_scores) / len(quality_scores)
        detailed += f"- **Average Quality Score:** {avg_quality:.1f}/100{newline}"
        detailed += f"- **Quality Range:** {min(quality_scores)}-{max(quality_scores)}/100{newline}"
    
    detailed += f"{newline}"
    
    # Tournament winners
    direction_winners = co_scientist_result.get("direction_winners", [])
    detailed += f"## Tournament Winners{newline}"
    detailed += f"- **Direction Champions:** {len(direction_winners)}{newline}"
    
    if direction_winners:
        detailed += f"{newline}"
        for i, winner in enumerate(direction_winners, 1):
            direction = winner.get("research_direction", "Unknown")
            team_id = winner.get("team_id", "Unknown")
            quality = winner.get("quality_score", 0)
            elo = winner.get("final_elo_rating", 0)
            
            detailed += f"### Winner {i}: {direction}{newline}"
            detailed += f"- **Team ID:** {team_id}{newline}"
            detailed += f"- **Quality Score:** {quality}/100{newline}"
            detailed += f"- **Final Elo Rating:** {elo:.0f}{newline}{newline}"
    
    return detailed


def format_co_scientist_winner_details(winner_scenario: dict, content_type: str) -> str:
    """Format detailed information about the winning scenario from co_scientist competition."""
    
    newline = "\n"
    details = f"# Co-Scientist Winner: {content_type.title()}{newline}{newline}"
    details += f"**Content Type:** {content_type}{newline}"
    details += f"**Competition Rank:** #{winner_scenario.get('competition_rank', 1)}{newline}"
    details += f"**Research Direction:** {winner_scenario.get('research_direction', 'Unknown')}{newline}"
    details += f"**Team ID:** {winner_scenario.get('team_id', 'Unknown')}{newline}"
    details += f"**Scenario ID:** {winner_scenario.get('scenario_id', 'Unknown')}{newline}{newline}"
    
    details += f"## Selection Reasoning{newline}{newline}"
    details += f"{winner_scenario.get('selection_reasoning', 'Selected through competitive tournament')}{newline}{newline}"
    
    details += f"## Generated Content{newline}{newline}"
    details += f"{winner_scenario.get('scenario_content', 'No content available')}{newline}{newline}"
    
    if winner_scenario.get('core_assumption'):
        details += f"## Core Research Assumption{newline}{newline}"
        details += f"{winner_scenario.get('core_assumption')}{newline}{newline}"
    
    if winner_scenario.get('research_query'):
        details += f"## Research Query{newline}{newline}"
        details += f"{winner_scenario.get('research_query')}{newline}{newline}"
    
    if any(winner_scenario.get(key) for key in ['generation_timestamp', 'quality_score', 'critiques']):
        details += f"## Competition Metadata{newline}"
        details += f"- **Generated:** {winner_scenario.get('generation_timestamp')}{newline}"
        details += f"- **Quality Score:** {winner_scenario.get('quality_score', 'N/A')}{newline}"
        details += f"- **Critiques:** {len(winner_scenario.get('critiques', []))}{newline}{newline}"
    
    return details


# === ROUTING FUNCTIONS FOR MODULAR CHAPTER WRITING ===

def route_chapter_writing(state: AgentState) -> str:
    """Route between standard and competitive chapter writing based on importance."""
    chapter_importance = state.get("current_chapter_importance", "STANDARD")
    
    if chapter_importance == "KEY":
        return "write_key_chapter_competitive"
    else:
        return "write_chapter_draft_node"


def route_after_rewrite(state: AgentState) -> str:
    """Route after chapter rewrite: dynamic research → coherence → check if more chapters"""
    current_chapter = state.get("current_chapter_number", 0)
    target_chapters = state.get("target_chapters_count", 0)
    
    # Always do dynamic research check first
    return "dynamic_research_update_node"


def route_after_dynamic_research(state: AgentState) -> str:
    """Route after dynamic research: check coherence, then check if more chapters"""
    current_chapter = state.get("current_chapter_number", 0)
    target_chapters = state.get("target_chapters_count", 0)
    
    # Check if we need coherence check (every 4 chapters or final chapter)
    should_check_coherence = (current_chapter % 4 == 0) or (current_chapter == target_chapters)
    
    if should_check_coherence:
        return "periodic_coherence_check_node"
    else:
        return "check_if_more_chapters"


def route_after_coherence_check(state: AgentState) -> str:
    """Route after coherence check: always go to chapter completion check"""
    return "check_if_more_chapters"


def route_chapter_completion(state: AgentState) -> str:
    """Route based on chapter completion status"""
    current_chapter = state.get("current_chapter_number", 0)
    target_chapters = state.get("target_chapters_count", 0)
    
    if current_chapter < target_chapters:
        # More chapters to write
        return "create_scene_brief_node"
    else:
        # All chapters complete
        return "compile_complete_novel"


# === MAIN WORKFLOW GRAPH ===

workflow = StateGraph(AgentState)

# Add nodes for the future-native workflow with user selection
workflow.add_node("parse_and_complete_user_input", parse_and_complete_user_input)
workflow.add_node("generate_light_future_context", generate_light_future_context)  
workflow.add_node("generate_competitive_loglines", generate_competitive_loglines)
workflow.add_node("user_story_selection", user_story_selection)
workflow.add_node("identify_story_research_targets", identify_story_research_targets)
workflow.add_node("generate_research_queries", generate_research_queries)
workflow.add_node("conduct_deep_research", conduct_deep_research)
workflow.add_node("integrate_research_findings", integrate_research_findings)
workflow.add_node("create_outline_prep_materials", create_outline_prep_materials)
workflow.add_node("create_competitive_outline", create_competitive_outline)
workflow.add_node("analyze_outline", analyze_outline)
workflow.add_node("rewrite_outline", rewrite_outline)
workflow.add_node("write_first_chapter_competitive", write_first_chapter_competitive)
# Enhanced modular chapter writing nodes
workflow.add_node("initialize_chapter_loop", initialize_chapter_loop)
workflow.add_node("create_scene_brief_node", create_scene_brief_node)
workflow.add_node("write_key_chapter_competitive", write_key_chapter_competitive)
workflow.add_node("write_chapter_draft_node", write_chapter_draft_node)
workflow.add_node("critique_chapter_node", critique_chapter_node)
workflow.add_node("conditional_rewrite_chapter_node", conditional_rewrite_chapter_node)
workflow.add_node("dynamic_research_update_node", dynamic_research_update_node)
workflow.add_node("check_if_more_chapters", check_if_more_chapters)
workflow.add_node("periodic_coherence_check_node", periodic_coherence_check_node)
workflow.add_node("compile_complete_novel", compile_complete_novel)

# Define the workflow edges with user selection interrupt
workflow.add_edge(START, "parse_and_complete_user_input")
workflow.add_edge("parse_and_complete_user_input", "generate_light_future_context")
workflow.add_edge("generate_light_future_context", "generate_competitive_loglines")
workflow.add_edge("generate_competitive_loglines", "user_story_selection")
workflow.add_edge("user_story_selection", "identify_story_research_targets")
workflow.add_edge("identify_story_research_targets", "generate_research_queries")
workflow.add_edge("generate_research_queries", "conduct_deep_research")
workflow.add_edge("conduct_deep_research", "integrate_research_findings")
workflow.add_edge("integrate_research_findings", "create_outline_prep_materials")
workflow.add_edge("create_outline_prep_materials", "create_competitive_outline")
workflow.add_edge("create_competitive_outline", "analyze_outline")
workflow.add_edge("analyze_outline", "rewrite_outline")
workflow.add_edge("rewrite_outline", "write_first_chapter_competitive")
workflow.add_edge("write_first_chapter_competitive", "initialize_chapter_loop")
# Enhanced modular chapter writing flow
workflow.add_edge("initialize_chapter_loop", "create_scene_brief_node")
# Conditional routing for chapter writing based on importance
workflow.add_conditional_edges(
    "create_scene_brief_node",
    route_chapter_writing,
    ["write_key_chapter_competitive", "write_chapter_draft_node"]
)
workflow.add_edge("write_key_chapter_competitive", "critique_chapter_node")
workflow.add_edge("write_chapter_draft_node", "critique_chapter_node")
workflow.add_edge("critique_chapter_node", "conditional_rewrite_chapter_node")
# Routing after rewrite: always go to dynamic research
workflow.add_conditional_edges(
    "conditional_rewrite_chapter_node",
    route_after_rewrite,
    ["dynamic_research_update_node"]
)
# Routing after dynamic research: conditional coherence check
workflow.add_conditional_edges(
    "dynamic_research_update_node",
    route_after_dynamic_research,
    ["periodic_coherence_check_node", "check_if_more_chapters"]
)
# Routing after coherence check
workflow.add_conditional_edges(
    "periodic_coherence_check_node",
    route_after_coherence_check,
    ["check_if_more_chapters"]
)
# Routing based on chapter completion
workflow.add_conditional_edges(
    "check_if_more_chapters",
    route_chapter_completion,
    ["create_scene_brief_node", "compile_complete_novel"]
)
workflow.add_edge("compile_complete_novel", END)

# Compile the workflow with user selection interrupt
# Note: LangGraph Studio provides persistence automatically
app = workflow.compile(
    interrupt_before=["user_story_selection"]
)

print("🚀 Deep Sci-Fi Writer initialized with Enhanced Scientific Coherence System!")
print("📚 Streamlined process: Parse → Context → Competitive Loglines → [USER SELECTION] → Research → Integrate → Outline Prep → Competitive Outline → Analyze → Rewrite → First Chapter → Intelligent Chapter Loop")
print("🔧 Intelligent Chapter Process: Scene Brief → [Classify] → Competitive/Standard Writing → Critique → Conditional Rewrite → Dynamic Research → Enhanced Coherence Check → Loop")
print("⏸️  Workflow pauses once for story logline selection in LangGraph Studio!")
print("💾 Persistence handled automatically by LangGraph Studio - no custom checkpointer needed!")
print("⚡ Research queries run in parallel for faster completion!")
print("🎯 Direct research integration eliminates second user selection step!")
print("🧠 Intelligent chapter classification routes KEY chapters through CS competition!")
print("🔬 Dynamic research updates detect and research emerging scientific concepts!")
print("📊 Enhanced coherence tracking maintains scientific consistency across dimensions!")
print("🔍 Maximum observability with separate nodes for each process step!")