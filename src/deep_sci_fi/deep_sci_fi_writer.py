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
)

async def _run_deep_researcher(research_query: str, config: RunnableConfig) -> str:
    """Helper to run the deep_researcher subgraph and correctly parse its final output."""
    subgraph_config = config.copy()
    subgraph_config["configurable"].update({
        "research_model": model_config["research_model"],
        "summarization_model": model_config["research_model"],
        "compression_model": model_config["research_model"],
        "compression_model_max_tokens": 8000,
        "final_report_model": model_config["research_model"],
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
    storyline_choice: Optional[str]  # User's storyline selection (1 or 2)
    chapter_arcs: Optional[str]
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

# === Model Configuration ===
model_config = {
    "research_model": "openai:gpt-4.1-nano", # "anthropic:claude-3-5-sonnet-20241022",
    "writing_model": "openai:gpt-4.1-nano", # "anthropic:claude-3-7-sonnet-20250219", 
    "general_model": "openai:gpt-4.1-nano", # "anthropic:claude-3-7-sonnet-20250219",
    
    # Co-scientist configuration
    "save_intermediate_results": True,  # Enable intermediate file saving
}

# Initialize the models with retry logic
writing_model = init_chat_model(
    model_config["writing_model"], 
    temperature=0.7,
    max_tokens=8000 
).with_retry()

general_model = init_chat_model(
    model_config["general_model"], 
    temperature=0.7
).with_retry()


async def create_storyline(state: AgentState, config: RunnableConfig):
    print("--- Starting New Story with Co-Scientist Competition ---")
    run_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_dir = os.path.join("output", run_timestamp)
    starting_year = datetime.now().year
    
    # Use co_scientist for competitive storyline creation (generic, not sci-fi specific)
    co_scientist_input = CoScientistConfiguration.create_input_state(
        task_description="Create a compelling storyline for a novel",
        context=f"User's idea for the novel: {state['input']}",
        use_case=UseCase.STORYLINE_CREATION,
        domain_context="General fiction writing with emphasis on strong narrative structure and character development"
    )
    
    # Configure co_scientist for quick competition using regular LLM (not research)
    subgraph_config = config.copy()
    subgraph_config["configurable"].update({
        "research_model": model_config["research_model"],
        "general_model": model_config["general_model"],
        "use_case": "storyline_creation",
        "process_depth": "quick",         # Fast iteration
        "population_scale": "light",      # Quick processing
        "use_deep_researcher": False,     # Use regular LLM for creative writing
        "save_intermediate_results": True,
        "output_dir": output_dir
    })
    
    # Run co_scientist competition
    co_scientist_result = await co_scientist.ainvoke(co_scientist_input, subgraph_config)
    
    # Save detailed competition results
    if model_config.get("save_intermediate_results", True):
        # Save competition summary
        competition_summary = co_scientist_result.get("competition_summary", "")
        save_output(output_dir, "00_01a_storyline_competition_summary.md", competition_summary)
        
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
            "options_metadata": direction_winners
        }
        
        print("--- Co-Scientist Storyline Competition Complete ---")
        print("--- Two storyline options created. User selection required. ---")
        
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
    
    # Save individual option files for reference
    option_1_content = storyline_options.get("option_1", "")
    option_2_content = storyline_options.get("option_2", "")
    
    save_output(output_dir, "00_01a_storyline_option_1.md", option_1_content)
    save_output(output_dir, "00_01b_storyline_option_2.md", option_2_content)
    
    print("--- Storyline Options Prepared for User Selection ---")
    print(f"Option 1: {options_metadata[0].get('research_direction', 'Unknown')}")
    print(f"Option 2: {options_metadata[1].get('research_direction', 'Unknown')}")
    
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
    
    # Process user choice
    choice = str(user_choice).strip()
    if choice == "1":
        selected_storyline = option_1_content
        selected_option = options_metadata[0] if len(options_metadata) > 0 else {}
    elif choice == "2":
        selected_storyline = option_2_content
        selected_option = options_metadata[1] if len(options_metadata) > 1 else {}
    else:
        # Default to option 1 if invalid choice
        print(f"Invalid choice '{choice}', defaulting to Option 1")
        selected_storyline = option_1_content
        selected_option = options_metadata[0] if len(options_metadata) > 0 else {}
    
    save_output(output_dir, "00_01_selected_storyline.md", selected_storyline)
    
    print(f"--- Storyline Selected: {selected_option.get('research_direction', 'Unknown')} ---")
    
    return {
        "storyline": selected_storyline,
        "selected_scenario": selected_option.get('research_direction', 'Unknown')
    }

def create_chapter_arcs(state: AgentState):
    if not (output_dir := state.get("output_dir")) or not (storyline := state.get("storyline")):
        raise ValueError("Required state 'output_dir' or 'storyline' is missing.")
    prompt = ChatPromptTemplate.from_template(CREATE_CHAPTER_ARCS_PROMPT)
    response = writing_model.invoke(prompt.format(storyline=storyline))
    content = response.content
    save_output(output_dir, "00_02_chapter_arcs.md", content)
    print("--- Chapter Arcs Created ---")
    return {"chapter_arcs": content}

async def write_first_chapter(state: AgentState, config: RunnableConfig):
    if not (output_dir := state.get("output_dir")) or not (storyline := state.get("storyline")) or not (chapter_arcs := state.get("chapter_arcs")):
        raise ValueError("Required state for writing first chapter is missing.")
    
    print("--- Writing First Chapter with Co-Scientist Competition ---")
    
    # Use co_scientist for competitive chapter writing (generic, not sci-fi specific)
    co_scientist_input = CoScientistConfiguration.create_input_state(
        task_description="Write an engaging opening chapter that hooks readers and establishes the story world",
        context=f"Write the first chapter based on this storyline and chapter structure. The opening should immediately engage readers, establish the protagonist's voice, introduce the key conflict, and set up the story elements naturally.\n\nStoryline: {storyline}\n\nChapter Structure: {chapter_arcs}",
        use_case=UseCase.CHAPTER_WRITING,  # Use chapter writing template
        reference_material=f"Storyline: {storyline}\n\nChapter Arcs: {chapter_arcs}",
        domain_context="Fiction writing with strong character introduction and world-building"
    )
    
    # Configure co_scientist for quick competition using regular LLM (not research)
    subgraph_config = config.copy()
    subgraph_config["configurable"].update({
        "research_model": model_config["research_model"],
        "general_model": model_config["general_model"],
        "use_case": "chapter_writing",
        "process_depth": "quick",         # Fast iteration
        "population_scale": "light",      # Quick processing
        "use_deep_researcher": False,     # Use regular LLM for creative writing
        "save_intermediate_results": True,
        "output_dir": output_dir
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
    
    # Save individual option files for reference
    option_1_content = first_chapter_options.get("option_1", "")
    option_2_content = first_chapter_options.get("option_2", "")
    
    save_output(output_dir, "00_03a_first_chapter_option_1.md", option_1_content)
    save_output(output_dir, "00_03b_first_chapter_option_2.md", option_2_content)
    
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
        task_description=f"Analyze the provided story context and world-building questions to identify 3 fundamentally different technological/scientific assumption sets that would lead to meaningfully different futures for {target_year}.",
        context=questions,  # World-building questions
        use_case=UseCase.SCENARIO_GENERATION,
        reference_material=storyline,  # Story context
        domain_context="Science fiction world-building with focus on technological development and scientific plausibility",
        # Legacy fields for backward compatibility
        target_year=target_year,
        baseline_world_state=state.get("baseline_world_state"),
        years_in_future=state.get("years_in_future")
    )
    
    # Configure subgraph
    subgraph_config = config.copy()
    subgraph_config["configurable"].update({
        "research_model": model_config["research_model"],
        "general_model": model_config["general_model"],
        "search_api": "tavily",
        "output_dir": output_dir
    })

    # Invoke the co_scientist subgraph
    co_scientist_result = await co_scientist.ainvoke(
        co_scientist_input,
        subgraph_config
    )
    
    # Save detailed competition results
    if model_config.get("save_intermediate_results", True):
        # Save competition summary
        competition_summary = co_scientist_result.get("competition_summary", "")
        save_output(output_dir, f"{state['loop_count']:02d}_05a_competition_summary.md", competition_summary)
        
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
    """Format detailed co-scientist competition results for analysis."""
    
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
    detailed += f"- **Per Direction:** ~{len(population) // max(len(directions), 1)}\n\n"
    
    # Reflection results
    critiques = co_scientist_result.get("reflection_critiques", [])
    detailed += f"## Reflection Phase\n"
    detailed += f"- **Total Critiques:** {len(critiques)}\n"
    
    if critiques:
        # Count critiques by domain
        domain_counts = {}
        for critique in critiques:
            domain = critique.get("critique_domain", "Unknown")
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
        
        detailed += "- **By Domain:**\n"
        for domain, count in domain_counts.items():
            detailed += f"  - {domain}: {count}\n"
    
    detailed += "\n"
    
    # Tournament results
    winners = co_scientist_result.get("tournament_winners", [])
    detailed += f"## Tournament Results\n"
    detailed += f"- **Direction Winners:** {len(winners)}\n"
    for i, winner in enumerate(winners, 1):
        direction = winner.get("direction", "Unknown")
        detailed += f"  - Winner {i}: {direction}\n"
    
    detailed += "\n"
    
    # Evolution results
    evolved = co_scientist_result.get("evolved_scenarios", [])
    detailed += f"## Evolution Phase\n"
    detailed += f"- **Total Evolutions:** {len(evolved)}\n"
    
    if evolved:
        # Count by strategy
        strategy_counts = {}
        for evolution in evolved:
            strategy = evolution.get("strategy", "Unknown")
            strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
        
        detailed += "- **By Strategy:**\n"
        for strategy, count in strategy_counts.items():
            detailed += f"  - {strategy}: {count}\n"
    
    detailed += "\n"
    
    # Final selection
    top_scenarios = co_scientist_result.get("top_scenarios", [])
    detailed += f"## Final Selection\n"
    detailed += f"- **Top Scenarios Selected:** {len(top_scenarios)}\n"
    for i, scenario in enumerate(top_scenarios, 1):
        direction = scenario.get("research_direction", "Unknown")
        detailed += f"  - Scenario {i}: {direction}\n"
    
    return detailed

def select_world_scenario(state: AgentState):
    """User selection node - presents world scenario options and waits for user choice."""
    if not (output_dir := state.get("output_dir")) or not (world_scenario_options := state.get("world_scenario_options")):
        raise ValueError("Required state 'output_dir' or 'world_scenario_options' is missing.")
    
    # Present options to user through the interface
    options_metadata = world_scenario_options.get("options_metadata", [])
    if len(options_metadata) < 2:
        raise ValueError("Not enough world scenario options for user selection.")
    
    # Save individual option files for reference
    for i in range(len(options_metadata)):
        option_content = world_scenario_options.get(f"option_{i+1}", "")
        save_output(output_dir, f"{state['loop_count']:02d}_05a_world_scenario_option_{i+1}.md", option_content)
    
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
    if not (output_dir := state.get("output_dir")) or not (target_year := state.get("target_year")) or not (loop_count := state.get("loop_count") is not None) or not (selected_scenario := state.get("selected_scenario")):
        raise ValueError("Required state for world projection research is missing.")
    
    print("--- Using Co-Scientist Selected Scenario as Baseline (Already Research-Backed) ---")
    
    # Use the selected scenario as the baseline world state since it's already comprehensive
    world_state = f"# Baseline World State for {target_year}\n\n"
    world_state += "This world state is derived from co-scientist competition results and is already research-backed.\n\n"
    world_state += f"## Selected Scenario\n\n{state['selected_scenario']}\n\n"
    world_state += "Note: This scenario has undergone:\n"
    world_state += "- Deep literature research by specialized teams\n"
    world_state += "- Expert critique by domain specialists\n" 
    world_state += "- Competitive tournament selection\n"
    world_state += "- Evolution and improvement phases\n"
    world_state += "- Meta-review synthesis\n\n"
    world_state += "No additional research is required as the scenario is scientifically grounded and comprehensive."
    
    save_output(output_dir, f"{state['loop_count']:02d}_07_world_state_{target_year}.md", world_state)
    return {"baseline_world_state": state["selected_scenario"]}

async def linguistic_evolution_research(state: AgentState, config: RunnableConfig):
    """Uses co_scientist to research the linguistic evolution of the world with competitive analysis."""
    if not (output_dir := state.get("output_dir")) or not (target_year := state.get("target_year")) or not (loop_count := state.get("loop_count") is not None) or not (baseline_world_state := state.get("baseline_world_state")) or not (storyline := state.get("storyline")) or not (chapter_arcs := state.get("chapter_arcs")) or not (first_chapter := state.get("first_chapter")) or not (years_in_future := state.get("years_in_future")):
        raise ValueError("Required state for linguistic research is missing.")
        
    print("--- Conducting Co-Scientist Competition on Linguistic Evolution ---")

    # Prepare research context based on loop iteration
    if state.get("loop_count", 0) > 0:
        task_description = f"Analyze and project linguistic evolution from baseline world state through {years_in_future} additional years"
        context = f"Building on the established world state, project how language, communication, and cultural expression will evolve over the next {years_in_future} years given technological and social developments.\n\nBaseline World: {baseline_world_state}\n\nStory Context: {storyline}\n\nChapter Structure: {chapter_arcs}\n\nFirst Chapter: {first_chapter}\n\nTarget Year: {target_year}"
    else:
        task_description = f"Analyze linguistic evolution and communication changes by {target_year}"
        context = f"Research how language, communication methods, cultural expression, and social linguistics will evolve given the technological and societal changes described in the world state.\n\nWorld State: {baseline_world_state}\n\nTarget Year: {target_year}"

    # Use co_scientist for competitive linguistic analysis with research
    co_scientist_input = CoScientistConfiguration.create_input_state(
        task_description=task_description,
        context=context,
        use_case=UseCase.LINGUISTIC_EVOLUTION,
        reference_material=f"World State: {baseline_world_state}\n\nStoryline: {storyline}",
        domain_context="Linguistics, sociolinguistics, communication technology, cultural evolution, and anthropology"
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
        "research_model": model_config["research_model"],
        "general_model": model_config["general_model"],
        "use_case": "linguistic_evolution",
        "process_depth": "quick",     # Fast iteration
        "population_scale": "light",  # Quick processing
        "use_deep_researcher": True,  # Use deep research for linguistic analysis
        "reflection_domains": ["linguistics", "technology", "sociology and anthropology"],
        "world_state_context": world_state_context,  # Pass comprehensive world state and previous research
        "save_intermediate_results": True,
        "output_dir": output_dir
    })
    
    # Run co_scientist competition
    co_scientist_result = await co_scientist.ainvoke(co_scientist_input, subgraph_config)
    
    # Save detailed competition results
    if model_config.get("save_intermediate_results", True):
        # Save competition summary
        competition_summary = co_scientist_result.get("competition_summary", "")
        save_output(output_dir, f"{state['loop_count']:02d}_08a_linguistic_competition_summary.md", competition_summary)
        
        # Save detailed competition data
        detailed_results = format_detailed_competition_results(co_scientist_result)
        save_output(output_dir, f"{state['loop_count']:02d}_08b_linguistic_competition_details.md", detailed_results)
        
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
        # Co-scientist failed to produce direction winners - this is a system failure
        raise RuntimeError("Co-scientist linguistic evolution competition failed to produce direction winners. Check competition configuration and model availability.")

def select_linguistic_evolution(state: AgentState):
    """User selection node - presents linguistic evolution options and waits for user choice."""
    if not (output_dir := state.get("output_dir")) or not (linguistic_evolution_options := state.get("linguistic_evolution_options")) or not (loop_count := state.get("loop_count") is not None):
        raise ValueError("Required state 'output_dir' or 'linguistic_evolution_options' is missing.")
    
    # Present options to user through the interface
    options_metadata = linguistic_evolution_options.get("options_metadata", [])
    if len(options_metadata) < 2:
        raise ValueError("Not enough linguistic evolution options for user selection.")
    
    # Save individual option files for reference
    option_1_content = linguistic_evolution_options.get("option_1", "")
    option_2_content = linguistic_evolution_options.get("option_2", "")
    
    save_output(output_dir, f"{state['loop_count']:02d}_08a_linguistic_option_1.md", option_1_content)
    save_output(output_dir, f"{state['loop_count']:02d}_08b_linguistic_option_2.md", option_2_content)
    
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
    if not (output_dir := state.get("output_dir")) or not (loop_count := state.get("loop_count") is not None) or not (storyline := state.get("storyline")) or not (baseline_world_state := state.get("baseline_world_state")) or not (linguistic_evolution := state.get("linguistic_evolution")):
        raise ValueError("Required state for adjusting storyline is missing.")
    
    print("--- Adjusting Storyline with Co-Scientist Competition ---")
    
    # Use co_scientist for competitive storyline adjustment
    co_scientist_input = CoScientistConfiguration.create_input_state(
        task_description="Revise and enhance the storyline to integrate world-building developments and linguistic evolution",
        context=f"Adjust the original storyline to incorporate the detailed world-building and linguistic evolution that has been developed. The revised storyline should seamlessly integrate new technological, social, and cultural developments while maintaining narrative coherence and character consistency.\n\nOriginal Storyline: {storyline}\n\nWorld Developments: {baseline_world_state}\n\nLinguistic Evolution: {linguistic_evolution}",
        use_case=UseCase.STORYLINE_ADJUSTMENT,
        reference_material=f"Original Storyline: {storyline}",
        domain_context="Science fiction narrative development with world-building integration and linguistic consistency"
    )
    
    # Configure co_scientist for full competition with world-aware reflection
    subgraph_config = config.copy()
    subgraph_config["configurable"].update({
        "research_model": model_config["research_model"],
        "general_model": model_config["general_model"],
        "use_case": "storyline_adjustment",
        "process_depth": "standard",  # Include generate → reflect → evolve
        "population_scale": "light",  # Keep processing reasonable
        "use_deep_researcher": False,  # Use regular LLM for creative writing
        "reflection_domains": ["narrative_structure", "world_building", "character_development", "thematic_coherence", "world_integration"],
        "world_state_context": f"Baseline World State: {baseline_world_state}\n\nLinguistic Evolution: {linguistic_evolution}",  # Pass world context for reflection
        "save_intermediate_results": True,
        "output_dir": output_dir
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
    
    # Save individual option files for reference
    option_1_content = storyline_adjustment_options.get("option_1", "")
    option_2_content = storyline_adjustment_options.get("option_2", "")
    
    save_output(output_dir, f"{state['loop_count']:02d}_09a_storyline_adjustment_option_1.md", option_1_content)
    save_output(output_dir, f"{state['loop_count']:02d}_09b_storyline_adjustment_option_2.md", option_2_content)
    
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

def adjust_chapter_arcs(state: AgentState):
    if not (output_dir := state.get("output_dir")) or not (loop_count := state.get("loop_count") is not None) or not (revised_storyline := state.get("revised_storyline")) or not (baseline_world_state := state.get("baseline_world_state")) or not (chapter_arcs := state.get("chapter_arcs")) or not (linguistic_evolution := state.get("linguistic_evolution")):
        raise ValueError("Required state for adjusting chapter arcs is missing.")
    prompt = ChatPromptTemplate.from_template(ADJUST_CHAPTER_ARCS_PROMPT)
    response = writing_model.invoke(prompt.format(revised_storyline=revised_storyline, baseline_world_state=baseline_world_state, chapter_arcs=chapter_arcs, linguistic_evolution=linguistic_evolution))
    content = response.content
    save_output(output_dir, f"{state['loop_count']:02d}_10_revised_chapter_arcs.md", content)
    return {"revised_chapter_arcs": content}

async def rewrite_first_chapter(state: AgentState, config: RunnableConfig):
    if not (output_dir := state.get("output_dir")) or not (target_year := state.get("target_year")) or not (loop_count := state.get("loop_count") is not None) or not (revised_storyline := state.get("revised_storyline")) or not (revised_chapter_arcs := state.get("revised_chapter_arcs")) or not (baseline_world_state := state.get("baseline_world_state")) or not (first_chapter := state.get("first_chapter")) or not (linguistic_evolution := state.get("linguistic_evolution")):
        raise ValueError("Required state for rewriting chapter is missing.")
    
    print("--- Rewriting First Chapter with Co-Scientist Competition ---")
    
    # Use co_scientist for competitive chapter rewriting
    co_scientist_input = CoScientistConfiguration.create_input_state(
        task_description="Rewrite the first chapter to fully integrate the developed world-building, linguistic evolution, and narrative revisions",
        context=f"Completely rewrite the opening chapter to seamlessly incorporate all the world-building, linguistic evolution, and storyline developments. The rewritten chapter should feel natural and immersive, using the evolved language and cultural elements while maintaining strong narrative pacing and character development.\n\nRevised Storyline: {revised_storyline}\n\nRevised Chapter Structure: {revised_chapter_arcs}\n\nWorld State: {baseline_world_state}\n\nLinguistic Evolution: {linguistic_evolution}\n\nTarget Year: {target_year}",
        use_case=UseCase.CHAPTER_REWRITING,
        reference_material=f"Original Chapter: {first_chapter}",
        domain_context=f"Hard science fiction chapter set in {target_year} with evolved linguistics and advanced world-building"
    )
    
    # Configure co_scientist for full competition with world-aware reflection
    subgraph_config = config.copy()
    subgraph_config["configurable"].update({
        "research_model": model_config["research_model"],
        "general_model": model_config["general_model"],
        "use_case": "chapter_rewriting",
        "process_depth": "standard",  # Include generate → reflect → evolve
        "population_scale": "light",  # Keep processing reasonable
        "use_deep_researcher": False,  # Use regular LLM for creative writing
        "reflection_domains": ["narrative_structure", "world_building", "character_development", "prose_style", "world_integration", "linguistic_consistency"],
        "world_state_context": f"Baseline World State: {baseline_world_state}\n\nLinguistic Evolution: {linguistic_evolution}\n\nRevised Storyline: {revised_storyline}",  # Pass world context for reflection
        "save_intermediate_results": True,
        "output_dir": output_dir
    })
    
    # Run co_scientist competition
    co_scientist_result = await co_scientist.ainvoke(co_scientist_input, subgraph_config)
    
    # Save detailed competition results
    if model_config.get("save_intermediate_results", True):
        # Save competition summary
        competition_summary = co_scientist_result.get("competition_summary", "")
        save_output(output_dir, f"{state['loop_count']:02d}_11a_chapter_rewrite_competition_summary.md", competition_summary)
        
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
    
    # Save individual option files for reference
    option_1_content = chapter_rewrite_options.get("option_1", "")
    option_2_content = chapter_rewrite_options.get("option_2", "")
    
    save_output(output_dir, f"{state['loop_count']:02d}_11a_chapter_rewrite_option_1.md", option_1_content)
    save_output(output_dir, f"{state['loop_count']:02d}_11b_chapter_rewrite_option_2.md", option_2_content)
    
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
    if not (output_dir := state.get("output_dir")) or not (loop_count := state.get("loop_count") is not None) or not (revised_first_chapter := state.get("revised_first_chapter")) or not (linguistic_evolution := state.get("linguistic_evolution")):
        raise ValueError("Required state for generating glossary is missing.")
    prompt = ChatPromptTemplate.from_template(GENERATE_GLOSSARY_PROMPT)
    response = general_model.invoke(prompt.format(revised_first_chapter=revised_first_chapter, linguistic_evolution=linguistic_evolution))
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
workflow.add_edge("create_chapter_arcs", "write_first_chapter")
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

workflow.add_conditional_edges("compile_baseline_world_state", should_loop, {"prompt_for_projection_year": "prompt_for_projection_year", END: END})

app = workflow.compile(interrupt_before=["get_storyline_selection_input", "get_chapter_selection_input", "get_world_scenario_selection_input", "get_linguistic_selection_input", "get_storyline_adjustment_input", "get_chapter_rewrite_input", "get_projection_year_input"]) 