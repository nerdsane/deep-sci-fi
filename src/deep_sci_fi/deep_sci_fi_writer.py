import os
import asyncio
from datetime import datetime
from langchain_core.prompts import ChatPromptTemplate
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END

from typing_extensions import TypedDict
from typing import Optional
from langchain_core.runnables import RunnableConfig

from deep_sci_fi.prompts import (
    PARSE_USER_INPUT_PROMPT,
    LIGHT_FUTURE_CONTEXT_PROMPT,
    DIRECT_LOGLINES_PROMPT,
)

# ============================================================================
# STATE MANAGEMENT
# ============================================================================

class AgentState(TypedDict):
    """State for the Deep Sci-Fi Writer workflow"""
    # Input and parsing
    user_input: str
    target_year: Optional[int]
    human_condition: Optional[str]
    technology_context: Optional[str]
    constraint: Optional[str]
    tone: Optional[str]
    setting: Optional[str]
    
    # Generated content
    light_future_context: Optional[str]
    story_seed_options: Optional[list]
    selected_story_concept: Optional[str]
    story_selection_ready: Optional[bool]
    
    # Chapter writing (handled by CS agents)
    current_chapter: Optional[str]
    research_cache: Optional[dict]
    
    # System state
    output_dir: str
    starting_year: Optional[int]


# ============================================================================
# MODEL CONFIGURATION
# ============================================================================

