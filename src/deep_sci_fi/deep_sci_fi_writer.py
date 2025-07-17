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
    "research_model": "openai:o4-mini", # "anthropic:claude-3-7-sonnet-20250219",
    "writing_model": "anthropic:claude-opus-4-20250514",
    "general_model": "anthropic:claude-3-7-sonnet-20250219",
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
    """Uses the deep_researcher to research and propose 3 plausible scenarios."""
    if not (output_dir := state.get("output_dir")) or not (target_year := state.get("target_year")) or not (loop_count := state.get("loop_count") is not None) or not (questions := state.get("world_building_questions")) or not (storyline := state.get("storyline")) or not (chapter_arcs := state.get("chapter_arcs")) or not (first_chapter := state.get("first_chapter")):
        raise ValueError("Required state for this research step is missing.")
    
    print("--- Researching and Proposing Scenarios ---")
    
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

def prompt_for_scenario_selection(state: AgentState):
    """Adds a message to the state to ask the user to select a scenario."""
    message = AIMessage(
        content="The research is complete and three potential scenarios have been proposed. Please review the scenarios and provide the full text of the one you'd like to develop further in the `selected_scenario` field."
    )
    return {"messages": [message]}

def critique_scenario(state: AgentState):
    """Critically reflects on the selected scenario to identify second-order effects and unanswered questions."""
    if not (output_dir := state.get("output_dir")) or not (target_year := state.get("target_year")) or not (loop_count := state.get("loop_count") is not None) or not (selected_scenario := state.get("selected_scenario")) or not (world_building_scenarios := state.get("world_building_scenarios")) or not (storyline := state.get("storyline")) or not (chapter_arcs := state.get("chapter_arcs")) or not (first_chapter := state.get("first_chapter")) or not (years_in_future := state.get("years_in_future")):
        raise ValueError("Required state for critiquing scenario is missing.")
        
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
    if not (output_dir := state.get("output_dir")) or not (target_year := state.get("target_year")) or not (loop_count := state.get("loop_count") is not None) or not (selected_scenario := state.get("selected_scenario")) or not (scenario_critique := state.get("scenario_critique")):
        raise ValueError("Required state for world projection research is missing.")
    print("--- Conducting Baseline World State Research ---")
    if baseline_world_state := state.get("baseline_world_state"):
        final_query = EVOLVE_BASELINE_WORLD_STATE_PROMPT.format(baseline_world_state=baseline_world_state, selected_scenario=selected_scenario, scenario_critique=scenario_critique, target_year=target_year)
    else:
        final_query = CREATE_BASELINE_WORLD_STATE_PROMPT.format(selected_scenario=selected_scenario, scenario_critique=scenario_critique, target_year=target_year)
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