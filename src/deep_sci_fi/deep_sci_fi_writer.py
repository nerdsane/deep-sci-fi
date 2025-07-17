import os
from datetime import datetime
from langchain_core.prompts import ChatPromptTemplate
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict, Annotated
from typing import Optional
import operator
import uuid
from langchain_core.messages import HumanMessage, AIMessage
from open_deep_research.deep_researcher import deep_researcher
from co_scientist.co_scientist import co_scientist
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from deep_sci_fi.prompts import (
    CREATE_STORYLINE_PROMPT,
    CREATE_CHAPTER_ARCS_PROMPT,
    WRITE_FIRST_CHAPTER_PROMPT,
    GENERATE_WORLD_BUILDING_QUESTIONS_PROMPT,
    RESEARCH_THREE_SCENARIOS_PROMPT,
    CRITIQUE_SCENARIO_PROMPT,
    CREATE_BASELINE_WORLD_STATE_PROMPT,
    EVOLVE_BASELINE_WORLD_STATE_PROMPT,
    INITIAL_LINGUISTIC_RESEARCH_PROMPT,
    PROJECT_LINGUISTIC_EVOLUTION_PROMPT,
    ADJUST_STORYLINE_PROMPT,
    ADJUST_CHAPTER_ARCS_PROMPT,
    REWRITE_CHAPTER_ONE_PROMPT,
    GENERATE_SCIENTIFIC_EXPLANATIONS_PROMPT,
    GENERATE_GLOSSARY_PROMPT,
    PROJECT_QUESTIONS_PROMPT,
    PROJECT_THREE_SCENARIOS_PROMPT,
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

async def _run_co_scientist(research_context: str, config: RunnableConfig, **kwargs) -> dict:
    """Helper to run the co_scientist subgraph for competitive scenario generation."""
    subgraph_config = config.copy()
    subgraph_config["configurable"].update({
        "research_model": model_config["research_model"],
        "general_model": model_config["general_model"],
        "search_api": "tavily",
        "scenarios_per_direction": model_config.get("scenarios_per_direction", 6),
        "parallel_directions": model_config.get("parallel_directions", 3),
        "enable_parallel_execution": model_config.get("enable_parallel_execution", True),
    })

    co_scientist_input = {
        "research_context": research_context,
        **kwargs  # storyline, target_year, baseline_world_state, years_in_future
    }
    
    # Pass output_dir to co_scientist configuration
    if "output_dir" in kwargs:
        subgraph_config["configurable"]["output_dir"] = kwargs["output_dir"]

    final_state = {}
    async for chunk in co_scientist.astream(
        co_scientist_input,
        subgraph_config,
        stream_mode="values"
    ):
        final_state = chunk
    
    return final_state

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
    chapter_arcs: Optional[str]
    first_chapter: Optional[str]
    world_building_questions: Optional[str]
    world_building_research: Optional[str]
    world_building_scenarios: Optional[str]
    scenario_critique: Optional[str]
    linguistic_evolution: Optional[str]
    revised_storyline: Optional[str]
    revised_chapter_arcs: Optional[str]
    revised_first_chapter: Optional[str]
    scientific_explanations: Optional[str]
    glossary: Optional[str]

# === Model Configuration ===
model_config = {
    "research_model": "openai:o4-mini", # "anthropic:claude-3-5-sonnet-20241022",
    "writing_model": "anthropic:claude-3-7-sonnet-20250219", 
    "general_model": "anthropic:claude-3-7-sonnet-20250219",
    
    # Co-scientist configuration
    "use_co_scientist": True,
    "scenarios_per_direction": 6,
    "parallel_directions": 3,
    "enable_parallel_execution": True,
    "save_intermediate_results": True,  # Enable intermediate file saving
    "reflection_domains": ["physics", "biology", "engineering", "social_science", "economics"],
    "evolution_strategies": ["feasibility", "creativity", "synthesis", "detail_enhancement"],
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


def create_storyline(state: AgentState):
    print("--- Starting New Story ---")
    run_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_dir = os.path.join("output", run_timestamp)
    starting_year = datetime.now().year
    prompt = ChatPromptTemplate.from_template(CREATE_STORYLINE_PROMPT)
    response = writing_model.invoke(prompt.format(input=state['input']))
    storyline = response.content
    save_output(output_dir, "00_01_storyline.md", storyline)
    print("--- Storyline Created ---")
    return {
        "output_dir": output_dir,
        "starting_year": starting_year,
        "target_year": starting_year,
        "loop_count": 0,
        "messages": [],
        "storyline": storyline,
        "years_in_future": None,
        "baseline_world_state": None,
        "chapter_arcs": None,
        "first_chapter": None,
        "world_building_questions": None,
        "world_building_research": None,
        "world_building_scenarios": None,
        "selected_scenario": None,
        "scenario_critique": None,
        "linguistic_evolution": None,
        "revised_storyline": None,
        "revised_chapter_arcs": None,
        "revised_first_chapter": None,
        "scientific_explanations": None,
        "glossary": None,
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

def write_first_chapter(state: AgentState):
    if not (output_dir := state.get("output_dir")) or not (storyline := state.get("storyline")) or not (chapter_arcs := state.get("chapter_arcs")):
        raise ValueError("Required state for writing first chapter is missing.")
    prompt = ChatPromptTemplate.from_template(WRITE_FIRST_CHAPTER_PROMPT)
    response = writing_model.invoke(prompt.format(storyline=storyline, chapter_arcs=chapter_arcs))
    content = response.content
    save_output(output_dir, "00_03_first_chapter.md", content)
    print("--- First Chapter Written ---")
    return {"first_chapter": content}

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
    """Uses co_scientist competitive tournament to generate and rank high-quality scenarios."""
    if not (output_dir := state.get("output_dir")) or not (target_year := state.get("target_year")) or not (loop_count := state.get("loop_count") is not None) or not (questions := state.get("world_building_questions")) or not (storyline := state.get("storyline")) or not (chapter_arcs := state.get("chapter_arcs")) or not (first_chapter := state.get("first_chapter")):
        raise ValueError("Required state for this research step is missing.")
    
    # Check if co_scientist is enabled
    if model_config.get("use_co_scientist", False):
        print("--- Starting Co-Scientist Competition ---")
        
        # Run co_scientist competitive tournament
        co_scientist_result = await _run_co_scientist(
            research_context=questions,
            config=config,
            storyline=storyline,
            target_year=target_year,
            baseline_world_state=state.get("baseline_world_state"),
            years_in_future=state.get("years_in_future"),
            output_dir=output_dir
        )
        
        # Format top scenarios for user selection
        top_scenarios = co_scientist_result.get("top_scenarios", [])
        competition_summary = co_scientist_result.get("competition_summary", "")
        
        # Format scenarios for user presentation
        formatted_scenarios = format_co_scientist_scenarios(top_scenarios, competition_summary)
        
        # Save intermediate results for debugging
        if model_config.get("save_intermediate_results", True):
            save_output(output_dir, f"{state['loop_count']:02d}_05a_competition_summary.md", competition_summary)
            
            # Save detailed competition data
            detailed_results = format_detailed_competition_results(co_scientist_result)
            save_output(output_dir, f"{state['loop_count']:02d}_05b_detailed_results.md", detailed_results)
        
        save_output(output_dir, f"{state['loop_count']:02d}_05_world_building_scenarios.md", formatted_scenarios)
        print("--- Co-Scientist Competition Complete ---")
        
        return {"world_building_scenarios": formatted_scenarios}
    
    else:
        # Fallback to original deep_researcher approach
        print("--- Researching and Proposing Scenarios (Original Method) ---")
        
        if state.get("baseline_world_state") and state.get("years_in_future"):
            research_query = PROJECT_THREE_SCENARIOS_PROMPT.format(
                questions=questions,
                baseline_world_state=state["baseline_world_state"],
                years_to_project=state["years_in_future"]
            )
        else:
            research_query = RESEARCH_THREE_SCENARIOS_PROMPT.format(
                questions=questions, 
                target_year=target_year,
                storyline=storyline,
                chapter_arcs=chapter_arcs,
                first_chapter=first_chapter
            )
        
        scenarios = await _run_deep_researcher(research_query, config)
        
        save_output(output_dir, f"{state['loop_count']:02d}_05_world_building_scenarios.md", scenarios)
        print("--- World-Building Scenarios Proposed ---")
        return {"world_building_scenarios": scenarios}

def format_co_scientist_scenarios(top_scenarios: list, competition_summary: str) -> str:
    """Format co_scientist competition results for user selection."""
    
    formatted_output = "# Top World-Building Scenarios (Co-Scientist Competition Winners)\n\n"
    formatted_output += "These scenarios have been refined through competitive multi-agent tournament, reflection, and evolution.\n\n"
    
    # Add competition overview
    formatted_output += "## Competition Overview\n"
    formatted_output += competition_summary + "\n\n"
    
    # Format each scenario
    for i, scenario in enumerate(top_scenarios[:3], 1):
        formatted_output += f"## Scenario {i}: {scenario.get('research_direction', 'Unknown Direction')}\n"
        formatted_output += f"**Competition Rank: #{scenario.get('competition_rank', i)}**\n\n"
        formatted_output += f"**Selection Reasoning:** {scenario.get('selection_reasoning', 'Selected by competitive tournament')}\n\n"
        formatted_output += f"{scenario.get('scenario_content', 'No content available')}\n\n"
        formatted_output += "---\n\n"
    
    formatted_output += "## Selection Instructions\n"
    formatted_output += "Please review these scenarios and provide the full text of your chosen scenario in the `selected_scenario` field.\n"
    formatted_output += "You may also modify or combine elements from multiple scenarios.\n\n"
    formatted_output += "Note: These scenarios have been scientifically validated through multi-agent competition and are ready for development.\n"
    
    return formatted_output

def format_detailed_competition_results(co_scientist_result: dict) -> str:
    """Format detailed competition results for debugging and analysis."""
    
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

def prompt_for_scenario_selection(state: AgentState):
    """Adds a message to the state to ask the user to select a scenario."""
    message = AIMessage(
        content="The research is complete and three potential scenarios have been proposed. Please review the scenarios and provide the full text of the one you'd like to develop further in the `selected_scenario` field."
    )
    return {"messages": [message]}

def critique_scenario(state: AgentState):
    """Critically reflects on the selected scenario to identify second-order effects and unanswered questions."""
    if not (output_dir := state.get("output_dir")) or not (target_year := state.get("target_year")) or not (loop_count := state.get("loop_count") is not None) or not (selected_scenario := state.get("selected_scenario")):
        raise ValueError("Required state for critiquing scenario is missing.")
    
    # Skip critique if co_scientist is enabled (scenarios already thoroughly critiqued)
    if model_config.get("use_co_scientist", False):
        print("--- Skipping Scenario Critique (Already Done by Co-Scientist) ---")
        content = "Scenario critique was performed during the co-scientist competition phase. See detailed competition results for comprehensive analysis."
        save_output(output_dir, f"{state['loop_count']:02d}_07_scenario_critique.md", content)
        return {"scenario_critique": content}
    
    # Original critique for non-co_scientist scenarios
    if not (world_building_scenarios := state.get("world_building_scenarios")) or not (storyline := state.get("storyline")) or not (chapter_arcs := state.get("chapter_arcs")) or not (first_chapter := state.get("first_chapter")) or not (years_in_future := state.get("years_in_future")):
        raise ValueError("Required state for traditional critiquing scenario is missing.")
        
    prompt = ChatPromptTemplate.from_template(CRITIQUE_SCENARIO_PROMPT)
    response = general_model.invoke(prompt.format(
        selected_scenario=selected_scenario, 
        target_year=target_year,
        world_building_scenarios=world_building_scenarios,
        storyline=storyline,
        chapter_arcs=chapter_arcs,
        first_chapter=first_chapter,
        years_in_future=years_in_future
    ))
    content = response.content
    save_output(output_dir, f"{state['loop_count']:02d}_07_scenario_critique.md", content)
    print("--- Scenario Critique Complete ---")
    return {"scenario_critique": content}

async def world_projection_deep_research(state: AgentState, config: RunnableConfig):
    if not (output_dir := state.get("output_dir")) or not (target_year := state.get("target_year")) or not (loop_count := state.get("loop_count") is not None) or not (selected_scenario := state.get("selected_scenario")):
        raise ValueError("Required state for world projection research is missing.")
    
    # Skip deep research if co_scientist is enabled (scenarios already research-backed)
    if model_config.get("use_co_scientist", False):
        print("--- Skipping World Projection Research (Co-Scientist Scenarios Already Research-Backed) ---")
        
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
        
        save_output(output_dir, f"{state['loop_count']:02d}_08_world_state_{target_year}.md", world_state)
        return {"baseline_world_state": state["selected_scenario"]}
    
    # Original workflow for non-co_scientist scenarios
    if not (scenario_critique := state.get("scenario_critique")):
        raise ValueError("Required state for traditional world projection research is missing.")
        
    print("--- Conducting Baseline World State Research ---")
    if baseline_world_state := state.get("baseline_world_state"):
        final_query = EVOLVE_BASELINE_WORLD_STATE_PROMPT.format(baseline_world_state=baseline_world_state, selected_scenario=state["selected_scenario"], scenario_critique=scenario_critique, target_year=target_year)
    else:
        final_query = CREATE_BASELINE_WORLD_STATE_PROMPT.format(selected_scenario=state["selected_scenario"], scenario_critique=scenario_critique, target_year=target_year)
    world_state = await _run_deep_researcher(final_query, config)
    save_output(output_dir, f"{state['loop_count']:02d}_08_world_state_{target_year}.md", world_state)
    print("--- Baseline World State Created ---")
    return {"baseline_world_state": world_state}

async def linguistic_evolution_research(state: AgentState, config: RunnableConfig):
    """Uses the deep_researcher to research the linguistic evolution of the world."""
    if not (output_dir := state.get("output_dir")) or not (target_year := state.get("target_year")) or not (loop_count := state.get("loop_count") is not None) or not (baseline_world_state := state.get("baseline_world_state")) or not (storyline := state.get("storyline")) or not (chapter_arcs := state.get("chapter_arcs")) or not (first_chapter := state.get("first_chapter")) or not (years_in_future := state.get("years_in_future")):
        raise ValueError("Required state for linguistic research is missing.")
        
    print("--- Conducting Deep Research on Linguistic Evolution ---")

    if state.get("loop_count", 0) > 0:
        research_query = PROJECT_LINGUISTIC_EVOLUTION_PROMPT.format(
            baseline_world_state=baseline_world_state,
            new_world_state_developments=state.get("world_projection_deep_research", ""), 
            target_year=target_year,
            years_in_future=years_in_future,
            storyline=storyline,
            chapter_arcs=chapter_arcs,
            first_chapter=first_chapter
        )
    else:
        research_query = INITIAL_LINGUISTIC_RESEARCH_PROMPT.format(
            baseline_world_state=baseline_world_state, 
            target_year=target_year
        )

    linguistic_report = await _run_deep_researcher(research_query, config)

    save_output(output_dir, f"{state['loop_count']:02d}_09_linguistic_evolution.md", linguistic_report)
    print("--- Linguistic Evolution Research Complete ---")
    return {"linguistic_evolution": linguistic_report}

def adjust_storyline(state: AgentState):
    if not (output_dir := state.get("output_dir")) or not (loop_count := state.get("loop_count") is not None) or not (storyline := state.get("storyline")) or not (baseline_world_state := state.get("baseline_world_state")) or not (linguistic_evolution := state.get("linguistic_evolution")):
        raise ValueError("Required state for adjusting storyline is missing.")
    prompt = ChatPromptTemplate.from_template(ADJUST_STORYLINE_PROMPT)
    response = writing_model.invoke(prompt.format(storyline=storyline, baseline_world_state=baseline_world_state, linguistic_evolution=linguistic_evolution))
    content = response.content
    save_output(output_dir, f"{state['loop_count']:02d}_10_revised_storyline.md", content)
    return {"revised_storyline": content}

def adjust_chapter_arcs(state: AgentState):
    if not (output_dir := state.get("output_dir")) or not (loop_count := state.get("loop_count") is not None) or not (revised_storyline := state.get("revised_storyline")) or not (baseline_world_state := state.get("baseline_world_state")) or not (chapter_arcs := state.get("chapter_arcs")) or not (linguistic_evolution := state.get("linguistic_evolution")):
        raise ValueError("Required state for adjusting chapter arcs is missing.")
    prompt = ChatPromptTemplate.from_template(ADJUST_CHAPTER_ARCS_PROMPT)
    response = writing_model.invoke(prompt.format(revised_storyline=revised_storyline, baseline_world_state=baseline_world_state, chapter_arcs=chapter_arcs, linguistic_evolution=linguistic_evolution))
    content = response.content
    save_output(output_dir, f"{state['loop_count']:02d}_11_revised_chapter_arcs.md", content)
    return {"revised_chapter_arcs": content}

def rewrite_first_chapter(state: AgentState):
    if not (output_dir := state.get("output_dir")) or not (target_year := state.get("target_year")) or not (loop_count := state.get("loop_count") is not None) or not (revised_storyline := state.get("revised_storyline")) or not (revised_chapter_arcs := state.get("revised_chapter_arcs")) or not (baseline_world_state := state.get("baseline_world_state")) or not (first_chapter := state.get("first_chapter")) or not (linguistic_evolution := state.get("linguistic_evolution")):
        raise ValueError("Required state for rewriting chapter is missing.")
    prompt = ChatPromptTemplate.from_template(REWRITE_CHAPTER_ONE_PROMPT)
    response = writing_model.invoke(prompt.format(revised_storyline=revised_storyline, revised_chapter_arcs=revised_chapter_arcs, baseline_world_state=baseline_world_state, first_chapter=first_chapter, linguistic_evolution=linguistic_evolution, target_year=target_year))
    content = response.content
    save_output(output_dir, f"{state['loop_count']:02d}_12_revised_first_chapter.md", content)
    return {"revised_first_chapter": content}

def generate_scientific_explanations(state: AgentState):
    if not (output_dir := state.get("output_dir")) or not (loop_count := state.get("loop_count") is not None) or not (revised_first_chapter := state.get("revised_first_chapter")) or not (baseline_world_state := state.get("baseline_world_state")):
        raise ValueError("Required state for generating scientific explanations is missing.")
    prompt = ChatPromptTemplate.from_template(GENERATE_SCIENTIFIC_EXPLANATIONS_PROMPT)
    response = general_model.invoke(prompt.format(revised_first_chapter=revised_first_chapter, baseline_world_state=baseline_world_state))
    content = response.content
    save_output(output_dir, f"{state['loop_count']:02d}_13_scientific_explanations.md", content)
    return {"scientific_explanations": content}

def generate_glossary(state: AgentState):
    if not (output_dir := state.get("output_dir")) or not (loop_count := state.get("loop_count") is not None) or not (revised_first_chapter := state.get("revised_first_chapter")) or not (linguistic_evolution := state.get("linguistic_evolution")):
        raise ValueError("Required state for generating glossary is missing.")
    prompt = ChatPromptTemplate.from_template(GENERATE_GLOSSARY_PROMPT)
    response = general_model.invoke(prompt.format(revised_first_chapter=revised_first_chapter, linguistic_evolution=linguistic_evolution))
    content = response.content
    save_output(output_dir, f"{state['loop_count']:02d}_14_glossary.md", content)
    return {"glossary": content}

def compile_baseline_world_state(state: AgentState):
    if not (output_dir := state.get("output_dir")) or not (target_year := state.get("target_year")) or not (loop_count := state.get("loop_count") is not None) or not (selected_scenario := state.get("selected_scenario")) or not (scenario_critique := state.get("scenario_critique")) or not (baseline_world_state := state.get("baseline_world_state")) or not (linguistic_evolution := state.get("linguistic_evolution")) or not (scientific_explanations := state.get("scientific_explanations")) or not (glossary := state.get("glossary")):
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
    save_output(output_dir, f"{state['loop_count']:02d}_15_baseline_world_state.md", baseline_content)
    return {"baseline_world_state": baseline_content, "loop_count": state["loop_count"] + 1}

def should_loop(state: AgentState):
    if state.get("loop_count", 0) < 5:
        return "prompt_for_projection_year"
    else:
        return END

workflow = StateGraph(AgentState)

workflow.add_node("create_storyline", create_storyline)
workflow.add_node("create_chapter_arcs", create_chapter_arcs)
workflow.add_node("write_first_chapter", write_first_chapter)
workflow.add_node("prompt_for_projection_year", prompt_for_projection_year)
workflow.add_node("get_projection_year_input", lambda state: None)
workflow.add_node("set_target_year", set_target_year)
workflow.add_node("generate_world_building_questions", generate_world_building_questions)
workflow.add_node("research_and_propose_scenarios", research_and_propose_scenarios)
workflow.add_node("prompt_for_scenario_selection", prompt_for_scenario_selection)
workflow.add_node("get_scenario_selection_input", lambda state: None) # Dummy node for interrupt
workflow.add_node("critique_scenario", critique_scenario)
workflow.add_node("world_projection_deep_research", world_projection_deep_research)
workflow.add_node("linguistic_evolution_research", linguistic_evolution_research)
workflow.add_node("adjust_storyline", adjust_storyline)
workflow.add_node("adjust_chapter_arcs", adjust_chapter_arcs)
workflow.add_node("rewrite_first_chapter", rewrite_first_chapter)
workflow.add_node("generate_scientific_explanations", generate_scientific_explanations)
workflow.add_node("generate_glossary", generate_glossary)
workflow.add_node("compile_baseline_world_state", compile_baseline_world_state)

workflow.add_edge(START, "create_storyline")
workflow.add_edge("create_storyline", "create_chapter_arcs")
workflow.add_edge("create_chapter_arcs", "write_first_chapter")
workflow.add_edge("write_first_chapter", "prompt_for_projection_year")
workflow.add_edge("prompt_for_projection_year", "get_projection_year_input")
workflow.add_edge("get_projection_year_input", "set_target_year")
workflow.add_edge("set_target_year", "generate_world_building_questions")
workflow.add_edge("generate_world_building_questions", "research_and_propose_scenarios")
workflow.add_edge("research_and_propose_scenarios", "prompt_for_scenario_selection")
workflow.add_edge("prompt_for_scenario_selection", "get_scenario_selection_input")
workflow.add_edge("get_scenario_selection_input", "critique_scenario")
workflow.add_edge("critique_scenario", "world_projection_deep_research")
workflow.add_edge("world_projection_deep_research", "linguistic_evolution_research")
workflow.add_edge("linguistic_evolution_research", "adjust_storyline")
workflow.add_edge("adjust_storyline", "adjust_chapter_arcs")
workflow.add_edge("adjust_chapter_arcs", "rewrite_first_chapter")
workflow.add_edge("rewrite_first_chapter", "generate_scientific_explanations")
workflow.add_edge("generate_scientific_explanations", "generate_glossary")
workflow.add_edge("generate_glossary", "compile_baseline_world_state")

workflow.add_conditional_edges("compile_baseline_world_state", should_loop, {"prompt_for_projection_year": "prompt_for_projection_year", END: END})

app = workflow.compile(interrupt_before=["get_projection_year_input", "get_scenario_selection_input"]) 