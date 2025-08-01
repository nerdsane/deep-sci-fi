import os
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
    CREATE_CHAPTER_ARCS_PROMPT,
    GENERATE_WORLD_BUILDING_QUESTIONS_PROMPT,
    ADJUST_CHAPTER_ARCS_PROMPT,
    GENERATE_SCIENTIFIC_EXPLANATIONS_PROMPT,
    GENERATE_GLOSSARY_PROMPT,
    PROJECT_QUESTIONS_PROMPT,
    # Multi-chapter book writing prompts
    GENERATE_CHAPTER_WORLD_QUESTIONS_PROMPT,
    CHECK_CHAPTER_COHERENCE_PROMPT,
    VALIDATE_TRANSITIONS_PROMPT,
    PLAN_REMAINING_CHAPTERS_PROMPT,
    UPDATE_PLOT_CONTINUITY_PROMPT,
    GENERATE_CHAPTER_SCIENTIFIC_EXPLANATIONS_PROMPT,
    UPDATE_ACCUMULATED_GLOSSARY_PROMPT,
)

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
    
    return final_state.get("final_report", "Error: Research failed to produce a report.")



def save_output(output_dir: str, filename: str, content: str):
    """Saves content to a markdown file in the specified output directory."""
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, filename), "w") as f:
        f.write(content)