class ModelProvider:
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
        # Creative narrative tasks - Claude Opus 4.1 for maximum creativity and logline generation
        "general_creative": {
            "provider": ModelProvider.ANTHROPIC,
            "model": "opus_4", 
            "thinking": True,  # Use thinking mode for better logline reasoning
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
            "temperature": 1.0,  # O3 models only support temperature=1
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
        model_string = cls.get_model_string(use_case)
        
        # O3 models only support temperature=1
        temperature = config.get("temperature", 0.8)
        if "o3" in model_string.lower():
            temperature = 1.0
            
        return {
            "temperature": temperature,
            "max_tokens": config.get("max_tokens", 8000)
        }
    
    @classmethod
    def supports_thinking(cls, use_case: str) -> bool:
        """Check if a use case should use thinking mode."""
        config = cls.USE_CASE_MODELS.get(use_case, cls.USE_CASE_MODELS["general_creative"])
        return config.get("thinking", False)
    
    @classmethod
    def create_model_instance(cls, use_case: str):
        """Create a model instance for a specific use case."""
        model_string = cls.get_model_string(use_case)
        params = cls.get_model_params(use_case)
        
        return init_chat_model(
            model=model_string,
            **params
        )


# Initialize models
general_model = ModelConfig.create_model_instance("general_creative")
    

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def save_output(output_dir: str, filename: str, content):
    """Saves content to a markdown file in the specified output directory."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Handle different content types
    if isinstance(content, list):
        # Convert list to string
        content_str = "\n".join(str(item) for item in content)
    elif isinstance(content, dict):
        # Convert dict to formatted string
        content_str = "\n".join(f"{key}: {value}" for key, value in content.items())
    else:
        # Assume it's already a string or can be converted
        content_str = str(content)
    
    file_path = os.path.join(output_dir, filename)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content_str)


def get_state_values_with_defaults(state: AgentState) -> tuple[int, str]:
    """Get target_year and human_condition with fallback defaults"""
    target_year = state.get("target_year") or (state.get("starting_year", 2024) + 60)
    human_condition = state.get("human_condition") or "What does it mean to be human in an age of technological transcendence?"
    return target_year, human_condition


def log_cs_mode(step_name: str):
    """Log which mode (CS or Direct) is being used for a step"""
    mode = "🏆 CS Competition" 
    print(f"--- {step_name}: Using {mode} ---")


# ============================================================================
# CORE WORKFLOW FUNCTIONS
# ============================================================================

async def parse_and_complete_user_input(state: AgentState, config: RunnableConfig):
    """Step 1: Parse and augment user input with extracted parameters"""
    user_input = state.get('user_input', '')
    if not user_input:
        raise ValueError("No user input provided")
    
    # Create output directory with timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_dir = os.path.join("output", timestamp)
    
    print("--- Parsing and Completing User Input ---")
    
    # Use general model to parse and complete user input
    prompt = ChatPromptTemplate.from_template(PARSE_USER_INPUT_PROMPT)
    response = general_model.invoke(prompt.format(user_input=user_input))
    
    content = response.content
    save_output(output_dir, "01_parsed_user_input.md", content)
    
    # Parse the structured output
    parsed_params = {}
    for line in content.split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip().lower().replace('_', '_').replace(' ', '_')
            value = value.strip()
            
            if key == "target_year":
                try:
                    parsed_params["target_year"] = int(value)
                except ValueError:
                    parsed_params["target_year"] = 2084  # Default fallback
            elif key in ["human_condition", "technology_context", "constraint", "tone", "setting"]:
                parsed_params[key] = value
    
    # Save parsed parameters
    params_content = f"# Parsed Parameters\n\n"
    for key, value in parsed_params.items():
        params_content += f"**{key.replace('_', ' ').title()}:** {value}\n\n"
    save_output(output_dir, "01_parsed_parameters.md", params_content)
    
    print("--- User Input Parsed and Augmented ---")
    
    return {
        "output_dir": output_dir,
        "starting_year": 2024,
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


async def generate_competitive_loglines_direct(state: AgentState, config: RunnableConfig):
    """Step 3 (Direct): Generate loglines using direct LLM call instead of CS competition"""
    if not (output_dir := state.get("output_dir")) or not (light_future_context := state.get("light_future_context")):
        raise ValueError("Required state for generating loglines is missing.")
    
    # Get values with fallback defaults
    target_year, human_condition = get_state_values_with_defaults(state)
    constraint = state.get("constraint") or "technological advancement"
    tone = state.get("tone") or "thoughtful and immersive"
    setting = state.get("setting") or "near-future Earth"
    
    log_cs_mode("Generate Loglines")
    
    # Use general creative model for direct logline generation
    prompt = ChatPromptTemplate.from_template(DIRECT_LOGLINES_PROMPT)
    response = general_model.invoke(prompt.format(
        original_user_request=state.get('user_input', ''),
        human_condition=human_condition,
        light_future_context=light_future_context,
        target_year=target_year,
        constraint=constraint,
        tone=tone,
        setting=setting
    ))
    
    loglines_content = response.content
    save_output(output_dir, "03_direct_loglines_generation.md", loglines_content)
    
    # Parse the direct response into direction_winners format for compatibility
    direction_winners = parse_direct_loglines_to_winners(loglines_content, target_year)
    
    # Save formatted options for user selection
    formatted_options = format_direction_winners_for_selection(direction_winners, "Direct LLM logline generation", target_year, human_condition)
    save_output(output_dir, "03_loglines_options.md", formatted_options)
    
    print("--- Direct LLM Logline Generation Complete ---")
    print(f"--- Generated {len(direction_winners)} direction sets with 3 loglines each ---")
    
    return {"story_seed_options": direction_winners}


def parse_direct_loglines_to_winners(loglines_content: str, target_year: int) -> list:
    """Parse direct loglines response into direction_winners format"""
    # This is a simplified parser - in production you'd want more robust parsing
    direction_winners = []
    
    # Split content into sections and extract loglines
    lines = loglines_content.split('\n')
    current_section = None
    current_loglines = []
    
    for line in lines:
        line = line.strip()
        if line.startswith('##') or line.startswith('**'):
            # New section
            if current_section and current_loglines:
                direction_winners.append({
                    'research_direction': current_section,
                    'core_assumption': f"Direct generation approach: {current_section}",
                    'scenario_content': f"## Top 3 Selected\n" + "\n".join([f"{i+1}. {logline}" for i, logline in enumerate(current_loglines)])
                })
            current_section = line.strip('#* ')
            current_loglines = []
        elif f'In {target_year}' in line and len(line) > 50:
            # This looks like a logline
            current_loglines.append(line.strip('123456789.- '))
    
    # Add the last section
    if current_section and current_loglines:
        direction_winners.append({
            'research_direction': current_section,
            'core_assumption': f"Direct generation approach: {current_section}",
            'scenario_content': f"## Top 3 Selected\n" + "\n".join([f"{i+1}. {logline}" for i, logline in enumerate(current_loglines)])
        })
    
    return direction_winners


def format_direction_winners_for_selection(direction_winners: list, approach: str, target_year: int, human_condition: str) -> str:
    """Format direction winners for user selection"""
    content = f"# Story Concept Selection Options\n\n"
    content += f"**Approach:** {approach}\n"
    content += f"**Target Year:** {target_year}\n"
    content += f"**Human Condition Theme:** {human_condition}\n\n"
    
    option_number = 1
    for winner in direction_winners:
        content += f"## Option {option_number}: {winner.get('research_direction', 'Unknown Approach')}\n\n"
        content += f"**Creative Philosophy:** {winner.get('core_assumption', 'No assumption available')}\n\n"
        content += winner.get('scenario_content', 'No content available')
        content += "\n\n---\n\n"
        option_number += 1
    
    return content


async def user_story_selection(state: AgentState, config: RunnableConfig):
    """Step 3.5: Allow user to select their preferred story concept"""
    if not (output_dir := state.get("output_dir")) or not (story_seed_options := state.get("story_seed_options")):
        raise ValueError("Required state for user story selection is missing.")
    
    # Get target_year and human_condition with fallback defaults
    target_year, human_condition = get_state_values_with_defaults(state)
    
    print("--- User Story Selection ---")
    
    # Format the options for user display
    formatted_options = format_direction_winners_for_selection(story_seed_options, "Story Concept Selection", target_year, human_condition)
    save_output(output_dir, "03_story_selection_options.md", formatted_options)
    
    print("--- Story selection options saved to 03_story_selection_options.md ---")
    print("--- Please select a story concept and set selected_story_concept in state ---")
    
    # This function doesn't automatically select - it prepares options for manual selection
    # The actual selection happens via state update outside this function
    return {"story_selection_ready": True}


# ============================================================================
# CS AGENT-BASED CHAPTER WRITING SYSTEM
# All functions below this point will be implemented with CS agents
# ============================================================================

async def initialize_cs_chapter_state(state: AgentState, config: RunnableConfig):
    """Initialize state for CS chapter writing subgraph"""
    
    if not (output_dir := state.get("output_dir")) or not (selected_story_concept := state.get("selected_story_concept")):
        raise ValueError("Required state for CS chapter writing is missing.")
    
    print("🚀 Initializing CS Agent-Based Chapter Writing System...")
    
    # Initialize CS state using the orchestrator
    cs_state = cs_chapter_orchestrator.initialize_cs_state(state)
    
    print("✅ CS state initialized - entering CS agent subgraph...")
    
    return cs_state


async def finalize_cs_chapter_output(state: AgentState, config: RunnableConfig):
    """Save final CS chapter outputs after subgraph completion"""
    
    output_dir = state.get("output_dir", "")
    
    # Save the final chapter to output
    if chapter_content := state.get("current_chapter"):
        save_output(output_dir, "04_cs_generated_chapter.md", chapter_content)
        print("💾 Final chapter saved to 04_cs_generated_chapter.md")
    
    # Save the final decision
    if final_decision := state.get("final_decision"):
        save_output(output_dir, "04_cs_final_decision.md", final_decision)
        print("📋 Final decision saved to 04_cs_final_decision.md")
    
    # Process summary is now generated by the CS subgraph with correct final state
    print("📊 CS process summary generated by subgraph with accurate completion flags")
    
    print("✅ CS Agent-Based Chapter Writing Complete!")
    
    return {
        "cs_chapter_complete": True
    }


# ============================================================================
# WORKFLOW SETUP
# ============================================================================

# Import CS chapter orchestrator
from co_scientist.agents.cs_chapter_orchestrator import cs_chapter_orchestrator

# Create the workflow
workflow = StateGraph(AgentState)

# Add the nodes we're keeping
workflow.add_node("parse_user_input", parse_and_complete_user_input)
workflow.add_node("generate_context", generate_light_future_context)
workflow.add_node("generate_loglines", generate_competitive_loglines_direct)
workflow.add_node("user_story_selection", user_story_selection)
workflow.add_node("initialize_cs_state", initialize_cs_chapter_state)

# Add CS chapter writing as a subgraph (this will show individual agents in Studio)
workflow.add_node("cs_chapter_writing", cs_chapter_orchestrator.graph)
workflow.add_node("finalize_cs_output", finalize_cs_chapter_output)

# Set up the basic flow
workflow.add_edge(START, "parse_user_input")
workflow.add_edge("parse_user_input", "generate_context")
workflow.add_edge("generate_context", "generate_loglines")
workflow.add_edge("generate_loglines", "user_story_selection")
workflow.add_edge("user_story_selection", "initialize_cs_state")
workflow.add_edge("initialize_cs_state", "cs_chapter_writing")
workflow.add_edge("cs_chapter_writing", "finalize_cs_output")
workflow.add_edge("finalize_cs_output", END)

# Compile the workflow with user selection interrupt
app = workflow.compile(
    interrupt_before=["user_story_selection"]
)

print(f"🚀 Deep Sci-Fi Writer initialized - UNDER RECONSTRUCTION!")
print("🔧 Converting to CS Agent-based system...")
print("⚡ Current flow: Parse → Context → Loglines → [USER SELECTION] → CS Agent System")
print("⏸️  Workflow pauses for story selection in LangGraph Studio!")
print("🚧 CS Agent system implementation in progress...") 