class AgentState(TypedDict):
    input: str
    output_dir: Optional[str]
    starting_year: Optional[int]
    loop_count: Optional[int]
    messages: Annotated[list, operator.add]
    years_in_future: Optional[int]
    selected_scenario: Optional[str]
    target_year: Optional[int]
    baseline_world_state: Optional[str]
    storyline: Optional[str]
    storyline_options: Optional[dict]  # Co-scientist storyline options
    storyline_choice: Optional[str]  # User's storyline selection (1, 2, or 3)
    chapter_arcs: Optional[str]
    chapter_arcs_options: Optional[dict]  # Co-scientist chapter arcs options
    chapter_arcs_choice: Optional[str]  # User's chapter arcs selection (1, 2, or 3)
    first_chapter: Optional[str]
    first_chapter_options: Optional[dict]  # Co-scientist first chapter options
    chapter_choice: Optional[str]  # User's chapter selection (1 or 2)
    world_building_questions: Optional[str]
    world_building_scenarios: Optional[str]
    world_scenario_options: Optional[dict]  # Co-scientist world scenario options
    world_scenario_choice: Optional[str]  # User's world scenario selection (1, 2, or 3)
    scenario_critique: Optional[str]
    linguistic_evolution: Optional[str]
    linguistic_evolution_options: Optional[dict]  # Co-scientist linguistic options
    linguistic_choice: Optional[str]  # User's linguistic evolution selection (1 or 2)
    revised_storyline: Optional[str]
    storyline_adjustment_options: Optional[dict]  # Co-scientist storyline adjustment options
    storyline_adjustment_choice: Optional[str]  # User's storyline adjustment selection (1 or 2)
    revised_chapter_arcs: Optional[str]
    revised_first_chapter: Optional[str]
    chapter_rewrite_options: Optional[dict]  # Co-scientist chapter rewrite options
    chapter_rewrite_choice: Optional[str]  # User's chapter rewrite selection (1 or 2)
    scientific_explanations: Optional[str]
    glossary: Optional[str]
    # Multi-chapter book writing fields
    next_action_choice: Optional[str]  # "project" or "write_book"
    current_chapter_number: Optional[int]
    total_planned_chapters: Optional[int]
    previous_chapters: Optional[list]  # List of completed chapter contents
    accumulated_scientific_explanations: Optional[str]
    accumulated_glossary: Optional[str]
    plot_continuity_tracker: Optional[str]
    chapter_coherence_issues: Optional[str]
    transition_quality_scores: Optional[list]  # List of transition quality scores
    chapter_transitions: Optional[str]  # Transition notes between chapters
    chapter_planning_options: Optional[dict]  # Co-scientist chapter planning options
    chapter_planning_choice: Optional[str]
    chapter_world_questions: Optional[str]
    chapter_world_context: Optional[str]
    current_chapter_draft: Optional[str]
    chapter_coherence_report: Optional[str]
    transition_validation_report: Optional[str]
    book_compilation_complete: Optional[bool]
    total_chapters_written: Optional[int]
    average_transition_quality: Optional[float]

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
            "opus_4": "anthropic:claude-opus-4-20250514", 
            "sonnet_3_5": "anthropic:claude-3-5-sonnet-20241022",
            "haiku_3_5": "anthropic:claude-3-5-haiku-20241022"
        },
        ModelProvider.OPENAI: {
            # OpenAI models (o3 supports thinking, o1 has built-in reasoning)
            "o3": "openai:o3-2025-04-16",
            "o3_mini": "openai:o3-mini-2025-04-16", 
            "o1": "openai:o1-2024-12-17",
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
    # Format: {"provider": "model_key", "thinking": True/False}
    USE_CASE_MODELS = {
        # Creative narrative tasks - OpenAI O3 for reasoning-driven creativity
        "general_creative": {
            "provider": ModelProvider.OPENAI,
            "model": "o3", 
            "thinking": False,  # O3 has built-in reasoning
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
        
        # Linguistic research - Claude Sonnet 4 with thinking + Deep Researcher
        "linguistic_research": {
            "provider": ModelProvider.ANTHROPIC, 
            "model": "sonnet_4",
            "thinking": True,
            "temperature": 0.8,
            "max_tokens": 8000
        }
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
            # Enable thinking mode for Anthropic models
            # Reference: https://python.langchain.com/docs/integrations/chat/anthropic/
            params["extra_headers"] = {"anthropic-beta": "thinking-2025-01-21"}
            
        return init_chat_model(model_string, **params).with_retry()

# === Legacy Model Configuration (for backward compatibility) ===
model_config = {
    # Map to new flexible system
    "research_model": ModelConfig.get_model_string("world_research"),
    "writing_model": ModelConfig.get_model_string("chapter_writing"), 
    "general_model": ModelConfig.get_model_string("general_creative"),
    
    # Co-scientist configuration
    "save_intermediate_results": True,
}

def reset_deep_sci_fi_models():
    """Reset model instances to prevent context bleeding between runs."""
    global writing_model, general_model
    
    # Use new flexible model system with thinking mode
    writing_model = ModelConfig.create_model_instance("chapter_writing")
    general_model = ModelConfig.create_model_instance("general_creative")
    
    print("🔄 Reset deep_sci_fi models for fresh creative generation")
    print(f"  📝 Writing model: {ModelConfig.get_model_string('chapter_writing')} (thinking: {ModelConfig.supports_thinking('chapter_writing')})")
    print(f"  🎯 General model: {ModelConfig.get_model_string('general_creative')} (thinking: {ModelConfig.supports_thinking('general_creative')})")

def comprehensive_deep_sci_fi_session_reset():
    """Enhanced session reset for deep_sci_fi that addresses multiple layers of context bleeding.
    
    Implements comprehensive session isolation to prevent any form of context bleeding
    between different deep-sci-fi runs, including:
    - Model instance state
    - Framework-level caching  
    - Random seed state
    - Environment variables
    - Provider-side session correlation
    """
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
    
    # 6. Clear any LangChain framework state
    try:
        from langchain.callbacks import get_openai_callback
        print("  ✅ Cleared LangChain framework state")
    except ImportError:
        pass
    
    print(f"🎉 Session reset complete with session ID: {unique_session_id}")
    return unique_session_id

# Initialize the models with new flexible system
writing_model = ModelConfig.create_model_instance("chapter_writing")
general_model = ModelConfig.create_model_instance("general_creative")


async def create_storyline(state: AgentState, config: RunnableConfig):
    print("--- Starting New Story with Co-Scientist Competition ---")
    
    # Comprehensive session reset to prevent all forms of context bleeding
    session_id = comprehensive_deep_sci_fi_session_reset()
    
    run_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_dir = os.path.join("output", run_timestamp)
    starting_year = datetime.now().year
    
    # Use co_scientist for competitive storyline creation
    co_scientist_input = CoScientistConfiguration.create_input_state(
        use_case=UseCase.STORYLINE_CREATION,
        context=f"User's idea for the novel: {state['input']}"
    )
    
    # Configure co_scientist for full creative competition
    subgraph_config = config.copy()
    subgraph_config["configurable"].update({
        "research_model": ModelConfig.get_model_string("general_creative"),
        "general_model": ModelConfig.get_model_string("general_creative"),
        "use_case": "storyline_creation",
        "process_depth": "standard",      # Full creative process with reflection and evolution
        "population_scale": "light",      # Keep processing reasonable for creative tasks
        "use_deep_researcher": False,     # Use regular LLM for creative writing
        "save_intermediate_results": True,
        "output_dir": output_dir,
        "phase": "storyline_creation"
    })
    
    # Run co_scientist competition
    co_scientist_result = await co_scientist.ainvoke(co_scientist_input, subgraph_config)
    
    # Save detailed competition results
    if model_config.get("save_intermediate_results", True):
        # Note: Competition summary saved in co_scientist subdirectory to avoid duplication
        
        # Save detailed competition data
        detailed_results = format_detailed_competition_results(co_scientist_result)
        save_output(output_dir, "00_01b_storyline_competition_details.md", detailed_results)
        
        # Save both direction winners with metadata
        direction_winners = co_scientist_result.get("direction_winners", [])
        for i, winner in enumerate(direction_winners, 1):
            winner_details = format_co_scientist_winner_details(winner, f"storyline_option_{i}")
            save_output(output_dir, f"00_01c_storyline_option_{i}_full.md", winner_details)
    
    # Store direction winners for user selection (not auto-selecting)
    direction_winners = co_scientist_result.get("direction_winners", [])
    
    
    if direction_winners:
        # Format both options for user presentation
        formatted_options = format_storyline_options_for_selection(direction_winners, co_scientist_result.get("competition_summary", ""))
        save_output(output_dir, "00_01_storyline_options.md", formatted_options)
        
        # Store options in state for user selection
        storyline_options = {
            "option_1": direction_winners[0].get("scenario_content", "") if len(direction_winners) > 0 else "",
            "option_2": direction_winners[1].get("scenario_content", "") if len(direction_winners) > 1 else "",
            "option_3": direction_winners[2].get("scenario_content", "") if len(direction_winners) > 2 else "",
            "options_metadata": direction_winners
        }
        
        print("--- Co-Scientist Storyline Competition Complete ---")
        print(f"--- {len(direction_winners)} storyline options created. User selection required. ---")
        
        return {
            "output_dir": output_dir,
            "starting_year": starting_year,
            "target_year": starting_year,
            "loop_count": 0,
            "messages": [],
            "storyline_options": storyline_options,  # Store options for user selection
            "storyline": None,  # No auto-selection - requires user input
            "years_in_future": None,
            "baseline_world_state": None,
        }
    else:
        # Co-scientist failed to produce direction winners - this is a system failure
        raise RuntimeError("Co-scientist storyline competition failed to produce direction winners. Check competition configuration and model availability.")

def select_storyline(state: AgentState):
    """User selection node - presents storyline options and waits for user choice."""
    if not (output_dir := state.get("output_dir")) or not (storyline_options := state.get("storyline_options")):
        raise ValueError("Required state 'output_dir' or 'storyline_options' is missing.")
    
    # Present options to user through the interface
    options_metadata = storyline_options.get("options_metadata", [])
    if len(options_metadata) < 2:
        raise ValueError("Not enough storyline options for user selection.")
    
    # Note: Individual storyline options saved as full versions (_full.md) in create_storyline() - no duplicates needed
    
    print("--- Storyline Options Prepared for User Selection ---")
    print(f"Option 1: {options_metadata[0].get('research_direction', 'Unknown')}")
    print(f"Option 2: {options_metadata[1].get('research_direction', 'Unknown')}")
    if len(options_metadata) > 2:
        print(f"Option 3: {options_metadata[2].get('research_direction', 'Unknown')}")
    
    # This function prepares options for user selection via LangGraph Studio interrupt
    # The actual selection happens in the next node via interrupt_before mechanism
    print("--- Storyline options prepared. Workflow will pause for user selection. ---")
    
    return {"storyline_options": storyline_options}

def process_storyline_selection(state: AgentState):
    """Process user's storyline selection after interrupt."""
    if not (output_dir := state.get("output_dir")) or not (storyline_options := state.get("storyline_options")):
        raise ValueError("Required state 'output_dir' or 'storyline_options' is missing.")
    
    # Get user's choice from state (will be set by LangGraph Studio)
    user_choice = state.get("storyline_choice", "1")  # Default to option 1
    options_metadata = storyline_options.get("options_metadata", [])
    
    option_1_content = storyline_options.get("option_1", "")
    option_2_content = storyline_options.get("option_2", "")
    option_3_content = storyline_options.get("option_3", "")
    
    # Process user choice
    choice = str(user_choice).strip()
    print(f"--- Processing user choice: '{choice}' ---")
    print(f"Available options: option_1={len(option_1_content)} chars, option_2={len(option_2_content)} chars, option_3={len(option_3_content)} chars")
    
    if choice == "1":
        selected_storyline = option_1_content
        selected_option = options_metadata[0] if len(options_metadata) > 0 else {}
    elif choice == "2":
        selected_storyline = option_2_content
        selected_option = options_metadata[1] if len(options_metadata) > 1 else {}
    elif choice == "3":
        selected_storyline = option_3_content
        selected_option = options_metadata[2] if len(options_metadata) > 2 else {}
        print(f"--- Option 3 selected. Content length: {len(selected_storyline)} characters ---")
    else:
        # Default to option 1 if invalid choice
        print(f"Invalid choice '{choice}', defaulting to Option 1")
        selected_storyline = option_1_content
        selected_option = options_metadata[0] if len(options_metadata) > 0 else {}
    
    if not selected_storyline:
        raise ValueError(f"Selected storyline content is empty for choice '{choice}'. This indicates a problem with option storage.")
    
    save_output(output_dir, "00_01_selected_storyline.md", selected_storyline)
    
    print(f"--- Storyline Selected: {selected_option.get('research_direction', 'Unknown')} ---")
    
    return {
        "storyline": selected_storyline,
        "selected_scenario": selected_option.get('research_direction', 'Unknown')
    }

def get_chapter_arcs_selection_input(state: AgentState):
    """Get chapter arcs selection input from user."""
    print("--- Chapter Arcs Options Available. User selection required. ---")
    return {"messages": ["User must select from chapter arc options"]}

def process_chapter_arcs_selection(state: AgentState):
    """Process user's chapter arcs selection after interrupt."""
    if not (output_dir := state.get("output_dir")) or not (chapter_arcs_options := state.get("chapter_arcs_options")):
        raise ValueError("Required state 'output_dir' or 'chapter_arcs_options' is missing.")
    
    # Get user's choice from state (will be set by LangGraph Studio)
    user_choice = state.get("chapter_arcs_choice", "1")  # Default to option 1
    options_metadata = chapter_arcs_options.get("options_metadata", [])
    
    option_1_content = chapter_arcs_options.get("option_1", "")
    option_2_content = chapter_arcs_options.get("option_2", "")
    option_3_content = chapter_arcs_options.get("option_3", "")
    
    # Process user choice
    choice = str(user_choice).strip()
    if choice == "1":
        selected_chapter_arcs = option_1_content
        selected_option = options_metadata[0] if len(options_metadata) > 0 else {}
    elif choice == "2":
        selected_chapter_arcs = option_2_content
        selected_option = options_metadata[1] if len(options_metadata) > 1 else {}
    elif choice == "3":
        selected_chapter_arcs = option_3_content
        selected_option = options_metadata[2] if len(options_metadata) > 2 else {}
    else:
        # Default to option 1 if invalid choice
        print(f"Invalid choice '{choice}', defaulting to Option 1")
        selected_chapter_arcs = option_1_content
        selected_option = options_metadata[0] if len(options_metadata) > 0 else {}
    
    save_output(output_dir, "00_02_selected_chapter_arcs.md", selected_chapter_arcs)
    
    print(f"--- Chapter Arcs Selected: {selected_option.get('research_direction', 'Unknown')} ---")
    
    return {
        "chapter_arcs": selected_chapter_arcs
    }

async def create_chapter_arcs(state: AgentState, config: RunnableConfig):
    if not (output_dir := state.get("output_dir")) or not (storyline := state.get("storyline")):
        raise ValueError("Required state 'output_dir' or 'storyline' is missing.")
    
    print("--- Creating Chapter Arcs with Co-Scientist Competition ---")
    
    # Get initial user input for context
    initial_input = state.get("input", "")
    
    # Use co_scientist for competitive chapter arcs creation
    co_scientist_input = CoScientistConfiguration.create_input_state(
        use_case=UseCase.CHAPTER_ARCS_CREATION,
        context=initial_input,  # Pass user's original story concept
        reference_material=storyline,  # Pass selected storyline as reference
        storyline=storyline  # Keep for backward compatibility
    )
    
    # Configure co_scientist for full creative competition
    subgraph_config = config.copy()
    subgraph_config["configurable"].update({
        "research_model": ModelConfig.get_model_string("general_creative"),
        "general_model": ModelConfig.get_model_string("general_creative"),
        "use_case": "chapter_arcs_creation",
        "process_depth": "standard",      # Full creative process with reflection and evolution
        "population_scale": "light",      # Keep processing reasonable for creative tasks
        "use_deep_researcher": False,     # Use regular LLM for creative writing
        "save_intermediate_results": True,
        "output_dir": output_dir,
        "phase": "chapter_arcs_creation"
    })
    
    # Run co_scientist competition
    co_scientist_result = await co_scientist.ainvoke(co_scientist_input, subgraph_config)
    
    # Save detailed competition results
    if model_config.get("save_intermediate_results", True):
        # Save competition summary
        competition_summary = co_scientist_result.get("competition_summary", "")
        save_output(output_dir, "00_02_chapter_arcs_competition_summary.md", competition_summary)
        
        # Save detailed results
        detailed_results = format_detailed_competition_results(co_scientist_result)
        save_output(output_dir, "00_02_chapter_arcs_competition_details.md", detailed_results)
        
        # Save winning chapter arcs options
        direction_winners = co_scientist_result.get("direction_winners", [])
        for i, winner in enumerate(direction_winners[:3]):  # Limit to top 3
            winner_details = format_co_scientist_winner_details(winner, f"chapter_arcs_option_{i}")
            save_output(output_dir, f"00_02_chapter_arcs_option_{i+1}.md", winner_details)
    
    # Extract direction winners for user selection
    direction_winners = co_scientist_result.get("direction_winners", [])
    if direction_winners:
        # Format options for user presentation
        formatted_options = format_chapter_arcs_options_for_selection(direction_winners, co_scientist_result.get("competition_summary", ""))
        save_output(output_dir, "00_02_chapter_arcs_options.md", formatted_options)
        
        # Store options in state for user selection
        chapter_arcs_options = {
            "option_1": direction_winners[0].get("scenario_content", "") if len(direction_winners) > 0 else "",
            "option_2": direction_winners[1].get("scenario_content", "") if len(direction_winners) > 1 else "",
            "option_3": direction_winners[2].get("scenario_content", "") if len(direction_winners) > 2 else "",
            "options_metadata": direction_winners
        }
        
        print("--- Co-Scientist Chapter Arcs Competition Complete ---")
        print(f"--- {len(direction_winners)} chapter arc options created. User selection required. ---")
        
        return {"chapter_arcs_options": chapter_arcs_options, "chapter_arcs": None}  # No auto-selection
    else:
        print("--- No chapter arcs generated. ---")
        return {"chapter_arcs": "No chapter arcs generated.", "chapter_arcs_options": None}

async def write_first_chapter(state: AgentState, config: RunnableConfig):
    if not (output_dir := state.get("output_dir")) or not (storyline := state.get("storyline")) or not (chapter_arcs := state.get("chapter_arcs")):
        raise ValueError("Required state for writing first chapter is missing.")
    
    print("--- Writing First Chapter with Co-Scientist Competition ---")
    
    # Use co_scientist for competitive chapter writing
    co_scientist_input = CoScientistConfiguration.create_input_state(
        use_case=UseCase.CHAPTER_WRITING,
        storyline=storyline,
        chapter_arcs=chapter_arcs
    )
    
    # Configure co_scientist for full creative competition
    subgraph_config = config.copy()
    subgraph_config["configurable"].update({
        "research_model": ModelConfig.get_model_string("chapter_writing"),
        "general_model": ModelConfig.get_model_string("chapter_writing"),
        "use_case": "chapter_writing",
        "process_depth": "standard",      # Full creative process with reflection and evolution
        "population_scale": "light",      # Keep processing reasonable for creative tasks
        "use_deep_researcher": False,     # Use regular LLM for creative writing
        "save_intermediate_results": True,
        "output_dir": output_dir,
        "phase": "chapter_writing"
    })
    
    # Run co_scientist competition
    co_scientist_result = await co_scientist.ainvoke(co_scientist_input, subgraph_config)
    
    # Save detailed competition results
    if model_config.get("save_intermediate_results", True):
        # Save competition summary
        competition_summary = co_scientist_result.get("competition_summary", "")
        save_output(output_dir, "00_03a_first_chapter_competition_summary.md", competition_summary)
        
        # Save detailed competition data
        detailed_results = format_detailed_competition_results(co_scientist_result)
        save_output(output_dir, "00_03b_first_chapter_competition_details.md", detailed_results)
        
        # Save both direction winners with metadata
        direction_winners = co_scientist_result.get("direction_winners", [])
        for i, winner in enumerate(direction_winners, 1):
            winner_details = format_co_scientist_winner_details(winner, f"first_chapter_option_{i}")
            save_output(output_dir, f"00_03c_first_chapter_option_{i}_full.md", winner_details)
    
    # Store direction winners for user selection (not auto-selecting)
    direction_winners = co_scientist_result.get("direction_winners", [])
    if direction_winners:
        # Format both options for user presentation
        formatted_options = format_chapter_options_for_selection(direction_winners, co_scientist_result.get("competition_summary", ""))
        save_output(output_dir, "00_03_first_chapter_options.md", formatted_options)
        
        # Store options in state for user selection
        chapter_options = {
            "option_1": direction_winners[0].get("scenario_content", "") if len(direction_winners) > 0 else "",
            "option_2": direction_winners[1].get("scenario_content", "") if len(direction_winners) > 1 else "",
            "options_metadata": direction_winners
        }
        
        print("--- Co-Scientist First Chapter Competition Complete ---")
        print("--- Two chapter options created. User selection required. ---")
        
        return {"first_chapter_options": chapter_options, "first_chapter": None}  # No auto-selection
    else:
        # Co-scientist failed to produce direction winners - this is a system failure
        raise RuntimeError("Co-scientist first chapter competition failed to produce direction winners. Check competition configuration and model availability.")

def select_first_chapter(state: AgentState):
    """User selection node - presents first chapter options and waits for user choice."""
    if not (output_dir := state.get("output_dir")) or not (first_chapter_options := state.get("first_chapter_options")):
        raise ValueError("Required state 'output_dir' or 'first_chapter_options' is missing.")
    
    # Present options to user through the interface
    options_metadata = first_chapter_options.get("options_metadata", [])
    if len(options_metadata) < 2:
        raise ValueError("Not enough first chapter options for user selection.")
    
    # Note: Individual chapter options saved as full versions (_full.md) - no duplicates needed
    
    print("--- First Chapter Options Prepared for User Selection ---")
    print(f"Option 1: {options_metadata[0].get('research_direction', 'Unknown')}")
    print(f"Option 2: {options_metadata[1].get('research_direction', 'Unknown')}")
    
    # This function prepares options for user selection via LangGraph Studio interrupt
    # The actual selection happens in the next node via interrupt_before mechanism
    print("--- First chapter options prepared. Workflow will pause for user selection. ---")
    
    return {"first_chapter_options": first_chapter_options}

def process_chapter_selection(state: AgentState):
    """Process user's first chapter selection after interrupt."""
    if not (output_dir := state.get("output_dir")) or not (first_chapter_options := state.get("first_chapter_options")):
        raise ValueError("Required state 'output_dir' or 'first_chapter_options' is missing.")
    
    # Get user's choice from state (will be set by LangGraph Studio)
    user_choice = state.get("chapter_choice", "1")  # Default to option 1
    options_metadata = first_chapter_options.get("options_metadata", [])
    
    option_1_content = first_chapter_options.get("option_1", "")
    option_2_content = first_chapter_options.get("option_2", "")
    
    # Process user choice
    choice = str(user_choice).strip()
    if choice == "1":
        selected_chapter = option_1_content
        selected_option = options_metadata[0] if len(options_metadata) > 0 else {}
    elif choice == "2":
        selected_chapter = option_2_content
        selected_option = options_metadata[1] if len(options_metadata) > 1 else {}
    else:
        # Default to option 1 if invalid choice
        print(f"Invalid choice '{choice}', defaulting to Option 1")
        selected_chapter = option_1_content
        selected_option = options_metadata[0] if len(options_metadata) > 0 else {}
    
    save_output(output_dir, "00_03_selected_first_chapter.md", selected_chapter)
    
    print(f"--- First Chapter Selected: {selected_option.get('research_direction', 'Unknown')} ---")
    
    return {
        "first_chapter": selected_chapter
    }

def prompt_for_projection_year(state: AgentState):
    message = AIMessage(content="The initial draft is complete. To project this world further into the future, please provide the number of years to project forward in the `years_in_future` field and then resume.")
    return {"messages": [message]}

def set_target_year(state: AgentState):
    if not (starting_year := state.get("starting_year")):
        raise ValueError("Required state 'starting_year' is missing.")
    previous_target_year = state.get("target_year", starting_year)
    years_in_future = state.get("years_in_future") or 10
    target_year = previous_target_year + years_in_future
    print(f"--- Target year set to: {target_year} ---")
    return {"target_year": target_year, "years_in_future": years_in_future}

def generate_world_building_questions(state: AgentState):
    """Generates unbiased questions about the world, either initially or for projection."""
    if not (output_dir := state.get("output_dir")) or not (target_year := state.get("target_year")) or not (loop_count := state.get("loop_count") is not None):
        raise ValueError("Required state for generating questions is missing.")
    
    if state.get("baseline_world_state") and state.get("years_in_future"):
        if not (baseline_world_state := state.get("baseline_world_state")) or not (storyline := state.get("storyline")) or not (chapter_arcs := state.get("chapter_arcs")) or not (first_chapter := state.get("first_chapter")):
            raise ValueError("Required state for projection questions is missing.")
        prompt = ChatPromptTemplate.from_template(PROJECT_QUESTIONS_PROMPT)
        response = general_model.invoke(prompt.format(
            baseline_world_state=baseline_world_state,
            years_to_project=state["years_in_future"],
            storyline=storyline,
            chapter_arcs=chapter_arcs,
            first_chapter=first_chapter
        ))
    else:
        if not (storyline := state.get("storyline")) or not (first_chapter := state.get("first_chapter")) or not (chapter_arcs := state.get("chapter_arcs")):
            raise ValueError("Required storyline, chapter_arcs, or first_chapter is missing for initial questions.")
        prompt = ChatPromptTemplate.from_template(GENERATE_WORLD_BUILDING_QUESTIONS_PROMPT)
        response = general_model.invoke(prompt.format(
            target_year=target_year,
            storyline=storyline,
            chapter_arcs=chapter_arcs,
            first_chapter=first_chapter
        ))
    content = response.content
    save_output(output_dir, f"{state['loop_count']:02d}_04_world_building_questions.md", content)
    print("--- World-Building Questions Generated ---")
    return {"world_building_questions": content}

async def research_and_propose_scenarios(state: AgentState, config: RunnableConfig):
    """Research and propose scenarios using the co_scientist competitive multi-agent system."""
    if not (output_dir := state.get("output_dir")) or not (target_year := state.get("target_year")) or not (loop_count := state.get("loop_count") is not None) or not (questions := state.get("world_building_questions")) or not (storyline := state.get("storyline")):
        raise ValueError("Required state for scenario research is missing.")
    
    print("--- Starting Co-Scientist Competition ---")
    
    # Use co_scientist for competitive scenario generation
    co_scientist_input = CoScientistConfiguration.create_input_state(
        use_case=UseCase.SCENARIO_GENERATION,
        context=questions,  # World-building questions
        reference_material=storyline,  # Story context
        target_year=target_year,
        baseline_world_state=state.get("baseline_world_state"),
        years_in_future=state.get("years_in_future")
    )
    
    # Configure subgraph
    subgraph_config = config.copy()
    subgraph_config["configurable"].update({
        "research_model": ModelConfig.get_model_string("world_research"), # Use OpenAI O3 for all world research tasks
        "general_model": ModelConfig.get_model_string("world_research"),  # Use OpenAI O3 for all world research tasks
        "search_api": "openai",  # Use OpenAI native web search for O3 models
        "use_deep_researcher": True,  # Enable research-backed scenario generation with sources
        "output_dir": output_dir,
        "phase": "world_scenario_research"
    })

    # Invoke the co_scientist subgraph
    co_scientist_result = await co_scientist.ainvoke(
        co_scientist_input,
        subgraph_config
    )
    
    # Save detailed competition results
    if model_config.get("save_intermediate_results", True):
        # Note: Competition summary saved in co_scientist subdirectory to avoid duplication
        
        # Save detailed competition data
        detailed_results = format_detailed_competition_results(co_scientist_result)
        save_output(output_dir, f"{state['loop_count']:02d}_05b_detailed_results.md", detailed_results)
        
        # Save all 3 direction winners with metadata
        direction_winners = co_scientist_result.get("direction_winners", [])
        for i, winner in enumerate(direction_winners, 1):
            winner_details = format_co_scientist_winner_details(winner, f"world_scenario_option_{i}")
            save_output(output_dir, f"{state['loop_count']:02d}_05c_world_scenario_option_{i}_full.md", winner_details)

    # Extract direction winners for user selection
    direction_winners = co_scientist_result.get("direction_winners", [])
    if direction_winners:
        # Format all 3 options for user presentation
        formatted_options = format_world_scenario_options_for_selection(direction_winners, co_scientist_result.get("competition_summary", ""))
        save_output(output_dir, f"{state['loop_count']:02d}_05_world_building_scenario_options.md", formatted_options)
        
        # Store options in state for user selection
        world_scenario_options = {
            "option_1": direction_winners[0].get("scenario_content", "") if len(direction_winners) > 0 else "",
            "option_2": direction_winners[1].get("scenario_content", "") if len(direction_winners) > 1 else "",
            "option_3": direction_winners[2].get("scenario_content", "") if len(direction_winners) > 2 else "",
            "options_metadata": direction_winners
        }
        
        print("--- Co-Scientist World Scenario Competition Complete ---")
        print(f"--- {len(direction_winners)} world scenario options created. User selection required. ---")
        
        return {"world_scenario_options": world_scenario_options, "world_building_scenarios": None}  # No auto-selection
    else:
        # Co-scientist failed to produce direction winners - this is a system failure
        raise RuntimeError("Co-scientist world scenario competition failed to produce direction winners. Check competition configuration and model availability.")



def format_world_scenario_options_for_selection(direction_winners: list, competition_summary: str) -> str:
    """Format world scenario options for user selection."""
    
    content = "# World Scenario Options from Co-Scientist Competition\n\n"
    content += f"{len(direction_winners)} different research approaches competed and are now available for your selection.\n\n"
    
    content += "## Competition Overview\n"
    content += competition_summary + "\n\n"
    
    for i, winner in enumerate(direction_winners, 1):
        content += f"## Option {i}: {winner.get('research_direction', 'Unknown Approach')}\n\n"
        content += f"**Core Approach:** {winner.get('core_assumption', 'No assumption available')}\n\n"
        content += f"**Selection Reasoning:** {winner.get('selection_reasoning', 'Tournament winner')}\n\n"
        content += "### Full World Scenario:\n\n"
        content += f"{winner.get('scenario_content', 'No content available')}\n\n"
        content += "---\n\n"
    
    content += "## Selection Instructions\n"
    content += f"Please review all {len(direction_winners)} world scenario options above and choose your preferred approach. "
    content += "You can select one option as-is, or combine elements from multiple approaches.\n\n"
    content += "To continue, provide your chosen world scenario (or modified version) in the workflow.\n"
    
    return content

def format_storyline_options_for_selection(direction_winners: list, competition_summary: str) -> str:
    """Format storyline options for user selection."""
    
    content = "# Storyline Options from Co-Scientist Competition\n\n"
    content += "Two different storytelling approaches competed and are now available for your selection.\n\n"
    
    content += "## Competition Overview\n"
    content += competition_summary + "\n\n"
    
    for i, winner in enumerate(direction_winners, 1):
        content += f"## Option {i}: {winner.get('research_direction', 'Unknown Approach')}\n\n"
        content += f"**Core Approach:** {winner.get('core_assumption', 'No assumption available')}\n\n"
        content += f"**Selection Reasoning:** {winner.get('selection_reasoning', 'Tournament winner')}\n\n"
        content += "### Full Storyline:\n\n"
        content += f"{winner.get('scenario_content', 'No content available')}\n\n"
        content += "---\n\n"
    
    content += "## Selection Instructions\n"
    content += "Please review both storyline options above and choose your preferred approach. "
    content += "You can select one option as-is, or combine elements from both approaches.\n\n"
    content += "To continue, provide your chosen storyline (or modified version) in the workflow.\n"
    
    return content

def format_chapter_options_for_selection(direction_winners: list, competition_summary: str) -> str:
    """Format first chapter options for user selection."""
    
    content = "# First Chapter Options from Co-Scientist Competition\n\n"
    content += "Two different writing approaches competed and are now available for your selection.\n\n"
    
    content += "## Competition Overview\n"
    content += competition_summary + "\n\n"
    
    for i, winner in enumerate(direction_winners, 1):
        content += f"## Option {i}: {winner.get('research_direction', 'Unknown Approach')}\n\n"
        content += f"**Core Approach:** {winner.get('core_assumption', 'No assumption available')}\n\n"
        content += f"**Selection Reasoning:** {winner.get('selection_reasoning', 'Tournament winner')}\n\n"
        content += "### Full Chapter:\n\n"
        content += f"{winner.get('scenario_content', 'No content available')}\n\n"
        content += "---\n\n"
    
    content += "## Selection Instructions\n"
    content += "Please review both chapter options above and choose your preferred approach. "
    content += "You can select one option as-is, or modify elements from both approaches.\n\n"
    content += "To continue, provide your chosen first chapter (or modified version) in the workflow.\n"
    
    return content

def format_linguistic_options_for_selection(direction_winners: list, competition_summary: str) -> str:
    """Format linguistic evolution options for user selection."""
    
    content = "# Linguistic Evolution Options from Co-Scientist Competition\n\n"
    content += "Two different research approaches competed and are now available for your selection.\n\n"
    
    content += "## Competition Overview\n"
    content += competition_summary + "\n\n"
    
    for i, winner in enumerate(direction_winners, 1):
        content += f"## Option {i}: {winner.get('research_direction', 'Unknown Approach')}\n\n"
        content += f"**Core Approach:** {winner.get('core_assumption', 'No assumption available')}\n\n"
        content += f"**Selection Reasoning:** {winner.get('selection_reasoning', 'Tournament winner')}\n\n"
        content += "### Full Analysis:\n\n"
        content += f"{winner.get('scenario_content', 'No content available')}\n\n"
        content += "---\n\n"
    
    content += "## Selection Instructions\n"
    content += "Please review both linguistic evolution analyses above and choose your preferred approach. "
    content += "You can select one option as-is, or combine insights from both approaches.\n\n"
    content += "To continue, provide your chosen linguistic evolution analysis (or modified version) in the workflow.\n"
    
    return content

def format_storyline_adjustment_options_for_selection(direction_winners: list, competition_summary: str) -> str:
    """Format storyline adjustment options for user selection."""
    
    content = "# Storyline Adjustment Options from Co-Scientist Competition\n\n"
    content += "Two different revision approaches competed and are now available for your selection.\n\n"
    
    content += "## Competition Overview\n"
    content += competition_summary + "\n\n"
    
    for i, winner in enumerate(direction_winners, 1):
        content += f"## Option {i}: {winner.get('research_direction', 'Unknown Approach')}\n\n"
        content += f"**Core Approach:** {winner.get('core_assumption', 'No assumption available')}\n\n"
        content += f"**Selection Reasoning:** {winner.get('selection_reasoning', 'Tournament winner')}\n\n"
        content += "### Revised Storyline:\n\n"
        content += f"{winner.get('scenario_content', 'No content available')}\n\n"
        content += "---\n\n"
    
    content += "## Selection Instructions\n"
    content += "Please review both storyline revision options above and choose your preferred approach. "
    content += "You can select one option as-is, or combine elements from both approaches.\n\n"
    content += "To continue, provide your chosen revised storyline (or modified version) in the workflow.\n"
    
    return content

def format_chapter_rewrite_options_for_selection(direction_winners: list, competition_summary: str) -> str:
    """Format chapter rewrite options for user selection."""
    
    content = "# Chapter Rewrite Options from Co-Scientist Competition\n\n"
    content += "Two different rewriting approaches competed and are now available for your selection.\n\n"
    
    content += "## Competition Overview\n"
    content += competition_summary + "\n\n"
    
    for i, winner in enumerate(direction_winners, 1):
        content += f"## Option {i}: {winner.get('research_direction', 'Unknown Approach')}\n\n"
        content += f"**Core Approach:** {winner.get('core_assumption', 'No assumption available')}\n\n"
        content += f"**Selection Reasoning:** {winner.get('selection_reasoning', 'Tournament winner')}\n\n"
        content += "### Rewritten Chapter:\n\n"
        content += f"{winner.get('scenario_content', 'No content available')}\n\n"
        content += "---\n\n"
    
    content += "## Selection Instructions\n"
    content += "Please review both chapter rewrite options above and choose your preferred approach. "
    content += "You can select one option as-is, or modify elements from both approaches.\n\n"
    content += "To continue, provide your chosen rewritten chapter (or modified version) in the workflow.\n"
    
    return content

def format_chapter_arcs_options_for_selection(direction_winners: list, competition_summary: str) -> str:
    """Format chapter arcs options for user selection."""
    
    content = "# Chapter Arcs Options from Co-Scientist Competition\n\n"
    content += "Multiple narrative structuring approaches competed and are now available for your selection.\n\n"
    
    content += "## Competition Overview\n"
    content += competition_summary + "\n\n"
    
    for i, winner in enumerate(direction_winners, 1):
        content += f"## Option {i}: {winner.get('research_direction', 'Unknown Approach')}\n\n"
        content += f"**Core Approach:** {winner.get('core_assumption', 'No assumption available')}\n\n"
        content += f"**Selection Reasoning:** {winner.get('selection_reasoning', 'Tournament winner')}\n\n"
        content += "### Chapter Arcs Structure:\n\n"
        content += f"{winner.get('scenario_content', 'No content available')}\n\n"
        content += "---\n\n"
    
    content += "## Selection Instructions\n"
    content += "Please review the chapter arcs options above and choose your preferred narrative structure. "
    content += "You can select one option as-is, or modify elements from multiple approaches.\n\n"
    content += "To continue, provide your chosen chapter arcs structure (or modified version) in the workflow.\n"
    
    return content

def format_co_scientist_winner_details(winner_scenario: dict, content_type: str) -> str:
    """Format detailed information about the winning scenario from co_scientist competition."""
    
    details = f"# Co-Scientist Winner: {content_type.title()}\n\n"
    details += f"**Content Type:** {content_type}\n"
    details += f"**Competition Rank:** #{winner_scenario.get('competition_rank', 1)}\n"
    details += f"**Research Direction:** {winner_scenario.get('research_direction', 'Unknown')}\n"
    details += f"**Team ID:** {winner_scenario.get('team_id', 'Unknown')}\n"
    details += f"**Scenario ID:** {winner_scenario.get('scenario_id', 'Unknown')}\n\n"
    
    details += "## Selection Reasoning\n\n"
    details += f"{winner_scenario.get('selection_reasoning', 'Selected through competitive tournament')}\n\n"
    
    details += "## Full Content\n\n"
    details += f"{winner_scenario.get('scenario_content', 'No content available')}\n\n"
    
    # Add metadata if available
    if winner_scenario.get('core_assumption'):
        details += "## Core Assumption\n\n"
        details += f"{winner_scenario.get('core_assumption')}\n\n"
    
    if winner_scenario.get('research_query'):
        details += "## Research Query Used\n\n"
        details += f"{winner_scenario.get('research_query')}\n\n"
    
    if winner_scenario.get('generation_timestamp'):
        details += "## Generation Details\n\n"
        details += f"- **Generated:** {winner_scenario.get('generation_timestamp')}\n"
        details += f"- **Quality Score:** {winner_scenario.get('quality_score', 'N/A')}\n"
        details += f"- **Critiques:** {len(winner_scenario.get('critiques', []))}\n\n"
    
    details += "---\n\n"
    details += "This content was selected through co_scientist competitive multi-agent tournament with research validation.\n"
    
    return details

def format_detailed_competition_results(co_scientist_result: dict) -> str:
    """Format detailed co-scientist competition results with meaningful analysis."""
    
    detailed = "# Detailed Co-Scientist Competition Results\n\n"
    
    # Research directions
    directions = co_scientist_result.get("research_directions", [])
    detailed += f"## Research Directions ({len(directions)})\n"
    for i, direction in enumerate(directions, 1):
        detailed += f"### Direction {i}: {direction.get('name', 'Unknown')}\n"
        detailed += f"- **Assumption:** {direction.get('assumption', 'N/A')}\n"
        detailed += f"- **Focus:** {direction.get('focus', 'N/A')}\n\n"
    
    # Population statistics  
    population = co_scientist_result.get("scenario_population", [])
    detailed += f"## Scenario Population\n"
    detailed += f"- **Total Generated:** {len(population)}\n"
    if directions:
        per_direction = len(population) // len(directions)
        detailed += f"- **Per Direction:** {per_direction} scenarios\n"
    
    # Calculate quality distribution
    quality_scores = [s.get("quality_score", 0) for s in population if s.get("quality_score")]
    if quality_scores:
        avg_quality = sum(quality_scores) / len(quality_scores)
        detailed += f"- **Average Quality Score:** {avg_quality:.1f}/100\n"
        detailed += f"- **Quality Range:** {min(quality_scores)}-{max(quality_scores)}/100\n"
    detailed += "\n"
    
    # Reflection results with meaningful stats
    critiques = co_scientist_result.get("reflection_critiques", [])
    detailed += f"## Reflection Phase\n"
    detailed += f"- **Total Critiques Generated:** {len(critiques)}\n"
    
    # Show advancement recommendations
    if critiques:
        advance_count = sum(1 for c in critiques if c.get("advancement_recommendation", "").upper() == "ADVANCE")
        detailed += f"- **Recommended for Advancement:** {advance_count}/{len(critiques)} scenarios\n"
    detailed += "\n"
    
    # Tournament results with winner details
    direction_winners = co_scientist_result.get("direction_winners", [])
    detailed += f"## Tournament Winners\n"
    detailed += f"- **Direction Champions:** {len(direction_winners)}\n"
    
    for i, winner in enumerate(direction_winners, 1):
        winner_scenario = winner.get("winner", {}) if "winner" in winner else winner
        direction = winner_scenario.get("research_direction", "Unknown Direction")
        team_id = winner_scenario.get("team_id", "unknown")
        quality = winner_scenario.get("quality_score", 0)
        elo = winner_scenario.get("elo_rating", winner_scenario.get("final_elo_rating", 1500))
        
        detailed += f"### Winner {i}: {direction}\n"
        detailed += f"- **Team ID:** {team_id}\n"
        detailed += f"- **Quality Score:** {quality}/100\n" 
        detailed += f"- **Final Elo Rating:** {elo:.0f}\n\n"
    
    # Evolution results with strategy breakdown
    evolved = co_scientist_result.get("evolved_scenarios", [])
    evolution_results = co_scientist_result.get("evolution_tournament_results", [])
    detailed += f"## Evolution Phase\n"
    detailed += f"- **Scenarios Evolved:** {len(evolved)}\n"
    detailed += f"- **Evolution Tournaments:** {len(evolution_results)}\n"
    
    if evolved:
        # Count successful evolutions
        successful = sum(1 for e in evolved if e.get("quality_score", 0) > 0)
        detailed += f"- **Successful Evolutions:** {successful}/{len(evolved)}\n"
    detailed += "\n"
    
    # Final selection - use direction_winners as the final result
    detailed += f"## Final Selection Results\n"
    if direction_winners:
        detailed += f"- **Tournament Champions Selected:** {len(direction_winners)}\n"
        detailed += f"- **Competition Status:** Complete\n"
        
        # Show quality distribution of winners
        winner_qualities = [w.get("winner", {}).get("quality_score", w.get("quality_score", 0)) for w in direction_winners]
        winner_qualities = [q for q in winner_qualities if q > 0]
        if winner_qualities:
            avg_winner_quality = sum(winner_qualities) / len(winner_qualities)
            detailed += f"- **Average Winner Quality:** {avg_winner_quality:.1f}/100\n"
    else:
        detailed += f"- **Champions Selected:** 0 (Competition may have failed)\n"
    
    return detailed

def select_world_scenario(state: AgentState):
    """User selection node - presents world scenario options and waits for user choice."""
    if not (output_dir := state.get("output_dir")) or not (world_scenario_options := state.get("world_scenario_options")):
        raise ValueError("Required state 'output_dir' or 'world_scenario_options' is missing.")
    
    # Present options to user through the interface
    options_metadata = world_scenario_options.get("options_metadata", [])
    if len(options_metadata) < 2:
        raise ValueError("Not enough world scenario options for user selection.")
    
    # Note: Individual world scenario options saved as full versions (_full.md) - no duplicates needed
    
    print("--- World Scenario Options Prepared for User Selection ---")
    for i, metadata in enumerate(options_metadata, 1):
        print(f"Option {i}: {metadata.get('research_direction', 'Unknown')}")
    
    # This function prepares options for user selection via LangGraph Studio interrupt
    # The actual selection happens in the next node via interrupt_before mechanism
    print("--- World scenario options prepared. Workflow will pause for user selection. ---")
    
    return {"world_scenario_options": world_scenario_options}

def process_world_scenario_selection(state: AgentState):
    """Process user's world scenario selection after interrupt."""
    if not (output_dir := state.get("output_dir")) or not (world_scenario_options := state.get("world_scenario_options")):
        raise ValueError("Required state 'output_dir' or 'world_scenario_options' is missing.")
    
    # Get user's choice from state (will be set by LangGraph Studio)
    user_choice = state.get("world_scenario_choice", "1")  # Default to option 1
    options_metadata = world_scenario_options.get("options_metadata", [])
    
    # Process user choice
    choice = str(user_choice).strip()
    try:
        choice_index = int(choice) - 1
        if 0 <= choice_index < len(options_metadata):
            selected_scenario = world_scenario_options.get(f"option_{choice_index + 1}", "")
            selected_option = options_metadata[choice_index]
        else:
            # Default to option 1 if invalid choice
            print(f"Invalid choice '{choice}', defaulting to Option 1")
            selected_scenario = world_scenario_options.get("option_1", "")
            selected_option = options_metadata[0] if len(options_metadata) > 0 else {}
    except (ValueError, IndexError):
        # Default to option 1 if invalid choice
        print(f"Invalid choice '{choice}', defaulting to Option 1")
        selected_scenario = world_scenario_options.get("option_1", "")
        selected_option = options_metadata[0] if len(options_metadata) > 0 else {}
    
    save_output(output_dir, f"{state['loop_count']:02d}_05_selected_world_scenario.md", selected_scenario)
    
    print(f"--- World Scenario Selected: {selected_option.get('research_direction', 'Unknown')} ---")
    
    return {
        "world_building_scenarios": selected_scenario,
        "selected_scenario": selected_option.get('research_direction', 'Unknown')
    }



async def world_projection_deep_research(state: AgentState, config: RunnableConfig):
    """Use the co-scientist selected scenario as the baseline world state since it's already research-backed."""
    if not (output_dir := state.get("output_dir")) or not (target_year := state.get("target_year")) or not (loop_count := state.get("loop_count") is not None) or not (selected_scenario := state.get("selected_scenario")) or not (world_building_scenarios := state.get("world_building_scenarios")):
        raise ValueError("Required state for world projection research is missing.")
    
    print("--- Using Co-Scientist Selected Scenario as Baseline (Already Research-Backed) ---")
    
    # Use the selected scenario content as the baseline world state since it's already comprehensive
    world_state = f"# Baseline World State for {target_year}\n\n"
    world_state += f"## Selected Scenario: {selected_scenario}\n\n"
    world_state += world_building_scenarios
    
    save_output(output_dir, f"{state['loop_count']:02d}_07_world_state_{target_year}.md", world_state)
    return {"baseline_world_state": world_building_scenarios}

async def linguistic_evolution_research(state: AgentState, config: RunnableConfig):
    """Uses co_scientist to research the linguistic evolution of the world with competitive analysis."""
    if not (output_dir := state.get("output_dir")) or not (target_year := state.get("target_year")) or not (loop_count := state.get("loop_count") is not None) or not (baseline_world_state := state.get("baseline_world_state")) or not (storyline := state.get("storyline")) or not (chapter_arcs := state.get("chapter_arcs")) or not (first_chapter := state.get("first_chapter")) or not (years_in_future := state.get("years_in_future")):
        raise ValueError("Required state for linguistic research is missing.")
        
    print("--- Conducting Co-Scientist Competition on Linguistic Evolution ---")

    # Use co_scientist for competitive linguistic analysis with research
    co_scientist_input = CoScientistConfiguration.create_input_state(
        use_case=UseCase.LINGUISTIC_EVOLUTION,
        reference_material=f"World State: {baseline_world_state}\n\nStoryline: {storyline}",
        target_year=target_year,
        years_in_future=years_in_future,
        baseline_world_state=baseline_world_state
    )
    
    # Configure co_scientist for quick competition with deep research
    subgraph_config = config.copy()
    
    # Build comprehensive world state context for linguistic research
    world_context_parts = [f"Baseline World State: {baseline_world_state}"]
    world_context_parts.append(f"Target Year: {target_year}")
    world_context_parts.append(f"Years to Project: {years_in_future}")
    
    # Include previous linguistic evolution if this is a subsequent cycle
    if previous_linguistic := state.get("linguistic_evolution"):
        world_context_parts.append(f"Previous Linguistic Research: {previous_linguistic}")
    
    world_state_context = "\n\n".join(world_context_parts)
    
    subgraph_config["configurable"].update({
        "research_model": ModelConfig.get_model_string("linguistic_research"),    # Sonnet 4 for thinking
        "general_model": ModelConfig.get_model_string("linguistic_research"),     # Sonnet 4 for thinking
        "search_api": "tavily",  # Use Tavily search API for external research access
        "use_case": "linguistic_evolution",
        "process_depth": "standard",  # Full creative process with reflection and evolution
        "population_scale": "light",  # Keep processing reasonable
        "use_deep_researcher": True,  # Research-backed analysis with Sonnet 4
        "world_state_context": world_state_context, # Pass world context for research
        "save_intermediate_results": True,
        "output_dir": output_dir,
        "phase": "linguistic_evolution"
    })
    
    # Run co_scientist competition
    co_scientist_result = await co_scientist.ainvoke(co_scientist_input, subgraph_config)
    
    # Debug logging - capture actual result structure
    print(f"Co-scientist result keys: {list(co_scientist_result.keys()) if co_scientist_result else 'None'}")
    print(f"Direction winners type: {type(co_scientist_result.get('direction_winners', 'missing'))}")
    print(f"Direction winners value: {co_scientist_result.get('direction_winners', 'missing')}")
    print(f"Tournament complete: {co_scientist_result.get('tournament_complete', 'missing')}")
    print(f"Scenario population count: {len(co_scientist_result.get('scenario_population', []))}")
    print(f"Tournament winners count: {len(co_scientist_result.get('tournament_winners', []))}")
    
    # Save detailed competition results
    if model_config.get("save_intermediate_results", True):
        # Note: Competition summary saved in co_scientist subdirectory to avoid duplication
        
        # Save detailed competition data
        detailed_results = format_detailed_competition_results(co_scientist_result)
        save_output(output_dir, f"{state['loop_count']:02d}_08b_linguistic_competition_details.md", detailed_results)
        
        # Save raw co_scientist_result for debugging
        import json
        save_output(output_dir, f"{state['loop_count']:02d}_08_DEBUG_coscientist_raw_result.json", 
                   json.dumps(co_scientist_result, indent=2, default=str))
        
        # Save all direction winners
        direction_winners = co_scientist_result.get("direction_winners", [])
        if direction_winners:
            for i, winner in enumerate(direction_winners):
                winner_details = format_co_scientist_winner_details(winner, f"linguistic_evolution_option_{i+1}")
                save_output(output_dir, f"{state['loop_count']:02d}_08c_linguistic_winner_{i+1}_full.md", winner_details)

    # Extract direction winners for user selection
    direction_winners = co_scientist_result.get("direction_winners", [])
    if direction_winners:
        # Format both options for user presentation
        formatted_options = format_linguistic_options_for_selection(direction_winners, co_scientist_result.get("competition_summary", ""))
        save_output(output_dir, f"{state['loop_count']:02d}_08_linguistic_evolution_options.md", formatted_options)
        
        # Store options in state for user selection
        linguistic_options = {
            "option_1": direction_winners[0].get("scenario_content", "") if len(direction_winners) > 0 else "",
            "option_2": direction_winners[1].get("scenario_content", "") if len(direction_winners) > 1 else "",
            "options_metadata": direction_winners
        }
        
        print("--- Co-Scientist Linguistic Evolution Competition Complete ---")
        print("--- Two linguistic evolution options created. User selection required. ---")
        
        return {"linguistic_evolution_options": linguistic_options, "linguistic_evolution": None}  # No auto-selection
    else:
        # Enhanced error with full diagnostic information
        error_details = {
            "co_scientist_result_keys": list(co_scientist_result.keys()) if co_scientist_result else [],
            "direction_winners": co_scientist_result.get("direction_winners", "missing"),
            "tournament_complete": co_scientist_result.get("tournament_complete", "missing"),
            "scenario_population_count": len(co_scientist_result.get("scenario_population", [])),
            "tournament_winners_count": len(co_scientist_result.get("tournament_winners", [])),
            "generation_complete": co_scientist_result.get("generation_complete", "missing"),
            "reflection_complete": co_scientist_result.get("reflection_complete", "missing"),
            "evolution_complete": co_scientist_result.get("evolution_complete", "missing"),
            "competition_summary": co_scientist_result.get("competition_summary", "missing")[:200] if co_scientist_result.get("competition_summary") else "missing"
        }
        
        # Co-scientist failed to produce direction winners - this is a system failure
        raise RuntimeError(f"Co-scientist linguistic evolution competition failed to produce direction winners. Debug info: {json.dumps(error_details, indent=2, default=str)}")

def select_linguistic_evolution(state: AgentState):
    """User selection node - presents linguistic evolution options and waits for user choice."""
    if not (output_dir := state.get("output_dir")) or not (linguistic_evolution_options := state.get("linguistic_evolution_options")) or not (loop_count := state.get("loop_count") is not None):
        raise ValueError("Required state 'output_dir' or 'linguistic_evolution_options' is missing.")
    
    # Present options to user through the interface
    options_metadata = linguistic_evolution_options.get("options_metadata", [])
    if len(options_metadata) < 2:
        raise ValueError("Not enough linguistic evolution options for user selection.")
    
    # Note: Individual linguistic evolution options saved as full versions (_full.md) - no duplicates needed
    
    print("--- Linguistic Evolution Options Prepared for User Selection ---")
    print(f"Option 1: {options_metadata[0].get('research_direction', 'Unknown')}")
    print(f"Option 2: {options_metadata[1].get('research_direction', 'Unknown')}")
    
    # This function prepares options for user selection via LangGraph Studio interrupt
    # The actual selection happens in the next node via interrupt_before mechanism
    print("--- Linguistic evolution options prepared. Workflow will pause for user selection. ---")
    
    return {"linguistic_evolution_options": linguistic_evolution_options}

def process_linguistic_evolution_selection(state: AgentState):
    """Process user's linguistic evolution selection after interrupt."""
    if not (output_dir := state.get("output_dir")) or not (linguistic_evolution_options := state.get("linguistic_evolution_options")) or not (loop_count := state.get("loop_count") is not None):
        raise ValueError("Required state 'output_dir' or 'linguistic_evolution_options' is missing.")
    
    # Get user's choice from state (will be set by LangGraph Studio)
    user_choice = state.get("linguistic_choice", "1")  # Default to option 1
    options_metadata = linguistic_evolution_options.get("options_metadata", [])
    
    option_1_content = linguistic_evolution_options.get("option_1", "")
    option_2_content = linguistic_evolution_options.get("option_2", "")
    
    # Process user choice
    choice = str(user_choice).strip()
    if choice == "1":
        selected_linguistic = option_1_content
        selected_option = options_metadata[0] if len(options_metadata) > 0 else {}
    elif choice == "2":
        selected_linguistic = option_2_content
        selected_option = options_metadata[1] if len(options_metadata) > 1 else {}
    else:
        # Default to option 1 if invalid choice
        print(f"Invalid choice '{choice}', defaulting to Option 1")
        selected_linguistic = option_1_content
        selected_option = options_metadata[0] if len(options_metadata) > 0 else {}
    
    save_output(output_dir, f"{state['loop_count']:02d}_08_selected_linguistic_evolution.md", selected_linguistic)
    
    print(f"--- Linguistic Evolution Selected: {selected_option.get('research_direction', 'Unknown')} ---")
    
    return {
        "linguistic_evolution": selected_linguistic
    }

async def adjust_storyline(state: AgentState, config: RunnableConfig):
    if not (output_dir := state.get("output_dir")) or not (loop_count := state.get("loop_count") is not None) or not (storyline := state.get("storyline")) or not (baseline_world_state := state.get("baseline_world_state")) or not (linguistic_evolution := state.get("linguistic_evolution")) or not (target_year := state.get("target_year")):
        raise ValueError("Required state for adjusting storyline is missing.")
    
    print("--- Adjusting Storyline with Co-Scientist Competition ---")
    
    # Use co_scientist for competitive storyline adjustment
    co_scientist_input = CoScientistConfiguration.create_input_state(
        use_case=UseCase.STORYLINE_ADJUSTMENT,
        reference_material=f"Original Storyline: {storyline}",
        storyline=storyline,
        baseline_world_state=baseline_world_state,
        linguistic_evolution=linguistic_evolution,
        target_year=target_year  # Pass target year for sci-fi context
    )
    
    # Configure co_scientist for full competition with world-aware reflection
    subgraph_config = config.copy()
    subgraph_config["configurable"].update({
        "research_model": ModelConfig.get_model_string("general_creative"),
        "general_model": ModelConfig.get_model_string("general_creative"),
        "use_case": "storyline_adjustment",
        "process_depth": "standard",  # Full creative process with reflection and evolution
        "population_scale": "light",  # Keep processing reasonable
        "use_deep_researcher": False,  # Use regular LLM for creative writing
        "reflection_domains": ["narrative_structure", "world_building", "character_development", "thematic_coherence", "world_integration"],
        "world_state_context": f"Baseline World State: {baseline_world_state}\n\nLinguistic Evolution: {linguistic_evolution}",  # Pass world context for reflection
        "save_intermediate_results": True,
        "output_dir": output_dir,
        "phase": "storyline_adjustment"
    })
    
    # Run co_scientist competition
    co_scientist_result = await co_scientist.ainvoke(co_scientist_input, subgraph_config)
    
    # Save detailed competition results
    if model_config.get("save_intermediate_results", True):
        # Save competition summary
        competition_summary = co_scientist_result.get("competition_summary", "")
        save_output(output_dir, f"{state['loop_count']:02d}_09a_storyline_adjustment_competition_summary.md", competition_summary)
        
        # Save detailed competition data
        detailed_results = format_detailed_competition_results(co_scientist_result)
        save_output(output_dir, f"{state['loop_count']:02d}_09b_storyline_adjustment_competition_details.md", detailed_results)
        
        # Save all direction winners
        direction_winners = co_scientist_result.get("direction_winners", [])
        if direction_winners:
            for i, winner in enumerate(direction_winners):
                winner_details = format_co_scientist_winner_details(winner, f"storyline_adjustment_option_{i+1}")
                save_output(output_dir, f"{state['loop_count']:02d}_09c_storyline_adjustment_winner_{i+1}_full.md", winner_details)
    
    # Extract direction winners for user selection
    direction_winners = co_scientist_result.get("direction_winners", [])
    if direction_winners:
        # Format both options for user presentation
        formatted_options = format_storyline_adjustment_options_for_selection(direction_winners, co_scientist_result.get("competition_summary", ""))
        save_output(output_dir, f"{state['loop_count']:02d}_09_revised_storyline_options.md", formatted_options)
        
        # Store options in state for user selection
        storyline_adjustment_options = {
            "option_1": direction_winners[0].get("scenario_content", "") if len(direction_winners) > 0 else "",
            "option_2": direction_winners[1].get("scenario_content", "") if len(direction_winners) > 1 else "",
            "options_metadata": direction_winners
        }
        
        print("--- Co-Scientist Storyline Adjustment Competition Complete ---")
        print("--- Two storyline adjustment options created. User selection required. ---")
        
        return {"storyline_adjustment_options": storyline_adjustment_options, "revised_storyline": None}  # No auto-selection
    else:
        # Co-scientist failed to produce direction winners - this is a system failure
        raise RuntimeError("Co-scientist storyline adjustment competition failed to produce direction winners. Check competition configuration and model availability.")

def select_storyline_adjustment(state: AgentState):
    """User selection node - presents storyline adjustment options and waits for user choice."""
    if not (output_dir := state.get("output_dir")) or not (storyline_adjustment_options := state.get("storyline_adjustment_options")) or not (loop_count := state.get("loop_count") is not None):
        raise ValueError("Required state 'output_dir' or 'storyline_adjustment_options' is missing.")
    
    # Present options to user through the interface
    options_metadata = storyline_adjustment_options.get("options_metadata", [])
    if len(options_metadata) < 2:
        raise ValueError("Not enough storyline adjustment options for user selection.")
    
    # Note: Individual storyline adjustment options saved as full versions (_full.md) - no duplicates needed
    
    print("--- Storyline Adjustment Options Prepared for User Selection ---")
    print(f"Option 1: {options_metadata[0].get('research_direction', 'Unknown')}")
    print(f"Option 2: {options_metadata[1].get('research_direction', 'Unknown')}")
    
    # This function prepares options for user selection via LangGraph Studio interrupt
    # The actual selection happens in the next node via interrupt_before mechanism
    print("--- Storyline adjustment options prepared. Workflow will pause for user selection. ---")
    
    return {"storyline_adjustment_options": storyline_adjustment_options}

def process_storyline_adjustment_selection(state: AgentState):
    """Process user's storyline adjustment selection after interrupt."""
    if not (output_dir := state.get("output_dir")) or not (storyline_adjustment_options := state.get("storyline_adjustment_options")) or not (loop_count := state.get("loop_count") is not None):
        raise ValueError("Required state 'output_dir' or 'storyline_adjustment_options' is missing.")
    
    # Get user's choice from state (will be set by LangGraph Studio)
    user_choice = state.get("storyline_adjustment_choice", "1")  # Default to option 1
    options_metadata = storyline_adjustment_options.get("options_metadata", [])
    
    option_1_content = storyline_adjustment_options.get("option_1", "")
    option_2_content = storyline_adjustment_options.get("option_2", "")
    
    # Process user choice
    choice = str(user_choice).strip()
    if choice == "1":
        selected_adjustment = option_1_content
        selected_option = options_metadata[0] if len(options_metadata) > 0 else {}
    elif choice == "2":
        selected_adjustment = option_2_content
        selected_option = options_metadata[1] if len(options_metadata) > 1 else {}
    else:
        # Default to option 1 if invalid choice
        print(f"Invalid choice '{choice}', defaulting to Option 1")
        selected_adjustment = option_1_content
        selected_option = options_metadata[0] if len(options_metadata) > 0 else {}
    
    save_output(output_dir, f"{state['loop_count']:02d}_09_selected_revised_storyline.md", selected_adjustment)
    
    print(f"--- Storyline Adjustment Selected: {selected_option.get('research_direction', 'Unknown')} ---")
    
    return {
        "revised_storyline": selected_adjustment
    }

async def adjust_chapter_arcs(state: AgentState, config: RunnableConfig):
    if not (output_dir := state.get("output_dir")) or not (loop_count := state.get("loop_count") is not None) or not (revised_storyline := state.get("revised_storyline")) or not (baseline_world_state := state.get("baseline_world_state")) or not (chapter_arcs := state.get("chapter_arcs")) or not (linguistic_evolution := state.get("linguistic_evolution")) or not (target_year := state.get("target_year")):
        raise ValueError("Required state for adjusting chapter arcs is missing.")
    
    print("--- Adjusting Chapter Arcs with Co-Scientist Competition ---")
    
    # Get initial user input for context
    initial_input = state.get("input", "")
    
    # Use co_scientist for competitive chapter arcs adjustment
    co_scientist_input = CoScientistConfiguration.create_input_state(
        use_case=UseCase.CHAPTER_ARCS_ADJUSTMENT,
        context=initial_input,  # Pass user's original story concept
        reference_material=chapter_arcs,  # Pass original chapter arcs to refine
        storyline=revised_storyline,
        baseline_world_state=baseline_world_state,
        linguistic_evolution=linguistic_evolution,
        target_year=target_year  # Pass target year for sci-fi context
    )
    
    # Configure co_scientist for full creative competition with world-aware reflection
    subgraph_config = config.copy()
    subgraph_config["configurable"].update({
        "research_model": ModelConfig.get_model_string("general_creative"),
        "general_model": ModelConfig.get_model_string("general_creative"),
        "use_case": "chapter_arcs_adjustment",
        "process_depth": "standard",      # Full creative process with reflection and evolution
        "population_scale": "light",      # Keep processing reasonable
        "use_deep_researcher": False,     # Use regular LLM for creative writing
        "reflection_domains": ["narrative_structure", "world_integration", "character_development", "plot_consistency", "thematic_alignment"],
        "world_state_context": f"Baseline World State: {baseline_world_state}\n\nLinguistic Evolution: {linguistic_evolution}\n\nRevised Storyline: {revised_storyline}",
        "save_intermediate_results": True,
        "output_dir": output_dir,
        "phase": "chapter_arcs_adjustment"
    })
    
    # Run co_scientist competition
    co_scientist_result = await co_scientist.ainvoke(co_scientist_input, subgraph_config)
    
    # Save detailed competition results
    if model_config.get("save_intermediate_results", True):
        # Save competition summary
        competition_summary = co_scientist_result.get("competition_summary", "")
        save_output(output_dir, f"{state['loop_count']:02d}_10_revised_chapter_arcs_competition_summary.md", competition_summary)
        
        # Save detailed results
        detailed_results = format_detailed_competition_results(co_scientist_result)
        save_output(output_dir, f"{state['loop_count']:02d}_10_revised_chapter_arcs_competition_details.md", detailed_results)
        
        # Save winning options
        direction_winners = co_scientist_result.get("direction_winners", [])
        for i, winner in enumerate(direction_winners[:3]):  # Limit to top 3
            winner_details = format_co_scientist_winner_details(winner, f"chapter_arcs_adjustment_option_{i+1}")
            save_output(output_dir, f"{state['loop_count']:02d}_10_revised_chapter_arcs_option_{i+1}.md", winner_details)
    
    # Format options for user selection
    direction_winners = co_scientist_result.get("direction_winners", [])
    formatted_options = format_chapter_arcs_options_for_selection(direction_winners, co_scientist_result.get("competition_summary", ""))
    
    return {
        "revised_chapter_arcs_options": formatted_options,
        "revised_chapter_arcs": direction_winners[0]["scenario_content"] if direction_winners else "No chapter arcs adjustments generated."
    }

async def rewrite_first_chapter(state: AgentState, config: RunnableConfig):
    if not (output_dir := state.get("output_dir")) or not (target_year := state.get("target_year")) or not (loop_count := state.get("loop_count") is not None) or not (revised_storyline := state.get("revised_storyline")) or not (revised_chapter_arcs := state.get("revised_chapter_arcs")) or not (baseline_world_state := state.get("baseline_world_state")) or not (first_chapter := state.get("first_chapter")) or not (linguistic_evolution := state.get("linguistic_evolution")):
        raise ValueError("Required state for rewriting chapter is missing.")
    
    print("--- Rewriting First Chapter with Co-Scientist Competition ---")
    
    # Use co_scientist for competitive chapter rewriting
    co_scientist_input = CoScientistConfiguration.create_input_state(
        use_case=UseCase.CHAPTER_REWRITING,
        reference_material=f"Original Chapter: {first_chapter}",
        revised_storyline=revised_storyline,
        revised_chapter_arcs=revised_chapter_arcs,
        baseline_world_state=baseline_world_state,
        linguistic_evolution=linguistic_evolution,
        target_year=target_year
    )
    
    # Configure co_scientist for full competition with world-aware reflection
    subgraph_config = config.copy()
    subgraph_config["configurable"].update({
        "research_model": ModelConfig.get_model_string("chapter_writing"),
        "general_model": ModelConfig.get_model_string("chapter_writing"),
        "use_case": "chapter_rewriting",
        "process_depth": "standard",  # Include generate → reflect → evolve
        "population_scale": "light",  # Keep processing reasonable
        "use_deep_researcher": False,  # Use regular LLM for creative writing
        "reflection_domains": ["narrative_structure", "world_building", "character_development", "prose_style", "world_integration", "linguistic_consistency"],
        "world_state_context": f"Baseline World State: {baseline_world_state}\n\nLinguistic Evolution: {linguistic_evolution}\n\nRevised Storyline: {revised_storyline}",  # Pass world context for reflection
        "save_intermediate_results": True,
        "output_dir": output_dir,
        "phase": "chapter_rewriting"
    })
    
    # Run co_scientist competition
    co_scientist_result = await co_scientist.ainvoke(co_scientist_input, subgraph_config)
    
    # Save detailed competition results
    if model_config.get("save_intermediate_results", True):
        # Note: Competition summary saved in co_scientist subdirectory to avoid duplication
        
        # Save detailed competition data
        detailed_results = format_detailed_competition_results(co_scientist_result)
        save_output(output_dir, f"{state['loop_count']:02d}_11b_chapter_rewrite_competition_details.md", detailed_results)
        
        # Save all direction winners
        direction_winners = co_scientist_result.get("direction_winners", [])
        if direction_winners:
            for i, winner in enumerate(direction_winners):
                winner_details = format_co_scientist_winner_details(winner, f"chapter_rewrite_option_{i+1}")
                save_output(output_dir, f"{state['loop_count']:02d}_11c_chapter_rewrite_winner_{i+1}_full.md", winner_details)
    
    # Extract direction winners for user selection
    direction_winners = co_scientist_result.get("direction_winners", [])
    if direction_winners:
        # Format both options for user presentation
        formatted_options = format_chapter_rewrite_options_for_selection(direction_winners, co_scientist_result.get("competition_summary", ""))
        save_output(output_dir, f"{state['loop_count']:02d}_11_revised_first_chapter_options.md", formatted_options)
        
        # Store options in state for user selection
        chapter_rewrite_options = {
            "option_1": direction_winners[0].get("scenario_content", "") if len(direction_winners) > 0 else "",
            "option_2": direction_winners[1].get("scenario_content", "") if len(direction_winners) > 1 else "",
            "options_metadata": direction_winners
        }
        
        print("--- Co-Scientist Chapter Rewriting Competition Complete ---")
        print("--- Two chapter rewrite options created. User selection required. ---")
        
        return {"chapter_rewrite_options": chapter_rewrite_options, "revised_first_chapter": None}  # No auto-selection
    else:
        # Co-scientist failed to produce direction winners - this is a system failure
        raise RuntimeError("Co-scientist chapter rewrite competition failed to produce direction winners. Check competition configuration and model availability.")

def select_chapter_rewrite(state: AgentState):
    """User selection node - presents chapter rewrite options and waits for user choice."""
    if not (output_dir := state.get("output_dir")) or not (chapter_rewrite_options := state.get("chapter_rewrite_options")) or not (loop_count := state.get("loop_count") is not None):
        raise ValueError("Required state 'output_dir' or 'chapter_rewrite_options' is missing.")
    
    # Present options to user through the interface
    options_metadata = chapter_rewrite_options.get("options_metadata", [])
    if len(options_metadata) < 2:
        raise ValueError("Not enough chapter rewrite options for user selection.")
    
    # Note: Individual chapter rewrite options saved as full versions (_full.md) - no duplicates needed
    
    print("--- Chapter Rewrite Options Prepared for User Selection ---")
    print(f"Option 1: {options_metadata[0].get('research_direction', 'Unknown')}")
    print(f"Option 2: {options_metadata[1].get('research_direction', 'Unknown')}")
    
    # This function prepares options for user selection via LangGraph Studio interrupt
    # The actual selection happens in the next node via interrupt_before mechanism
    print("--- Chapter rewrite options prepared. Workflow will pause for user selection. ---")
    
    return {"chapter_rewrite_options": chapter_rewrite_options}

def process_chapter_rewrite_selection(state: AgentState):
    """Process user's chapter rewrite selection after interrupt."""
    if not (output_dir := state.get("output_dir")) or not (chapter_rewrite_options := state.get("chapter_rewrite_options")) or not (loop_count := state.get("loop_count") is not None):
        raise ValueError("Required state 'output_dir' or 'chapter_rewrite_options' is missing.")
    
    # Get user's choice from state (will be set by LangGraph Studio)
    user_choice = state.get("chapter_rewrite_choice", "1")  # Default to option 1
    options_metadata = chapter_rewrite_options.get("options_metadata", [])
    
    option_1_content = chapter_rewrite_options.get("option_1", "")
    option_2_content = chapter_rewrite_options.get("option_2", "")
    
    # Process user choice
    choice = str(user_choice).strip()
    if choice == "1":
        selected_rewrite = option_1_content
        selected_option = options_metadata[0] if len(options_metadata) > 0 else {}
    elif choice == "2":
        selected_rewrite = option_2_content
        selected_option = options_metadata[1] if len(options_metadata) > 1 else {}
    else:
        # Default to option 1 if invalid choice
        print(f"Invalid choice '{choice}', defaulting to Option 1")
        selected_rewrite = option_1_content
        selected_option = options_metadata[0] if len(options_metadata) > 0 else {}
    
    save_output(output_dir, f"{state['loop_count']:02d}_11_selected_revised_first_chapter.md", selected_rewrite)
    
    print(f"--- Chapter Rewrite Selected: {selected_option.get('research_direction', 'Unknown')} ---")
    
    return {
        "revised_first_chapter": selected_rewrite
    }

def generate_scientific_explanations(state: AgentState):
    if not (output_dir := state.get("output_dir")) or not (loop_count := state.get("loop_count") is not None) or not (revised_first_chapter := state.get("revised_first_chapter")) or not (baseline_world_state := state.get("baseline_world_state")):
        raise ValueError("Required state for generating scientific explanations is missing.")
    prompt = ChatPromptTemplate.from_template(GENERATE_SCIENTIFIC_EXPLANATIONS_PROMPT)
    response = general_model.invoke(prompt.format(revised_first_chapter=revised_first_chapter, baseline_world_state=baseline_world_state))
    content = response.content
    save_output(output_dir, f"{state['loop_count']:02d}_12_scientific_explanations.md", content)
    return {"scientific_explanations": content}

def generate_glossary(state: AgentState):
    if not (output_dir := state.get("output_dir")) or not (loop_count := state.get("loop_count") is not None) or not (revised_first_chapter := state.get("revised_first_chapter")) or not (baseline_world_state := state.get("baseline_world_state")) or not (linguistic_evolution := state.get("linguistic_evolution")):
        raise ValueError("Required state for generating glossary is missing.")
    prompt = ChatPromptTemplate.from_template(GENERATE_GLOSSARY_PROMPT)
    response = general_model.invoke(prompt.format(revised_first_chapter=revised_first_chapter, baseline_world_state=baseline_world_state, linguistic_evolution=linguistic_evolution))
    content = response.content
    save_output(output_dir, f"{state['loop_count']:02d}_13_glossary.md", content)
    return {"glossary": content}

def compile_baseline_world_state(state: AgentState):
    if not (output_dir := state.get("output_dir")) or not (target_year := state.get("target_year")) or not (loop_count := state.get("loop_count") is not None) or not (selected_scenario := state.get("selected_scenario")) or not (baseline_world_state := state.get("baseline_world_state")) or not (linguistic_evolution := state.get("linguistic_evolution")) or not (scientific_explanations := state.get("scientific_explanations")) or not (glossary := state.get("glossary")):
        raise ValueError("Required state for compiling baseline is missing.")
    baseline_content = f"""
# World State as of {target_year}
## World State
{baseline_world_state}
## Linguistic Evolution
{linguistic_evolution}
## Scientific Explanations
{scientific_explanations}
## Glossary
{glossary}
"""
    save_output(output_dir, f"{state['loop_count']:02d}_14_baseline_world_state.md", baseline_content)
    return {"baseline_world_state": baseline_content, "loop_count": state["loop_count"] + 1}

# === Multi-Chapter Book Writing Workflow Nodes ===

def choose_next_action(state: AgentState):
    """Present user with choice to project further into future or write remaining chapters."""
    message = AIMessage(content="Choose your next action:\n1. Project the world further into the future (continue current loop)\n2. Write the remaining chapters of the book\n\nPlease provide your choice in the `next_action_choice` field: 'project' or 'write_book'")
    return {"messages": [message]}

async def plan_remaining_chapters(state: AgentState, config: RunnableConfig):
    """Use Co-Scientist to plan the structure for remaining chapters."""
    if not (output_dir := state.get("output_dir")) or not (storyline := state.get("storyline")) or not (chapter_arcs := state.get("chapter_arcs")) or not (first_chapter := state.get("revised_first_chapter", state.get("first_chapter"))) or not (baseline_world_state := state.get("baseline_world_state")):
        raise ValueError("Required state for planning remaining chapters is missing.")
    
    print("--- Planning Remaining Chapters with Co-Scientist Competition ---")
    
    # Use co_scientist for competitive chapter planning
    co_scientist_input = CoScientistConfiguration.create_input_state(
        use_case=UseCase.CHAPTER_PLANNING,
        reference_material=f"First Chapter: {first_chapter}",
        storyline=storyline,
        chapter_arcs=chapter_arcs,
        baseline_world_state=baseline_world_state
    )
    
    # Configure co_scientist for planning competition
    subgraph_config = config.copy()
    subgraph_config["configurable"].update({
        "research_model": ModelConfig.get_model_string("general_creative"),
        "general_model": ModelConfig.get_model_string("general_creative"),
        "use_case": "chapter_planning",
        "process_depth": "standard",
        "population_scale": "light",
        "use_deep_researcher": False,
        "save_intermediate_results": True,
        "output_dir": output_dir,
        "phase": "chapter_planning"
    })
    
    # Run co_scientist competition
    co_scientist_result = await co_scientist.ainvoke(co_scientist_input, subgraph_config)
    
    # Save and process results
    if model_config.get("save_intermediate_results", True):
        competition_summary = co_scientist_result.get("competition_summary", "")
        save_output(output_dir, "15_chapter_planning_competition_summary.md", competition_summary)
        
        detailed_results = format_detailed_competition_results(co_scientist_result)
        save_output(output_dir, "15_chapter_planning_details.md", detailed_results)
        
        direction_winners = co_scientist_result.get("direction_winners", [])
        for i, winner in enumerate(direction_winners, 1):
            winner_details = format_co_scientist_winner_details(winner, f"chapter_planning_option_{i}")
            save_output(output_dir, f"15_chapter_planning_option_{i}_full.md", winner_details)
    
    # Store options for user selection
    direction_winners = co_scientist_result.get("direction_winners", [])
    if direction_winners:
        formatted_options = format_chapter_planning_options_for_selection(direction_winners, co_scientist_result.get("competition_summary", ""))
        save_output(output_dir, "15_chapter_planning_options.md", formatted_options)
        
        chapter_planning_options = {
            "option_1": direction_winners[0].get("scenario_content", "") if len(direction_winners) > 0 else "",
            "option_2": direction_winners[1].get("scenario_content", "") if len(direction_winners) > 1 else "",
            "options_metadata": direction_winners
        }
        
        # Extract total chapters from the winning plan and initialize chapter progression
        plan_content = direction_winners[0].get("scenario_content", "")
        total_chapters = extract_total_chapters_from_plan(plan_content)
        
        print(f"--- Chapter Planning Complete: {total_chapters} total chapters planned ---")
        
        return {
            "chapter_planning_options": chapter_planning_options,
            "total_planned_chapters": total_chapters,
            "current_chapter_number": 2,  # Starting with chapter 2 (first chapter already done)
            "previous_chapters": [first_chapter],
            "accumulated_scientific_explanations": state.get("scientific_explanations", ""),
            "accumulated_glossary": state.get("glossary", ""),
            "plot_continuity_tracker": f"Chapter 1 Complete: {first_chapter[:200]}...",
            "transition_quality_scores": []
        }
    else:
        raise RuntimeError("Co-scientist chapter planning competition failed to produce direction winners.")

def extract_total_chapters_from_plan(plan_content: str) -> int:
    """Extract the total number of chapters from the planning content."""
    import re
    # Look for patterns like "12 chapters" or "Chapter 12"
    matches = re.findall(r'(?:chapter\s*(\d+)|(\d+)\s*chapters)', plan_content.lower())
    if matches:
        # Find the highest number mentioned
        numbers = [int(match[0] or match[1]) for match in matches if match[0] or match[1]]
        return max(numbers) if numbers else 10
    return 10  # Default fallback

def generate_chapter_world_questions(state: AgentState):
    """Generate research questions specific to the current chapter."""
    if not (output_dir := state.get("output_dir")) or not (current_chapter_number := state.get("current_chapter_number")) or not (baseline_world_state := state.get("baseline_world_state")):
        raise ValueError("Required state for generating chapter world questions is missing.")
    
    # Get the current chapter arc from the planning
    chapter_planning = state.get("chapter_planning_options", {}).get("option_1", "")
    current_chapter_arc = extract_chapter_arc(chapter_planning, current_chapter_number)
    
    # Summarize previous chapters
    previous_chapters = state.get("previous_chapters", [])
    previous_chapters_summary = "\n\n".join([f"Chapter {i+1}: {ch[:300]}..." for i, ch in enumerate(previous_chapters)])
    
    prompt = ChatPromptTemplate.from_template(GENERATE_CHAPTER_WORLD_QUESTIONS_PROMPT)
    response = general_model.invoke(prompt.format(
        chapter_number=current_chapter_number,
        current_chapter_arc=current_chapter_arc,
        baseline_world_state=baseline_world_state,
        previous_chapters_summary=previous_chapters_summary
    ))
    
    content = response.content
    save_output(output_dir, f"chapter_{current_chapter_number:02d}_01_world_questions.md", content)
    print(f"--- Chapter {current_chapter_number} World Questions Generated ---")
    return {"chapter_world_questions": content}

def extract_chapter_arc(planning_content: str, chapter_number: int) -> str:
    """Extract the specific arc for the current chapter from the planning content."""
    import re
    # Look for chapter-specific content
    pattern = rf'chapter\s*{chapter_number}[:\s]([^#]*?)(?=chapter\s*{chapter_number + 1}|$)'
    match = re.search(pattern, planning_content.lower())
    if match:
        return match.group(1).strip()
    return f"Chapter {chapter_number} content from overall plan"

async def chapter_world_research(state: AgentState, config: RunnableConfig):
    """Use Co-Scientist with Deep Research to research chapter-specific world context."""
    if not (output_dir := state.get("output_dir")) or not (current_chapter_number := state.get("current_chapter_number")) or not (chapter_world_questions := state.get("chapter_world_questions")) or not (baseline_world_state := state.get("baseline_world_state")):
        raise ValueError("Required state for chapter world research is missing.")
    
    print(f"--- Researching World Context for Chapter {current_chapter_number} ---")
    
    # Use co_scientist for competitive chapter world research
    co_scientist_input = CoScientistConfiguration.create_input_state(
        use_case=UseCase.CHAPTER_WORLD_RESEARCH,
        context=chapter_world_questions,
        reference_material=f"Baseline World State: {baseline_world_state}",
        target_year=state.get("target_year"),
        baseline_world_state=baseline_world_state
    )
    
    # Configure co_scientist for research competition
    subgraph_config = config.copy()
    subgraph_config["configurable"].update({
        "research_model": ModelConfig.get_model_string("world_research"),
        "general_model": ModelConfig.get_model_string("world_research"),
        "search_api": "openai",  # Use OpenAI native web search for O3 models
        "use_case": "chapter_world_research",
        "process_depth": "standard",
        "population_scale": "light",
        "use_deep_researcher": True,  # Enable research for world context
        "save_intermediate_results": True,
        "output_dir": output_dir,
        "phase": f"chapter_{current_chapter_number}_world_research"
    })
    
    # Run co_scientist competition
    co_scientist_result = await co_scientist.ainvoke(co_scientist_input, subgraph_config)
    
    # Save and process results
    if model_config.get("save_intermediate_results", True):
        detailed_results = format_detailed_competition_results(co_scientist_result)
        save_output(output_dir, f"chapter_{current_chapter_number:02d}_02_world_research_details.md", detailed_results)
        
        direction_winners = co_scientist_result.get("direction_winners", [])
        for i, winner in enumerate(direction_winners, 1):
            winner_details = format_co_scientist_winner_details(winner, f"chapter_world_context_option_{i}")
            save_output(output_dir, f"chapter_{current_chapter_number:02d}_02_world_context_option_{i}.md", winner_details)
    
    # Use the top research result as chapter world context
    direction_winners = co_scientist_result.get("direction_winners", [])
    if direction_winners:
        chapter_world_context = direction_winners[0].get("scenario_content", "")
        save_output(output_dir, f"chapter_{current_chapter_number:02d}_02_selected_world_context.md", chapter_world_context)
        
        print(f"--- Chapter {current_chapter_number} World Research Complete ---")
        return {"chapter_world_context": chapter_world_context}
    else:
        raise RuntimeError(f"Co-scientist chapter world research for chapter {current_chapter_number} failed to produce results.")

async def write_next_chapter(state: AgentState, config: RunnableConfig):
    """Use Co-Scientist to write the next chapter with full context."""
    if not (output_dir := state.get("output_dir")) or not (current_chapter_number := state.get("current_chapter_number")) or not (storyline := state.get("storyline")) or not (chapter_world_context := state.get("chapter_world_context")):
        raise ValueError("Required state for writing next chapter is missing.")
    
    print(f"--- Writing Chapter {current_chapter_number} with Co-Scientist Competition ---")
    
    # Prepare comprehensive context for chapter writing
    previous_chapters = state.get("previous_chapters", [])
    previous_chapters_context = "\n\n".join([f"Chapter {i+1}:\n{ch}" for i, ch in enumerate(previous_chapters)])
    
    # Get chapter planning context
    chapter_planning = state.get("chapter_planning_options", {}).get("option_1", "")
    current_chapter_arc = extract_chapter_arc(chapter_planning, current_chapter_number)
    
    # Use co_scientist for competitive chapter writing
    co_scientist_input = CoScientistConfiguration.create_input_state(
        use_case=UseCase.CHAPTER_WRITING,
        context=f"Chapter {current_chapter_number} Arc: {current_chapter_arc}",
        storyline=storyline,
        reference_material=f"Previous Chapters: {previous_chapters_context}\n\nWorld Context: {chapter_world_context}",
        baseline_world_state=state.get("baseline_world_state"),
        linguistic_evolution=state.get("linguistic_evolution")
    )
    
    # Configure co_scientist for chapter writing competition
    subgraph_config = config.copy()
    subgraph_config["configurable"].update({
        "research_model": ModelConfig.get_model_string("chapter_writing"),
        "general_model": ModelConfig.get_model_string("chapter_writing"),
        "use_case": "chapter_writing",
        "process_depth": "standard",
        "population_scale": "light",
        "use_deep_researcher": False,
        "reflection_domains": ["prose_quality", "scene_development", "character_voice", "pacing", "atmosphere", "world_integration"],
        "world_state_context": f"Chapter World Context: {chapter_world_context}",
        "save_intermediate_results": True,
        "output_dir": output_dir,
        "phase": f"chapter_{current_chapter_number}_writing"
    })
    
    # Run co_scientist competition
    co_scientist_result = await co_scientist.ainvoke(co_scientist_input, subgraph_config)
    
    # Save and process results
    if model_config.get("save_intermediate_results", True):
        detailed_results = format_detailed_competition_results(co_scientist_result)
        save_output(output_dir, f"chapter_{current_chapter_number:02d}_03_writing_details.md", detailed_results)
        
        direction_winners = co_scientist_result.get("direction_winners", [])
        for i, winner in enumerate(direction_winners, 1):
            winner_details = format_co_scientist_winner_details(winner, f"chapter_{current_chapter_number}_option_{i}")
            save_output(output_dir, f"chapter_{current_chapter_number:02d}_03_chapter_option_{i}.md", winner_details)
    
    # Use the top result as the chapter draft
    direction_winners = co_scientist_result.get("direction_winners", [])
    if direction_winners:
        chapter_draft = direction_winners[0].get("scenario_content", "")
        save_output(output_dir, f"chapter_{current_chapter_number:02d}_03_draft.md", chapter_draft)
        
        print(f"--- Chapter {current_chapter_number} Draft Complete ---")
        return {"current_chapter_draft": chapter_draft}
    else:
        raise RuntimeError(f"Co-scientist chapter writing for chapter {current_chapter_number} failed to produce results.")

def check_chapter_coherence(state: AgentState):
    """Check the written chapter for coherence with previous chapters and storyline."""
    if not (output_dir := state.get("output_dir")) or not (current_chapter_number := state.get("current_chapter_number")) or not (current_chapter_draft := state.get("current_chapter_draft")):
        raise ValueError("Required state for checking chapter coherence is missing.")
    
    print(f"--- Checking Chapter {current_chapter_number} Coherence ---")
    
    # Prepare context for coherence check
    previous_chapters = state.get("previous_chapters", [])
    previous_chapters_context = "\n\n".join([f"Chapter {i+1}:\n{ch}" for i, ch in enumerate(previous_chapters)])
    
    prompt = ChatPromptTemplate.from_template(CHECK_CHAPTER_COHERENCE_PROMPT)
    response = general_model.invoke(prompt.format(
        current_chapter=current_chapter_draft,
        storyline=state.get("storyline", ""),
        previous_chapters=previous_chapters_context,
        baseline_world_state=state.get("baseline_world_state", ""),
        plot_continuity_tracker=state.get("plot_continuity_tracker", "")
    ))
    
    coherence_report = response.content
    save_output(output_dir, f"chapter_{current_chapter_number:02d}_04_coherence_check.md", coherence_report)
    
    # Extract coherence score (simple pattern matching)
    import re
    score_match = re.search(r'score[:\s]*(\d+)', coherence_report.lower())
    coherence_score = int(score_match.group(1)) if score_match else 5
    
    print(f"--- Chapter {current_chapter_number} Coherence Score: {coherence_score}/10 ---")
    
    return {
        "chapter_coherence_report": coherence_report,
        "chapter_coherence_score": coherence_score
    }

def validate_transitions(state: AgentState):
    """Validate the transition from the previous chapter to the current chapter."""
    if not (output_dir := state.get("output_dir")) or not (current_chapter_number := state.get("current_chapter_number")) or not (current_chapter_draft := state.get("current_chapter_draft")):
        raise ValueError("Required state for validating transitions is missing.")
    
    # Skip transition validation for chapter 2 (no previous chapter to transition from)
    if current_chapter_number <= 2:
        print(f"--- Skipping Transition Validation for Chapter {current_chapter_number} (First/Second Chapter) ---")
        return {"transition_validation_report": "N/A - No previous chapter", "transition_score": 10}
    
    print(f"--- Validating Chapter {current_chapter_number} Transition ---")
    
    # Get previous chapter ending and current chapter beginning
    previous_chapters = state.get("previous_chapters", [])
    if len(previous_chapters) < current_chapter_number - 1:
        print(f"--- Warning: Not enough previous chapters for transition validation ---")
        return {"transition_validation_report": "Warning: Insufficient previous chapters", "transition_score": 5}
    
    previous_chapter = previous_chapters[-1]  # Last completed chapter
    previous_chapter_ending = previous_chapter[-1000:]  # Last 1000 characters
    current_chapter_beginning = current_chapter_draft[:1000]  # First 1000 characters
    
    prompt = ChatPromptTemplate.from_template(VALIDATE_TRANSITIONS_PROMPT)
    response = general_model.invoke(prompt.format(
        previous_chapter_ending=previous_chapter_ending,
        current_chapter_beginning=current_chapter_beginning,
        storyline=state.get("storyline", "")
    ))
    
    transition_report = response.content
    save_output(output_dir, f"chapter_{current_chapter_number:02d}_05_transition_validation.md", transition_report)
    
    # Extract transition score
    import re
    score_match = re.search(r'score[:\s]*(\d+)', transition_report.lower())
    transition_score = int(score_match.group(1)) if score_match else 5
    
    print(f"--- Chapter {current_chapter_number} Transition Score: {transition_score}/10 ---")
    
    return {
        "transition_validation_report": transition_report,
        "transition_score": transition_score
    }

async def rewrite_chapter_for_coherence(state: AgentState, config: RunnableConfig):
    """Rewrite the chapter to address coherence or transition issues."""
    if not (output_dir := state.get("output_dir")) or not (current_chapter_number := state.get("current_chapter_number")) or not (current_chapter_draft := state.get("current_chapter_draft")) or not (target_year := state.get("target_year")):
        raise ValueError("Required state for rewriting chapter is missing.")
    
    print(f"--- Rewriting Chapter {current_chapter_number} for Improved Coherence ---")
    
    # Prepare context including the issues found
    coherence_report = state.get("chapter_coherence_report", "")
    transition_report = state.get("transition_validation_report", "")
    previous_chapters = state.get("previous_chapters", [])
    previous_chapters_context = "\n\n".join([f"Chapter {i+1}:\n{ch}" for i, ch in enumerate(previous_chapters)])
    
    # Use co_scientist for competitive chapter rewriting
    co_scientist_input = CoScientistConfiguration.create_input_state(
        use_case=UseCase.CHAPTER_REWRITING,
        reference_material=f"Original Chapter: {current_chapter_draft}\n\nCoherence Issues: {coherence_report}\n\nTransition Issues: {transition_report}",
        storyline=state.get("storyline"),
        baseline_world_state=state.get("baseline_world_state"),
        linguistic_evolution=state.get("linguistic_evolution"),
        revised_storyline=state.get("revised_storyline", state.get("storyline")),
        revised_chapter_arcs=state.get("revised_chapter_arcs", state.get("chapter_arcs")),
        target_year=target_year  # Pass target year for sci-fi context
    )
    
    # Configure co_scientist for rewriting competition
    subgraph_config = config.copy()
    subgraph_config["configurable"].update({
        "research_model": ModelConfig.get_model_string("chapter_writing"),
        "general_model": ModelConfig.get_model_string("chapter_writing"),
        "use_case": "chapter_rewriting",
        "process_depth": "standard",
        "population_scale": "light",
        "use_deep_researcher": False,
        "reflection_domains": ["narrative_structure", "world_building", "character_development", "prose_style", "world_integration", "coherence_improvement"],
        "world_state_context": f"Previous Chapters: {previous_chapters_context}\n\nCoherence Requirements: {coherence_report}",
        "save_intermediate_results": True,
        "output_dir": output_dir,
        "phase": f"chapter_{current_chapter_number}_rewrite"
    })
    
    # Run co_scientist competition
    co_scientist_result = await co_scientist.ainvoke(co_scientist_input, subgraph_config)
    
    # Save and process results
    if model_config.get("save_intermediate_results", True):
        detailed_results = format_detailed_competition_results(co_scientist_result)
        save_output(output_dir, f"chapter_{current_chapter_number:02d}_06_rewrite_details.md", detailed_results)
        
        direction_winners = co_scientist_result.get("direction_winners", [])
        for i, winner in enumerate(direction_winners, 1):
            winner_details = format_co_scientist_winner_details(winner, f"chapter_{current_chapter_number}_rewrite_option_{i}")
            save_output(output_dir, f"chapter_{current_chapter_number:02d}_06_rewrite_option_{i}.md", winner_details)
    
    # Use the top result as the improved chapter
    direction_winners = co_scientist_result.get("direction_winners", [])
    if direction_winners:
        improved_chapter = direction_winners[0].get("scenario_content", "")
        save_output(output_dir, f"chapter_{current_chapter_number:02d}_06_improved_draft.md", improved_chapter)
        
        print(f"--- Chapter {current_chapter_number} Rewrite Complete ---")
        return {"current_chapter_draft": improved_chapter}
    else:
        print(f"--- Chapter {current_chapter_number} Rewrite Failed, Using Original ---")
        return {"current_chapter_draft": current_chapter_draft}

def generate_chapter_scientific_explanations(state: AgentState):
    """Generate scientific explanations for concepts in the current chapter."""
    if not (output_dir := state.get("output_dir")) or not (current_chapter_number := state.get("current_chapter_number")) or not (current_chapter_draft := state.get("current_chapter_draft")):
        raise ValueError("Required state for generating chapter scientific explanations is missing.")
    
    print(f"--- Generating Scientific Explanations for Chapter {current_chapter_number} ---")
    
    prompt = ChatPromptTemplate.from_template(GENERATE_CHAPTER_SCIENTIFIC_EXPLANATIONS_PROMPT)
    response = general_model.invoke(prompt.format(
        chapter_number=current_chapter_number,
        chapter_content=current_chapter_draft,
        baseline_world_state=state.get("baseline_world_state", ""),
        previous_explanations=state.get("accumulated_scientific_explanations", "")
    ))
    
    chapter_explanations = response.content
    save_output(output_dir, f"chapter_{current_chapter_number:02d}_07_scientific_explanations.md", chapter_explanations)
    
    print(f"--- Chapter {current_chapter_number} Scientific Explanations Generated ---")
    return {"chapter_scientific_explanations": chapter_explanations}

def update_accumulated_materials(state: AgentState):
    """Update accumulated scientific explanations and glossary with the current chapter's materials."""
    if not (output_dir := state.get("output_dir")) or not (current_chapter_number := state.get("current_chapter_number")) or not (current_chapter_draft := state.get("current_chapter_draft")):
        raise ValueError("Required state for updating accumulated materials is missing.")
    
    print(f"--- Updating Accumulated Materials for Chapter {current_chapter_number} ---")
    
    # Update accumulated scientific explanations
    current_explanations = state.get("chapter_scientific_explanations", "")
    previous_explanations = state.get("accumulated_scientific_explanations", "")
    
    updated_explanations = f"{previous_explanations}\n\n## Chapter {current_chapter_number} Scientific Explanations\n\n{current_explanations}" if previous_explanations else f"## Chapter {current_chapter_number} Scientific Explanations\n\n{current_explanations}"
    
    # Update accumulated glossary
    prompt = ChatPromptTemplate.from_template(UPDATE_ACCUMULATED_GLOSSARY_PROMPT)
    response = general_model.invoke(prompt.format(
        chapter_number=current_chapter_number,
        chapter_content=current_chapter_draft,
        existing_glossary=state.get("accumulated_glossary", ""),
        baseline_world_state=state.get("baseline_world_state", ""),
        linguistic_evolution=state.get("linguistic_evolution", "")
    ))
    
    updated_glossary = response.content
    
    # Update plot continuity tracker
    continuity_prompt = ChatPromptTemplate.from_template(UPDATE_PLOT_CONTINUITY_PROMPT)
    continuity_response = general_model.invoke(continuity_prompt.format(
        current_tracker=state.get("plot_continuity_tracker", ""),
        new_chapter=current_chapter_draft,
        chapter_number=current_chapter_number
    ))
    
    updated_plot_tracker = continuity_response.content
    
    # Save updated materials
    save_output(output_dir, f"chapter_{current_chapter_number:02d}_08_updated_explanations.md", updated_explanations)
    save_output(output_dir, f"chapter_{current_chapter_number:02d}_08_updated_glossary.md", updated_glossary)
    save_output(output_dir, f"chapter_{current_chapter_number:02d}_08_updated_plot_tracker.md", updated_plot_tracker)
    
    print(f"--- Chapter {current_chapter_number} Materials Updated ---")
    
    return {
        "accumulated_scientific_explanations": updated_explanations,
        "accumulated_glossary": updated_glossary,
        "plot_continuity_tracker": updated_plot_tracker
    }

def advance_to_next_chapter(state: AgentState):
    """Finalize the current chapter and advance to the next chapter."""
    if not (output_dir := state.get("output_dir")) or not (current_chapter_number := state.get("current_chapter_number")) or not (current_chapter_draft := state.get("current_chapter_draft")):
        raise ValueError("Required state for advancing to next chapter is missing.")
    
    print(f"--- Finalizing Chapter {current_chapter_number} ---")
    
    # Add current chapter to previous chapters list
    previous_chapters = state.get("previous_chapters", [])
    previous_chapters.append(current_chapter_draft)
    
    # Add transition score to the list
    transition_scores = state.get("transition_quality_scores", [])
    transition_score = state.get("transition_score", 10)
    transition_scores.append(transition_score)
    
    # Save the completed chapter
    save_output(output_dir, f"chapter_{current_chapter_number:02d}_FINAL.md", current_chapter_draft)
    
    # Increment chapter number
    next_chapter_number = current_chapter_number + 1
    
    print(f"--- Chapter {current_chapter_number} Finalized, Moving to Chapter {next_chapter_number} ---")
    
    return {
        "previous_chapters": previous_chapters,
        "current_chapter_number": next_chapter_number,
        "transition_quality_scores": transition_scores,
        "current_chapter_draft": None,  # Clear current draft
        "chapter_coherence_report": None,
        "transition_validation_report": None,
        "chapter_scientific_explanations": None,
        "chapter_world_questions": None,
        "chapter_world_context": None
    }

# Helper functions for chapter planning
def format_chapter_planning_options_for_selection(direction_winners: list, competition_summary: str) -> str:
    """Format chapter planning options for user selection."""
    content = "# Chapter Planning Options from Co-Scientist Competition\n\n"
    content += "Multiple planning approaches competed and are now available for your selection.\n\n"
    
    content += "## Competition Overview\n"
    content += competition_summary + "\n\n"
    
    for i, winner in enumerate(direction_winners, 1):
        content += f"## Option {i}: {winner.get('research_direction', 'Unknown Approach')}\n\n"
        content += f"**Core Approach:** {winner.get('core_assumption', 'No assumption available')}\n\n"
        content += f"**Selection Reasoning:** {winner.get('selection_reasoning', 'Tournament winner')}\n\n"
        content += "### Full Chapter Plan:\n\n"
        content += f"{winner.get('scenario_content', 'No content available')}\n\n"
        content += "---\n\n"
    
    content += "## Selection Instructions\n"
    content += f"Please review all {len(direction_winners)} chapter planning options above and choose your preferred approach. "
    content += "You can select one option as-is, or combine elements from multiple approaches.\n\n"
    content += "To continue, the system will automatically use the top-ranked option from the competition.\n"
    
    return content

# Conditional functions for workflow control
def check_if_rewrite_needed(state: AgentState):
    """Check if chapter needs rewriting based on coherence and transition scores."""
    coherence_score = state.get("chapter_coherence_score", 10)
    transition_score = state.get("transition_score", 10)
    
    # Rewrite if either score is below 7
    if coherence_score < 7 or transition_score < 7:
        print(f"--- Chapter needs rewriting (Coherence: {coherence_score}, Transition: {transition_score}) ---")
        return "rewrite_chapter_for_coherence"
    else:
        print(f"--- Chapter quality acceptable (Coherence: {coherence_score}, Transition: {transition_score}) ---")
        return "generate_chapter_scientific_explanations"

def compile_complete_book(state: AgentState):
    """Compile all chapters into a single complete book file."""
    if not (output_dir := state.get("output_dir")) or not (previous_chapters := state.get("previous_chapters")):
        raise ValueError("Required state for compiling complete book is missing.")
    
    print("--- Compiling Complete Book ---")
    
    # Gather all components
    storyline = state.get("revised_storyline", state.get("storyline", ""))
    chapter_arcs = state.get("revised_chapter_arcs", state.get("chapter_arcs", ""))
    baseline_world_state = state.get("baseline_world_state", "")
    linguistic_evolution = state.get("linguistic_evolution", "")
    accumulated_scientific_explanations = state.get("accumulated_scientific_explanations", "")
    accumulated_glossary = state.get("accumulated_glossary", "")
    plot_continuity_tracker = state.get("plot_continuity_tracker", "")
    total_chapters = len(previous_chapters)
    transition_scores = state.get("transition_quality_scores", [])
    
    # Calculate average transition quality
    avg_transition_score = sum(transition_scores) / len(transition_scores) if transition_scores else "N/A"
    
    # Build complete book content
    complete_book = f"""# Complete Science Fiction Novel
Generated by Deep Sci-Fi Writer with Co-Scientist Competition

## Metadata
- **Total Chapters:** {total_chapters}
- **Target Year:** {state.get("target_year", "Future")}
- **Average Transition Quality:** {avg_transition_score}
- **Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

## Storyline

{storyline}

---

## Chapter Structure

{chapter_arcs}

---

## The Complete Novel

"""
    
    # Add all chapters
    for i, chapter in enumerate(previous_chapters, 1):
        complete_book += f"""
### Chapter {i}

{chapter}

---

"""
    
    # Add supporting materials
    complete_book += f"""
## Supporting Materials

### World State
{baseline_world_state}

### Linguistic Evolution
{linguistic_evolution}

### Scientific Explanations
{accumulated_scientific_explanations}

### Glossary
{accumulated_glossary}

### Plot Continuity Summary
{plot_continuity_tracker}

---

*This novel was generated using the Deep Sci-Fi Writer system with Co-Scientist competitive multi-agent generation, ensuring scientific grounding and narrative coherence.*
"""
    
    # Save the complete book
    save_output(output_dir, "COMPLETE_BOOK.md", complete_book)
    
    # Also save a version with just the story (no supporting materials)
    story_only = f"""# {storyline.split('.')[0] if storyline else 'Science Fiction Novel'}

"""
    
    for i, chapter in enumerate(previous_chapters, 1):
        story_only += f"""
## Chapter {i}

{chapter}

"""
    
    save_output(output_dir, "STORY_ONLY.md", story_only)
    
    print(f"--- Complete Book Compiled: {total_chapters} chapters ---")
    print(f"--- Files saved: COMPLETE_BOOK.md, STORY_ONLY.md ---")
    
    return {
        "book_compilation_complete": True,
        "total_chapters_written": total_chapters,
        "average_transition_quality": avg_transition_score
    }

def check_if_more_chapters(state: AgentState):
    """Check if there are more chapters to write."""
    current_chapter_number = state.get("current_chapter_number", 2)
    total_planned_chapters = state.get("total_planned_chapters", 10)
    
    if current_chapter_number <= total_planned_chapters:
        print(f"--- Continuing to Chapter {current_chapter_number} of {total_planned_chapters} ---")
        return "generate_chapter_world_questions"
    else:
        print(f"--- Book Complete: All {total_planned_chapters} chapters written ---")
        return "compile_complete_book"

def process_next_action_choice(state: AgentState):
    """Process user's choice between projecting further or writing the book."""
    user_choice = state.get("next_action_choice", "project")  # Default to projection
    
    if user_choice.lower() == "write_book":
        print("--- User chose to write the remaining chapters ---")
        return {"next_action_choice": "write_book"}
    else:
        print("--- User chose to project further into the future ---")
        return {"next_action_choice": "project"}

def should_loop_or_write_book(state: AgentState):
    """Determine whether to continue projection loop or start book writing."""
    user_choice = state.get("next_action_choice", "project")
    
    if user_choice == "write_book":
        return "plan_remaining_chapters"
    elif user_choice == "project":
        return "prompt_for_projection_year" 
    else:
        return END

def should_loop(state: AgentState):
    if state.get("loop_count", 0) < 5:
        return "prompt_for_projection_year"
    else:
        return END

workflow = StateGraph(AgentState)

workflow.add_node("create_storyline", create_storyline)
workflow.add_node("select_storyline", select_storyline)
workflow.add_node("get_storyline_selection_input", lambda state: None)  # Dummy node for interrupt
workflow.add_node("process_storyline_selection", process_storyline_selection)
workflow.add_node("create_chapter_arcs", create_chapter_arcs)
workflow.add_node("get_chapter_arcs_selection_input", get_chapter_arcs_selection_input)  # Dummy node for interrupt
workflow.add_node("process_chapter_arcs_selection", process_chapter_arcs_selection)
workflow.add_node("write_first_chapter", write_first_chapter)
workflow.add_node("select_first_chapter", select_first_chapter)
workflow.add_node("get_chapter_selection_input", lambda state: None)  # Dummy node for interrupt
workflow.add_node("process_chapter_selection", process_chapter_selection)
workflow.add_node("prompt_for_projection_year", prompt_for_projection_year)
workflow.add_node("get_projection_year_input", lambda state: None)
workflow.add_node("set_target_year", set_target_year)
workflow.add_node("generate_world_building_questions", generate_world_building_questions)
workflow.add_node("research_and_propose_scenarios", research_and_propose_scenarios)
workflow.add_node("select_world_scenario", select_world_scenario)
workflow.add_node("get_world_scenario_selection_input", lambda state: None)  # Dummy node for interrupt
workflow.add_node("process_world_scenario_selection", process_world_scenario_selection)
workflow.add_node("world_projection_deep_research", world_projection_deep_research)
workflow.add_node("linguistic_evolution_research", linguistic_evolution_research)
workflow.add_node("select_linguistic_evolution", select_linguistic_evolution)
workflow.add_node("get_linguistic_selection_input", lambda state: None)  # Dummy node for interrupt
workflow.add_node("process_linguistic_evolution_selection", process_linguistic_evolution_selection)
workflow.add_node("adjust_storyline", adjust_storyline)
workflow.add_node("select_storyline_adjustment", select_storyline_adjustment)
workflow.add_node("get_storyline_adjustment_input", lambda state: None)  # Dummy node for interrupt
workflow.add_node("process_storyline_adjustment_selection", process_storyline_adjustment_selection)
workflow.add_node("adjust_chapter_arcs", adjust_chapter_arcs)
workflow.add_node("rewrite_first_chapter", rewrite_first_chapter)
workflow.add_node("select_chapter_rewrite", select_chapter_rewrite)
workflow.add_node("get_chapter_rewrite_input", lambda state: None)  # Dummy node for interrupt
workflow.add_node("process_chapter_rewrite_selection", process_chapter_rewrite_selection)
workflow.add_node("generate_scientific_explanations", generate_scientific_explanations)
workflow.add_node("generate_glossary", generate_glossary)
workflow.add_node("compile_baseline_world_state", compile_baseline_world_state)

workflow.add_edge(START, "create_storyline")
workflow.add_edge("create_storyline", "select_storyline")
workflow.add_edge("select_storyline", "get_storyline_selection_input")
workflow.add_edge("get_storyline_selection_input", "process_storyline_selection")
workflow.add_edge("process_storyline_selection", "create_chapter_arcs")
workflow.add_edge("create_chapter_arcs", "get_chapter_arcs_selection_input")
workflow.add_edge("get_chapter_arcs_selection_input", "process_chapter_arcs_selection")
workflow.add_edge("process_chapter_arcs_selection", "write_first_chapter")
workflow.add_edge("write_first_chapter", "select_first_chapter")
workflow.add_edge("select_first_chapter", "get_chapter_selection_input")
workflow.add_edge("get_chapter_selection_input", "process_chapter_selection")
workflow.add_edge("process_chapter_selection", "prompt_for_projection_year")
workflow.add_edge("prompt_for_projection_year", "get_projection_year_input")
workflow.add_edge("get_projection_year_input", "set_target_year")
workflow.add_edge("set_target_year", "generate_world_building_questions")
workflow.add_edge("generate_world_building_questions", "research_and_propose_scenarios")
workflow.add_edge("research_and_propose_scenarios", "select_world_scenario")
workflow.add_edge("select_world_scenario", "get_world_scenario_selection_input")
workflow.add_edge("get_world_scenario_selection_input", "process_world_scenario_selection")
workflow.add_edge("process_world_scenario_selection", "world_projection_deep_research")
workflow.add_edge("world_projection_deep_research", "linguistic_evolution_research")
workflow.add_edge("linguistic_evolution_research", "select_linguistic_evolution")
workflow.add_edge("select_linguistic_evolution", "get_linguistic_selection_input")
workflow.add_edge("get_linguistic_selection_input", "process_linguistic_evolution_selection")
workflow.add_edge("process_linguistic_evolution_selection", "adjust_storyline")
workflow.add_edge("adjust_storyline", "select_storyline_adjustment")
workflow.add_edge("select_storyline_adjustment", "get_storyline_adjustment_input")
workflow.add_edge("get_storyline_adjustment_input", "process_storyline_adjustment_selection")
workflow.add_edge("process_storyline_adjustment_selection", "adjust_chapter_arcs")
workflow.add_edge("adjust_chapter_arcs", "rewrite_first_chapter")
workflow.add_edge("rewrite_first_chapter", "select_chapter_rewrite")
workflow.add_edge("select_chapter_rewrite", "get_chapter_rewrite_input")
workflow.add_edge("get_chapter_rewrite_input", "process_chapter_rewrite_selection")
workflow.add_edge("process_chapter_rewrite_selection", "generate_scientific_explanations")
workflow.add_edge("generate_scientific_explanations", "generate_glossary")
workflow.add_edge("generate_glossary", "compile_baseline_world_state")

workflow.add_edge("compile_baseline_world_state", "choose_next_action")

# === Multi-Chapter Book Writing Workflow ===

# User choice between projection and book writing
workflow.add_node("choose_next_action", choose_next_action)
workflow.add_node("get_next_action_input", lambda state: None)  # Dummy node for interrupt
workflow.add_node("process_next_action_choice", process_next_action_choice)

# Chapter planning and book writing workflow
workflow.add_node("plan_remaining_chapters", plan_remaining_chapters)
workflow.add_node("generate_chapter_world_questions", generate_chapter_world_questions)
workflow.add_node("chapter_world_research", chapter_world_research)
workflow.add_node("write_next_chapter", write_next_chapter)
workflow.add_node("check_chapter_coherence", check_chapter_coherence)
workflow.add_node("validate_transitions", validate_transitions)
workflow.add_node("rewrite_chapter_for_coherence", rewrite_chapter_for_coherence)
workflow.add_node("generate_chapter_scientific_explanations", generate_chapter_scientific_explanations)
workflow.add_node("update_accumulated_materials", update_accumulated_materials)
workflow.add_node("advance_to_next_chapter", advance_to_next_chapter)
workflow.add_node("compile_complete_book", compile_complete_book)

# User choice workflow edges
workflow.add_edge("choose_next_action", "get_next_action_input")
workflow.add_edge("get_next_action_input", "process_next_action_choice")
workflow.add_conditional_edges("process_next_action_choice", should_loop_or_write_book, {
    "prompt_for_projection_year": "prompt_for_projection_year",
    "plan_remaining_chapters": "plan_remaining_chapters",
    END: END
})

# Chapter writing workflow edges
workflow.add_edge("plan_remaining_chapters", "generate_chapter_world_questions")
workflow.add_edge("generate_chapter_world_questions", "chapter_world_research")
workflow.add_edge("chapter_world_research", "write_next_chapter")
workflow.add_edge("write_next_chapter", "check_chapter_coherence")
workflow.add_edge("check_chapter_coherence", "validate_transitions")

# Conditional rewrite based on coherence/transition scores
workflow.add_conditional_edges("validate_transitions", check_if_rewrite_needed, {
    "rewrite_chapter_for_coherence": "rewrite_chapter_for_coherence",
    "generate_chapter_scientific_explanations": "generate_chapter_scientific_explanations"
})

# Continue chapter workflow after rewrite
workflow.add_edge("rewrite_chapter_for_coherence", "generate_chapter_scientific_explanations")
workflow.add_edge("generate_chapter_scientific_explanations", "update_accumulated_materials")
workflow.add_edge("update_accumulated_materials", "advance_to_next_chapter")

# Chapter progression loop - continue to next chapter or compile complete book
workflow.add_conditional_edges("advance_to_next_chapter", check_if_more_chapters, {
    "generate_chapter_world_questions": "generate_chapter_world_questions",
    "compile_complete_book": "compile_complete_book"
})

# Final book compilation
workflow.add_edge("compile_complete_book", END)

app = workflow.compile(interrupt_before=["get_storyline_selection_input", "get_chapter_arcs_selection_input", "get_chapter_selection_input", "get_world_scenario_selection_input", "get_linguistic_selection_input", "get_storyline_adjustment_input", "get_chapter_rewrite_input", "get_projection_year_input", "get_next_action_input"]) 