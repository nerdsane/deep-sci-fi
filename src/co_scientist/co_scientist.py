from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import START, END, StateGraph
from typing import Literal
import asyncio
import uuid
import json
import os
from datetime import datetime
from pathlib import Path

from co_scientist.configuration import CoScientistConfiguration
from co_scientist.state import (
    CoScientistState,
    CoScientistInputState,
    MetaAnalysisOutput,
    ScenarioGeneration,
    ReflectionCritique,
    TournamentComparison,
    EvolutionImprovement,
    TournamentDirectionState
)
from co_scientist.prompts import (
    INITIAL_META_ANALYSIS_PROMPT,
    INCREMENTAL_META_ANALYSIS_PROMPT,
    INITIAL_SCENARIO_GENERATION_PROMPT,
    INCREMENTAL_SCENARIO_GENERATION_PROMPT,
    DOMAIN_CRITIQUE_PROMPT,
    CROSS_SCENARIO_REFLECTION_PROMPT,
    PAIRWISE_RANKING_PROMPT,
    TOURNAMENT_SCORING_PROMPT,
    FEASIBILITY_EVOLUTION_PROMPT,
    CREATIVE_EVOLUTION_PROMPT,
    SYNTHESIS_EVOLUTION_PROMPT,
    META_REVIEW_PROMPT,
    COMPETITION_SUMMARY_PROMPT
)

# Import deep_researcher for research tasks
from open_deep_research.deep_researcher import deep_researcher
import os

# Initialize configurable models
configurable_model = init_chat_model(
    configurable_fields=("model", "max_tokens", "api_key"),
)

class CoScientistOutputManager:
    """Manages detailed output for co-scientist runs with timestamped directories."""
    
    def __init__(self, base_output_dir: str = "output"):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_dir = Path(base_output_dir) / f"{self.timestamp}_coscientist"
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.file_counter = 0
        
    def get_next_filename(self, name: str) -> str:
        """Get next numbered filename."""
        self.file_counter += 1
        return f"{self.file_counter:02d}_{name}"
    
    def save_file(self, filename: str, content: str, subdirectory: str = None):
        """Save a file to the run directory."""
        if subdirectory:
            save_dir = self.run_dir / subdirectory
            save_dir.mkdir(exist_ok=True)
        else:
            save_dir = self.run_dir
            
        filepath = save_dir / filename
        with open(filepath, "w") as f:
            f.write(content)
        print(f"Co-scientist saved: {filepath}")
        
    def save_json(self, filename: str, data: dict, subdirectory: str = None):
        """Save JSON data."""
        if subdirectory:
            save_dir = self.run_dir / subdirectory
            save_dir.mkdir(exist_ok=True)
        else:
            save_dir = self.run_dir
            
        filepath = save_dir / filename
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)
        print(f"Co-scientist saved JSON: {filepath}")

# Global output manager instance
_output_manager = None

def get_output_manager(output_dir: str = "output") -> CoScientistOutputManager:
    """Get or create the output manager for this run."""
    global _output_manager
    if _output_manager is None:
        _output_manager = CoScientistOutputManager(output_dir)
    return _output_manager

def save_co_scientist_output(filename: str, content: str, output_dir: str = "output"):
    """Save co_scientist intermediate results to markdown files."""
    manager = get_output_manager(output_dir)
    numbered_filename = manager.get_next_filename(filename)
    manager.save_file(numbered_filename, content)

def save_individual_scenarios(scenarios: list, output_dir: str = "output"):
    """Save each scenario individually with full content."""
    manager = get_output_manager(output_dir)
    
    for i, scenario in enumerate(scenarios, 1):
        scenario_id = scenario.get('scenario_id', f'scenario_{i}')
        team_id = scenario.get('team_id', 'unknown_team')
        direction = scenario.get('research_direction', 'unknown_direction')
        
        # Full scenario content
        content = f"# Scenario {scenario_id}\n\n"
        content += f"**Team ID:** {team_id}\n"
        content += f"**Research Direction:** {direction}\n"
        content += f"**Generated:** {datetime.now().isoformat()}\n\n"
        content += "## Full Scenario Content\n\n"
        content += scenario.get('scenario_content', 'No content available')
        
        # Include research query and raw results if available
        if 'research_query' in scenario:
            content += f"\n\n## Research Query\n\n{scenario['research_query']}"
            
        if 'raw_research_result' in scenario:
            content += f"\n\n## Raw Research Output\n\n{scenario['raw_research_result']}"
        
        filename = f"scenario_{i:02d}_{team_id}_{scenario_id[:8]}.md"
        manager.save_file(filename, content, "scenarios")

def save_individual_critiques(critiques: list, output_dir: str = "output"):
    """Save each critique individually."""
    manager = get_output_manager(output_dir)
    
    # Group by domain for organization
    by_domain = {}
    for critique in critiques:
        domain = critique.get('critique_domain', 'general')
        if domain not in by_domain:
            by_domain[domain] = []
        by_domain[domain].append(critique)
    
    critique_counter = 1
    for domain, domain_critiques in by_domain.items():
        for critique in domain_critiques:
            scenario_id = critique.get('target_scenario_id', 'unknown')
            severity = critique.get('severity_score', 0)
            
            content = f"# Critique {critique_counter:03d}\n\n"
            content += f"**Domain:** {domain}\n"
            content += f"**Target Scenario:** {scenario_id}\n"
            content += f"**Severity Score:** {severity}/10\n"
            content += f"**Generated:** {datetime.now().isoformat()}\n\n"
            content += "## Critique Content\n\n"
            content += critique.get('critique_content', 'No critique content available')
            
            filename = f"critique_{critique_counter:03d}_{domain}_{scenario_id[:8]}_sev{severity}.md"
            manager.save_file(filename, content, "critiques")
            critique_counter += 1

def save_individual_tournament_comparisons(all_tournament_data: list, output_dir: str = "output"):
    """Save each tournament comparison individually with full reasoning."""
    manager = get_output_manager(output_dir)
    
    comparison_counter = 1
    for tournament in all_tournament_data:
        if not tournament or isinstance(tournament, Exception):
            continue
            
        direction = tournament.get('direction', 'unknown')
        comparisons = tournament.get('all_comparisons', [])
        
        for comparison in comparisons:
            scenario1_id = comparison.get('scenario1_id', 'unknown')
            scenario2_id = comparison.get('scenario2_id', 'unknown')
            round_num = comparison.get('round', 'unknown')
            winner_id = comparison.get('winner', {}).get('scenario_id', 'unknown')
            
            content = f"# Tournament Comparison {comparison_counter:03d}\n\n"
            content += f"**Direction:** {direction}\n"
            content += f"**Round:** {round_num}\n"
            content += f"**Scenario 1 ID:** {scenario1_id}\n"
            content += f"**Scenario 2 ID:** {scenario2_id}\n"
            content += f"**Winner ID:** {winner_id}\n"
            content += f"**Timestamp:** {comparison.get('timestamp', 'unknown')}\n\n"
            
            content += "## Comparison Reasoning\n\n"
            content += comparison.get('reasoning', 'No reasoning available')
            
            filename = f"comparison_{comparison_counter:03d}_round{round_num}_{direction.replace(' ', '_')}_{scenario1_id[:8]}_vs_{scenario2_id[:8]}.md"
            manager.save_file(filename, content, "tournament_comparisons")
            comparison_counter += 1

def save_individual_evolution_attempts(evolutions: list, output_dir: str = "output"):
    """Save each evolution attempt individually with full prompts and reasoning."""
    manager = get_output_manager(output_dir)
    
    evolution_counter = 1
    for evolution in evolutions:
        if not evolution:
            continue
            
        strategy = evolution.get('strategy', 'unknown')
        original_direction = evolution.get('original_direction', 'unknown')
        original_scenario_id = evolution.get('original_scenario_id', 'unknown')
        evolution_id = evolution.get('evolution_id', 'unknown')
        
        content = f"# Evolution Attempt {evolution_counter:03d}\n\n"
        content += f"**Evolution ID:** {evolution_id}\n"
        content += f"**Strategy:** {strategy}\n"
        content += f"**Original Direction:** {original_direction}\n"
        content += f"**Original Scenario ID:** {original_scenario_id}\n"
        content += f"**Timestamp:** {evolution.get('timestamp', 'unknown')}\n\n"
        
        content += "## Original Scenario Content\n\n"
        content += evolution.get('original_scenario_content', 'No original scenario content')
        
        content += "\n\n## Evolution Prompt Used\n\n"
        content += evolution.get('evolution_prompt', 'No evolution prompt available')
        
        content += "\n\n## Evolved Content\n\n"
        content += evolution.get('evolved_content', 'No evolved content available')
        
        content += "\n\n## Critique Summary (for feasibility/synthesis)\n\n"
        content += evolution.get('critique_summary', 'No critique summary')
        
        content += "\n\n## Competing Scenarios (for creativity/synthesis)\n\n"
        content += evolution.get('competing_scenarios', 'No competing scenarios')
        
        filename = f"evolution_{evolution_counter:03d}_{strategy}_{original_scenario_id[:8]}_{evolution_id[:8]}.md"
        manager.save_file(filename, content, "evolution_attempts")
        evolution_counter += 1

def save_tournament_brackets(all_tournament_data: list, output_dir: str = "output"):
    """Save detailed tournament bracket progression for each direction."""
    manager = get_output_manager(output_dir)
    
    for i, tournament in enumerate(all_tournament_data, 1):
        if not tournament or isinstance(tournament, Exception):
            continue
            
        direction = tournament.get('direction', 'unknown')
        rounds = tournament.get('round_progression', [])
        winner = tournament.get('winner', {})
        
        content = f"# Tournament Bracket {i}: {direction}\n\n"
        content += f"**Direction:** {direction}\n"
        content += f"**Total Rounds:** {len(rounds)}\n"
        content += f"**Final Winner:** {winner.get('team_id', 'unknown')} ({winner.get('scenario_id', 'unknown')})\n\n"
        
        content += "## Bracket Progression\n\n"
        for round_num, round_data in enumerate(rounds, 1):
            content += f"### Round {round_num}\n\n"
            participants = round_data.get('participants', [])
            winners = round_data.get('winners', [])
            
            content += f"**Participants:** {len(participants)}\n"
            for participant in participants:
                content += f"- {participant.get('team_id', 'unknown')} ({participant.get('scenario_id', 'unknown')[:8]})\n"
            
            content += f"\n**Winners advancing:** {len(winners)}\n"
            for winner in winners:
                content += f"- {winner.get('team_id', 'unknown')} ({winner.get('scenario_id', 'unknown')[:8]})\n"
            content += "\n"
        
        content += "## Final Winner Details\n\n"
        content += f"**Team ID:** {winner.get('team_id', 'unknown')}\n"
        content += f"**Scenario ID:** {winner.get('scenario_id', 'unknown')}\n"
        content += f"**Research Direction:** {winner.get('research_direction', 'unknown')}\n\n"
        content += "**Winning Scenario Content:**\n\n"
        content += winner.get('scenario_content', 'No scenario content available')
        
        filename = f"bracket_{i:02d}_{direction.replace(' ', '_')}.md"
        manager.save_file(filename, content, "tournament_brackets")

def save_evolution_tournament_details(evolution_tournaments: list, output_dir: str = "output"):
    """Save detailed evolution tournament comparisons."""
    manager = get_output_manager(output_dir)
    
    tournament_counter = 1
    for tournament in evolution_tournaments:
        if not tournament:
            continue
            
        direction = tournament.get('direction', 'unknown')
        original_winner = tournament.get('original_winner', {})
        final_winner = tournament.get('final_winner', {})
        all_comparisons = tournament.get('comparisons', [])
        
        content = f"# Evolution Tournament {tournament_counter:03d}: {direction}\n\n"
        content += f"**Direction:** {direction}\n"
        content += f"**Original Winner:** {original_winner.get('team_id', 'unknown')} ({original_winner.get('scenario_id', 'unknown')[:8]})\n"
        content += f"**Final Winner:** {final_winner.get('team_id', 'unknown')} ({final_winner.get('scenario_id', 'unknown')[:8]})\n"
        content += f"**Total Comparisons:** {len(all_comparisons)}\n\n"
        
        content += "## Evolution Tournament Comparisons\n\n"
        for i, comparison in enumerate(all_comparisons, 1):
            content += f"### Comparison {i}: {comparison.get('type', 'unknown')}\n\n"
            content += f"**Participant 1:** {comparison.get('scenario1_type', 'unknown')} - {comparison.get('scenario1_id', 'unknown')[:8]}\n"
            content += f"**Participant 2:** {comparison.get('scenario2_type', 'unknown')} - {comparison.get('scenario2_id', 'unknown')[:8]}\n"
            content += f"**Winner:** {comparison.get('winner_type', 'unknown')} - {comparison.get('winner_id', 'unknown')[:8]}\n\n"
            
            content += "**Reasoning:**\n"
            content += comparison.get('reasoning', 'No reasoning available')
            content += "\n\n---\n\n"
        
        content += "## Final Winner Details\n\n"
        content += f"**Type:** {final_winner.get('type', 'unknown')} (original vs evolved)\n"
        content += f"**Team ID:** {final_winner.get('team_id', 'unknown')}\n"
        content += f"**Scenario ID:** {final_winner.get('scenario_id', 'unknown')}\n\n"
        content += "**Content:**\n\n"
        content += final_winner.get('scenario_content', 'No content available')
        
        filename = f"evolution_tournament_{tournament_counter:03d}_{direction.replace(' ', '_')}.md"
        manager.save_file(filename, content, "evolution_tournaments")
        tournament_counter += 1

def save_tournament_details(tournaments: list, output_dir: str = "output"):
    """Save detailed tournament results."""
    manager = get_output_manager(output_dir)
    
    for i, tournament in enumerate(tournaments, 1):
        direction = tournament.get('direction', 'unknown')
        winner = tournament.get('winner', {})
        rounds = tournament.get('total_rounds', 0)
        
        content = f"# Tournament {i}: {direction}\n\n"
        content += f"**Direction:** {direction}\n"
        content += f"**Total Rounds:** {rounds}\n"
        content += f"**Winner Team:** {winner.get('team_id', 'unknown')}\n"
        content += f"**Winner Scenario ID:** {winner.get('scenario_id', 'unknown')}\n\n"
        
        # Include all rounds if available
        if 'rounds' in tournament:
            content += "## Tournament Rounds\n\n"
            for round_num, round_data in enumerate(tournament['rounds'], 1):
                content += f"### Round {round_num}\n\n"
                content += f"**Participants:** {len(round_data.get('participants', []))}\n"
                content += f"**Winner:** {round_data.get('winner', {}).get('team_id', 'unknown')}\n\n"
        
        content += "## Winning Scenario\n\n"
        content += winner.get('scenario_content', 'No winning scenario content')
        
        filename = f"tournament_{i:02d}_{direction.replace(' ', '_')}.md"
        manager.save_file(filename, content, "tournaments")

def save_evolution_details(evolutions: list, output_dir: str = "output"):
    """Save detailed evolution results."""
    manager = get_output_manager(output_dir)
    
    evolution_counter = 1
    for evolution in evolutions:
        strategy = evolution.get('strategy', 'unknown')
        original_direction = evolution.get('original_direction', 'unknown')
        
        content = f"# Evolution {evolution_counter:03d}\n\n"
        content += f"**Strategy:** {strategy}\n"
        content += f"**Original Direction:** {original_direction}\n"
        content += f"**Generated:** {datetime.now().isoformat()}\n\n"
        
        content += "## Original Scenario\n\n"
        content += evolution.get('original_scenario', 'No original scenario')
        
        content += "\n\n## Evolution Prompt\n\n"
        content += evolution.get('evolution_prompt', 'No evolution prompt')
        
        content += "\n\n## Evolved Content\n\n"
        content += evolution.get('evolved_content', 'No evolved content')
        
        filename = f"evolution_{evolution_counter:03d}_{strategy}_{original_direction.replace(' ', '_')}.md"
        manager.save_file(filename, content, "evolutions")
        evolution_counter += 1

async def meta_analysis_phase(state: CoScientistInputState, config: RunnableConfig) -> dict:
    """Meta-analysis to identify distinct research directions for competition."""
    
    configuration = CoScientistConfiguration.from_runnable_config(config)
    
    # Configure model for meta-analysis
    model = configurable_model.with_config(
        configurable={
            "model": configuration.research_model,
            "max_tokens": 4096,
        }
    )
    
    # Choose appropriate meta-analysis prompt based on whether we have baseline state
    if state.get("baseline_world_state") and state.get("years_in_future"):
        # Incremental analysis - building on existing world state
        meta_prompt = INCREMENTAL_META_ANALYSIS_PROMPT.format(
            storyline=state.get("storyline", ""),
            research_context=state["research_context"],
            baseline_world_state=state["baseline_world_state"],
            years_in_future=state["years_in_future"]
        )
    else:
        # Initial analysis - projecting to target year from present
        meta_prompt = INITIAL_META_ANALYSIS_PROMPT.format(
            storyline=state.get("storyline", ""),
            research_context=state["research_context"],
            target_year=state.get("target_year", "future")
        )
    
    # Generate research directions
    response = await model.ainvoke([HumanMessage(content=meta_prompt)])
    
    # Parse response to extract research directions
    research_directions = parse_research_directions(response.content)
    
    # Debug logging
    print(f"Meta-analysis complete. Parsed {len(research_directions)} research directions:")
    for i, direction in enumerate(research_directions):
        print(f"  Direction {i+1}: {direction}")
    
    # Save meta-analysis results
    if configuration.save_intermediate_results:
        save_co_scientist_output("meta_analysis.md", response.content, configuration.output_dir)
    
    return {
        "research_directions": research_directions,
        "meta_analysis_reasoning": response.content,
        "generation_complete": False,
        "reflection_complete": False,
        "tournament_complete": False,
        "evolution_complete": False,
        "evolution_tournament_complete": False,
        "scenario_population": [],
        "reflection_critiques": [],
        "tournament_rounds": [],
        "tournament_winners": [],
        "evolved_scenarios": [],
        "evolution_tournament_results": [],
        "final_representatives": [],
        "top_scenarios": [],
        "competition_summary": ""
    }

async def parallel_scenario_generation(state: CoScientistState, config: RunnableConfig) -> dict:
    """Generate scenarios in parallel for each research direction."""
    
    configuration = CoScientistConfiguration.from_runnable_config(config)
    
    # Create tasks for parallel generation
    generation_tasks = []
    
    print(f"Starting scenario generation: {len(state['research_directions'])} directions, {configuration.scenarios_per_direction} scenarios per direction")
    
    for direction_idx, direction in enumerate(state["research_directions"]):
        print(f"Processing direction {direction_idx}: {direction.get('name', 'Unknown')}")
        # Create multiple research teams per direction
        for team_idx in range(configuration.scenarios_per_direction):
            team_id = f"direction_{direction_idx}_team_{team_idx}"
            
            task = generate_single_scenario(
                direction=direction,
                team_id=team_id,
                state=state,
                config=config
            )
            generation_tasks.append(task)
    
    print(f"Created {len(generation_tasks)} scenario generation tasks")
    
    # Execute all scenario generation in parallel
    generated_scenarios = await asyncio.gather(*generation_tasks, return_exceptions=True)
    
    # Filter out exceptions and collect valid scenarios
    valid_scenarios = []
    failed_scenarios = []
    
    for i, scenario in enumerate(generated_scenarios):
        if isinstance(scenario, Exception):
            failed_scenarios.append(f"Task {i}: {str(scenario)}")
            print(f"Scenario generation failed for task {i}: {scenario}")
        else:
            valid_scenarios.append(scenario)
    
    # Log results
    print(f"Scenario generation complete: {len(valid_scenarios)} successful, {len(failed_scenarios)} failed")
    if failed_scenarios:
        print("Failed scenarios:", failed_scenarios)
    
    # Save scenario generation results
    if configuration.save_intermediate_results:
        # Save individual scenarios with full content
        save_individual_scenarios(valid_scenarios, configuration.output_dir)
        
        # Save raw JSON data for debugging
        manager = get_output_manager(configuration.output_dir)
        manager.save_json("scenarios_raw_data.json", {"scenarios": valid_scenarios}, "raw_data")
        
        # Save summary
        scenario_content = format_scenario_population(valid_scenarios)
        save_co_scientist_output("scenario_population_summary.md", scenario_content, configuration.output_dir)
    
    return {
        "scenario_population": valid_scenarios,
        "generation_complete": True
    }

async def generate_single_scenario(direction: dict, team_id: str, state: CoScientistState, config: RunnableConfig) -> dict:
    """Generate a single scenario using deep research."""
    
    print(f"Generating scenario for {team_id} in direction: {direction.get('name', 'Unknown')}")
    
    # Choose appropriate scenario generation prompt based on whether we have baseline state
    if state.get("baseline_world_state") and state.get("years_in_future"):
        # Incremental scenario generation - building on existing world state
        research_query = INCREMENTAL_SCENARIO_GENERATION_PROMPT.format(
            research_direction=direction.get("name", ""),
            core_assumption=direction.get("assumption", ""),
            team_id=team_id,
            research_context=state["research_context"],
            storyline=state.get("storyline", ""),
            baseline_world_state=state["baseline_world_state"],
            years_in_future=state["years_in_future"]
        )
    else:
        # Initial scenario generation - projecting to target year from present
        research_query = INITIAL_SCENARIO_GENERATION_PROMPT.format(
            research_direction=direction.get("name", ""),
            core_assumption=direction.get("assumption", ""),
            team_id=team_id,
            research_context=state["research_context"],
            storyline=state.get("storyline", ""),
            target_year=state.get("target_year", "future")
        )
    
    # Use deep_researcher for scenario generation
    research_config = config.copy()
    co_config = CoScientistConfiguration.from_runnable_config(config)
    research_config["configurable"].update({
        "research_model": co_config.research_model,
        "research_model_max_tokens": 8000,  # Stay under Claude's 8192 limit
        "summarization_model": co_config.general_model,
        "compression_model": co_config.research_model,
        "compression_model_max_tokens": 8000,
        "final_report_model": co_config.research_model,
        "final_report_model_max_tokens": 8000,
        "allow_clarification": False,
        "search_api": co_config.search_api
    })
    
    try:
        research_result = await deep_researcher.ainvoke(
            {"messages": [HumanMessage(content=research_query)]},
            research_config
        )
        print(f"Successfully generated scenario for {team_id}, content length: {len(research_result.get('final_report', ''))}")
    except Exception as e:
        print(f"Failed to generate scenario for {team_id}: {e}")
        raise e
    
    return {
        "scenario_id": str(uuid.uuid4()),
        "team_id": team_id,
        "research_direction": direction.get("name", ""),
        "core_assumption": direction.get("assumption", ""),
        "scenario_content": research_result.get("final_report", ""),
        "research_query": research_query,
        "raw_research_result": str(research_result),
        "generation_timestamp": datetime.now().isoformat(),
        "quality_score": None,
        "critiques": []
    }

async def reflection_phase(state: CoScientistState, config: RunnableConfig) -> dict:
    """Conduct parallel reflection/critique of all scenarios."""
    
    configuration = CoScientistConfiguration.from_runnable_config(config)
    
    # Check if we have any scenarios to critique
    scenario_population = state.get("scenario_population", [])
    if not scenario_population:
        print("No scenarios available for reflection - returning empty results")
        return {
            "reflection_critiques": [],
            "reflection_complete": True
        }
    
    # Create reflection tasks
    reflection_tasks = []
    
    for scenario in scenario_population:
        for domain in configuration.reflection_domains:
            task = generate_domain_critique(
                scenario=scenario,
                domain=domain,
                config=config
            )
            reflection_tasks.append(task)
    
    # Execute all reflections in parallel
    reflection_results = await asyncio.gather(*reflection_tasks, return_exceptions=True)
    
    # Filter valid critiques
    valid_critiques = [
        critique for critique in reflection_results 
        if not isinstance(critique, Exception)
    ]
    
    # Save reflection results
    if configuration.save_intermediate_results:
        # Save individual critiques with full content
        save_individual_critiques(valid_critiques, configuration.output_dir)
        
        # Save raw JSON data for debugging
        manager = get_output_manager(configuration.output_dir)
        manager.save_json("critiques_raw_data.json", {"critiques": valid_critiques}, "raw_data")
        
        # Save summary
        critique_content = format_reflection_critiques(valid_critiques)
        save_co_scientist_output("reflection_critiques_summary.md", critique_content, configuration.output_dir)
    
    return {
        "reflection_critiques": valid_critiques,
        "reflection_complete": True
    }

async def generate_domain_critique(scenario: dict, domain: str, config: RunnableConfig) -> dict:
    """Generate critique from a domain expert."""
    
    configuration = CoScientistConfiguration.from_runnable_config(config)
    
    model = configurable_model.with_config(
        configurable={
            "model": configuration.general_model,
            "max_tokens": 2048,
        }
    )
    
    # Get scenario information with defaults for missing fields
    scenario_id = scenario.get("scenario_id", f"missing_id_{uuid.uuid4().hex[:8]}")
    research_direction = scenario.get("research_direction", "Unknown Direction")
    scenario_content = scenario.get("scenario_content", "No scenario content available")
    
    critique_prompt = DOMAIN_CRITIQUE_PROMPT.format(
        critique_domain=domain,
        scenario_id=scenario_id,
        research_direction=research_direction,
        scenario_content=scenario_content
    )
    
    response = await model.ainvoke([HumanMessage(content=critique_prompt)])
    
    # Parse severity score from response
    severity_score = extract_severity_score(response.content)
    
    return {
        "critique_id": str(uuid.uuid4()),
        "target_scenario_id": scenario_id,
        "critique_domain": domain,
        "critique_content": response.content,
        "severity_score": severity_score,
        "timestamp": datetime.now().isoformat()
    }

async def tournament_phase(state: CoScientistState, config: RunnableConfig) -> dict:
    """Run tournament brackets for each research direction."""
    
    configuration = CoScientistConfiguration.from_runnable_config(config)
    
    # Check if we have any scenarios to run tournaments on
    scenario_population = state.get("scenario_population", [])
    if not scenario_population:
        print("No scenarios available for tournaments - returning empty results")
        return {
            "tournament_winners": [],
            "tournament_complete": True
        }
    
    # Group scenarios by research direction
    direction_groups = {}
    for scenario in scenario_population:
        direction = scenario["research_direction"]
        if direction not in direction_groups:
            direction_groups[direction] = []
        direction_groups[direction].append(scenario)
    
    # Run parallel tournaments for each direction
    tournament_tasks = []
    for direction, scenarios in direction_groups.items():
        task = run_direction_tournament(direction, scenarios, config)
        tournament_tasks.append(task)
    
    tournament_results = await asyncio.gather(*tournament_tasks, return_exceptions=True)
    
    # Collect winners from each direction
    direction_winners = [
        result for result in tournament_results 
        if not isinstance(result, Exception)
    ]
    
    # Save tournament results
    if configuration.save_intermediate_results:
        # Save individual tournament comparisons with full reasoning
        save_individual_tournament_comparisons(direction_winners, configuration.output_dir)
        
        # Save tournament bracket progressions
        save_tournament_brackets(direction_winners, configuration.output_dir)
        
        # Save individual tournament details (existing function)
        save_tournament_details(direction_winners, configuration.output_dir)
        
        # Save raw JSON data for debugging
        manager = get_output_manager(configuration.output_dir)
        manager.save_json("tournaments_raw_data.json", {"tournaments": direction_winners}, "raw_data")
        
        # Save summary
        tournament_content = format_tournament_results(direction_winners, tournament_results)
        save_co_scientist_output("tournament_results_summary.md", tournament_content, configuration.output_dir)
    
    return {
        "tournament_rounds": tournament_results,
        "tournament_winners": direction_winners,
        "tournament_complete": True
    }

async def run_direction_tournament(direction: str, scenarios: list, config: RunnableConfig) -> dict:
    """Run tournament bracket for a single direction."""
    
    if len(scenarios) < 2:
        winner = scenarios[0] if scenarios else None
        return {
            "direction": direction,
            "winner": winner,
            "total_rounds": 0,
            "all_comparisons": [],
            "round_progression": []
        }
    
    current_round = scenarios.copy()
    round_number = 1
    all_comparisons = []
    round_progression = []
    
    while len(current_round) > 1:
        next_round = []
        comparison_tasks = []
        round_participants = current_round.copy()
        
        # Create pairwise comparisons for this round
        for i in range(0, len(current_round), 2):
            if i + 1 < len(current_round):
                task = pairwise_comparison(
                    current_round[i], 
                    current_round[i + 1], 
                    round_number,
                    config
                )
                comparison_tasks.append(task)
            else:
                # Odd number of scenarios, this one advances automatically
                next_round.append(current_round[i])
        
        # Execute all comparisons for this round in parallel
        round_results = await asyncio.gather(*comparison_tasks, return_exceptions=True)
        
        # Collect winners and store comparison data
        round_winners = []
        for result in round_results:
            if not isinstance(result, Exception) and result:
                next_round.append(result["winner"])
                round_winners.append(result["winner"])
                all_comparisons.append(result)
        
        # Store round progression
        round_progression.append({
            "round": round_number,
            "participants": round_participants,
            "winners": round_winners,
            "comparisons_count": len([r for r in round_results if not isinstance(r, Exception)])
        })
        
        current_round = next_round
        round_number += 1
    
    return {
        "direction": direction,
        "winner": current_round[0] if current_round else None,
        "total_rounds": round_number - 1,
        "all_comparisons": all_comparisons,
        "round_progression": round_progression
    }

async def pairwise_comparison(scenario1: dict, scenario2: dict, round_number: int, config: RunnableConfig) -> dict:
    """Compare two scenarios head-to-head."""
    
    configuration = CoScientistConfiguration.from_runnable_config(config)
    
    model = configurable_model.with_config(
        configurable={
            "model": configuration.general_model,
            "max_tokens": 3072,
        }
    )
    
    comparison_prompt = PAIRWISE_RANKING_PROMPT.format(
        scenario1_content=scenario1["scenario_content"],
        direction1=scenario1["research_direction"],
        scenario2_content=scenario2["scenario_content"],
        direction2=scenario2["research_direction"]
    )
    
    response = await model.ainvoke([HumanMessage(content=comparison_prompt)])
    
    # Determine winner based on response
    winner = scenario1 if "better scenario: 1" in response.content else scenario2
    
    return {
        "round": round_number,
        "scenario1_id": scenario1["scenario_id"],
        "scenario2_id": scenario2["scenario_id"],
        "winner": winner,
        "reasoning": response.content,
        "timestamp": datetime.now().isoformat()
    }

async def evolution_phase(state: CoScientistState, config: RunnableConfig) -> dict:
    """Evolve winning scenarios using multiple enhancement strategies."""
    
    configuration = CoScientistConfiguration.from_runnable_config(config)
    
    # Check if we have any tournament winners to evolve
    tournament_winners = state.get("tournament_winners", [])
    if not tournament_winners:
        print("No tournament winners available for evolution - returning empty results")
        return {
            "evolved_scenarios": [],
            "evolution_complete": True
        }
    
    # Collect all winning scenarios
    winners = [result["winner"] for result in tournament_winners if result.get("winner")]
    
    # Create evolution tasks
    evolution_tasks = []
    
    for winner in winners:
        for strategy in configuration.evolution_strategies:
            task = evolve_scenario(winner, strategy, state, config)
            evolution_tasks.append(task)
    
    # Execute all evolution in parallel
    evolution_results = await asyncio.gather(*evolution_tasks, return_exceptions=True)
    
    # Filter valid evolution results
    evolved_scenarios = [
        result for result in evolution_results 
        if not isinstance(result, Exception)
    ]
    
    # Save evolution results
    if configuration.save_intermediate_results:
        # Save individual evolution attempts with full prompts and reasoning
        save_individual_evolution_attempts(evolved_scenarios, configuration.output_dir)
        
        # Save individual evolution details (existing function)
        save_evolution_details(evolved_scenarios, configuration.output_dir)
        
        # Save raw JSON data for debugging
        manager = get_output_manager(configuration.output_dir)
        manager.save_json("evolutions_raw_data.json", {"evolutions": evolved_scenarios}, "raw_data")
        
        # Save summary
        evolution_content = format_evolution_results(evolved_scenarios)
        save_co_scientist_output("evolution_results_summary.md", evolution_content, configuration.output_dir)
    
    return {
        "evolved_scenarios": evolved_scenarios,
        "evolution_complete": True
    }

async def run_evolution_tournament_with_metadata(direction: str, original_winner: dict, competitors: list, config: RunnableConfig) -> dict:
    """Run evolution tournament and add metadata about original vs evolved scenarios."""
    
    # Run the tournament
    tournament_result = await run_direction_tournament(f"Evolution_{direction}", competitors, config)
    
    if isinstance(tournament_result, Exception) or not tournament_result:
        return {
            "direction": direction,
            "original_winner": original_winner,
            "final_winner": None,
            "comparisons": [],
            "tournament_failed": True
        }
    
    # Extract comparison data and add original vs evolved metadata
    enhanced_comparisons = []
    for comparison in tournament_result.get("all_comparisons", []):
        # Determine if each scenario is original or evolved
        scenario1_id = comparison.get("scenario1_id")
        scenario2_id = comparison.get("scenario2_id")
        winner_id = comparison.get("winner", {}).get("scenario_id")
        
        scenario1_type = "original" if scenario1_id == original_winner.get("scenario_id") else "evolved"
        scenario2_type = "original" if scenario2_id == original_winner.get("scenario_id") else "evolved"
        winner_type = "original" if winner_id == original_winner.get("scenario_id") else "evolved"
        
        enhanced_comparison = {
            "type": f"{scenario1_type}_vs_{scenario2_type}",
            "scenario1_id": scenario1_id,
            "scenario1_type": scenario1_type,
            "scenario2_id": scenario2_id,
            "scenario2_type": scenario2_type,
            "winner_id": winner_id,
            "winner_type": winner_type,
            "reasoning": comparison.get("reasoning", ""),
            "round": comparison.get("round", "unknown"),
            "timestamp": comparison.get("timestamp", "")
        }
        enhanced_comparisons.append(enhanced_comparison)
    
    # Determine final winner type
    final_winner = tournament_result.get("winner", {})
    final_winner_type = "original" if final_winner.get("scenario_id") == original_winner.get("scenario_id") else "evolved"
    
    # Add type metadata to final winner
    enhanced_final_winner = final_winner.copy()
    enhanced_final_winner["type"] = final_winner_type
    
    return {
        "direction": direction,
        "original_winner": original_winner,
        "final_winner": enhanced_final_winner,
        "comparisons": enhanced_comparisons,
        "total_rounds": tournament_result.get("total_rounds", 0),
        "round_progression": tournament_result.get("round_progression", []),
        "tournament_successful": True
    }

async def evolution_tournament_phase(state: CoScientistState, config: RunnableConfig) -> dict:
    """Run tournament between original winners and their evolved variants within each direction."""
    
    configuration = CoScientistConfiguration.from_runnable_config(config)
    
    # Check if we have evolved scenarios and tournament winners
    evolved_scenarios = state.get("evolved_scenarios", [])
    tournament_winners = state.get("tournament_winners", [])
    
    if not evolved_scenarios or not tournament_winners:
        print("No evolved scenarios or tournament winners available for evolution tournaments - returning empty results")
        return {
            "final_representatives": [],
            "evolution_tournament_complete": True
        }
    
    # Group evolved scenarios by original direction
    evolved_by_direction = {}
    for evolution in evolved_scenarios:
        direction = evolution.get("original_direction", "Unknown")
        if direction not in evolved_by_direction:
            evolved_by_direction[direction] = []
        evolved_by_direction[direction].append(evolution)
    
    # Get original winners
    original_winners = [result["winner"] for result in tournament_winners if result.get("winner")]
    
    # Run evolution tournament for each direction
    evolution_tournament_tasks = []
    
    for original_winner in original_winners:
        direction = original_winner.get("research_direction", "Unknown")
        
        # Get evolved variants for this direction
        evolved_variants = evolved_by_direction.get(direction, [])
        
        # Convert evolved scenarios back to scenario format for tournament
        competitors = [original_winner]  # Start with original winner
        
        for evolved in evolved_variants:
            # Create scenario format from evolution
            evolved_scenario = {
                "scenario_id": evolved.get("evolution_id", str(uuid.uuid4())),
                "team_id": f"evolved_{evolved.get('strategy', 'unknown')}",
                "research_direction": direction,
                "core_assumption": original_winner.get("core_assumption", ""),
                "scenario_content": evolved.get("evolved_content", ""),
                "generation_timestamp": evolved.get("timestamp", ""),
                "quality_score": None,
                "critiques": [],
                "evolution_type": evolved.get("strategy", "unknown")
            }
            competitors.append(evolved_scenario)
        
        # Run tournament for this direction (original + evolved)
        task = run_evolution_tournament_with_metadata(direction, original_winner, competitors, config)
        evolution_tournament_tasks.append(task)
    
    # Execute all evolution tournaments in parallel
    evolution_results = await asyncio.gather(*evolution_tournament_tasks, return_exceptions=True)
    
    # Collect final representatives
    final_representatives = [
        result for result in evolution_results 
        if not isinstance(result, Exception)
    ]
    
    # Save evolution tournament results
    if configuration.save_intermediate_results:
        # Save detailed evolution tournament comparisons
        save_evolution_tournament_details(evolution_results, configuration.output_dir)
        
        # Save raw JSON data for debugging
        manager = get_output_manager(configuration.output_dir)
        manager.save_json("evolution_tournaments_raw_data.json", {"evolution_tournaments": evolution_results}, "raw_data")
        
        # Save summary
        tournament_content = format_evolution_tournament_results(final_representatives)
        save_co_scientist_output("evolution_tournaments_summary.md", tournament_content, configuration.output_dir)
    
    return {
        "evolution_tournament_results": evolution_results,
        "final_representatives": final_representatives,
        "evolution_tournament_complete": True
    }

async def evolve_scenario(scenario: dict, strategy: str, state: CoScientistState, config: RunnableConfig) -> dict:
    """Evolve a single scenario using specified strategy."""
    
    configuration = CoScientistConfiguration.from_runnable_config(config)
    
    model = configurable_model.with_config(
        configurable={
            "model": configuration.research_model,
            "max_tokens": 8000,
        }
    )
    
    # Select appropriate evolution prompt
    if strategy == "feasibility":
        prompt_template = FEASIBILITY_EVOLUTION_PROMPT
        # Collect critiques for this scenario
        critique_summary = get_critique_summary(scenario["scenario_id"], state["reflection_critiques"])
    elif strategy == "creativity":
        prompt_template = CREATIVE_EVOLUTION_PROMPT
        # Get competing scenarios for inspiration
        competing_scenarios = get_competing_scenarios(scenario, state["scenario_population"])
    elif strategy == "synthesis":
        prompt_template = SYNTHESIS_EVOLUTION_PROMPT
        competing_scenarios = get_competing_scenarios(scenario, state["scenario_population"])
        critique_summary = get_critique_summary(scenario["scenario_id"], state["reflection_critiques"])
    else:
        # Default to feasibility evolution
        prompt_template = FEASIBILITY_EVOLUTION_PROMPT
        critique_summary = get_critique_summary(scenario["scenario_id"], state["reflection_critiques"])
    
    # Format prompt based on strategy
    if strategy == "feasibility":
        evolution_prompt = prompt_template.format(
            scenario_content=scenario["scenario_content"],
            research_direction=scenario["research_direction"],
            critique_summary=critique_summary
        )
        competing_scenarios_used = ""
    else:
        evolution_prompt = prompt_template.format(
            scenario_content=scenario["scenario_content"],
            research_direction=scenario["research_direction"],
            competing_scenarios=competing_scenarios[:2000],  # Limit length
            critique_summary=critique_summary if strategy == "synthesis" else ""
        )
        competing_scenarios_used = competing_scenarios[:2000]
    
    response = await model.ainvoke([HumanMessage(content=evolution_prompt)])
    
    return {
        "evolution_id": str(uuid.uuid4()),
        "original_scenario_id": scenario["scenario_id"],
        "original_scenario_content": scenario["scenario_content"],
        "evolution_prompt": evolution_prompt,
        "strategy": strategy,
        "evolved_content": response.content,
        "original_direction": scenario["research_direction"],
        "critique_summary": critique_summary if strategy in ["feasibility", "synthesis"] else "",
        "competing_scenarios": competing_scenarios_used,
        "timestamp": datetime.now().isoformat()
    }

async def final_meta_review_phase(state: CoScientistState, config: RunnableConfig) -> dict:
    """Comprehensive meta-review and synthesis of competition results."""
    
    configuration = CoScientistConfiguration.from_runnable_config(config)
    
    # Check if we have any final representatives to review
    final_representatives = state.get("final_representatives", [])
    if not final_representatives:
        print("No final representatives available for meta-review - generating summary with available data")
        # Still generate a summary even if no final representatives exist
        competition_summary = "Competition completed but no final representatives were generated due to scenario generation failures."
        return {
            "top_scenarios": [],
            "competition_summary": competition_summary
        }
    
    model = configurable_model.with_config(
        configurable={
            "model": configuration.research_model,
            "max_tokens": 4096,
        }
    )
    
    # Prepare comprehensive competition data for synthesis
    competition_data = {
        "research_directions": state.get("research_directions", []),
        "total_scenarios": len(state.get("scenario_population", [])),
        "critique_count": len(state.get("reflection_critiques", [])),
        "tournament_rounds": len(state.get("tournament_rounds", [])),
        "evolution_count": len(state.get("evolved_scenarios", [])),
    }
    
    meta_review_prompt = COMPETITION_SUMMARY_PROMPT.format(
        research_directions=format_research_directions(state.get("research_directions", [])),
        total_scenarios=competition_data["total_scenarios"],
        critique_count=competition_data["critique_count"],
        tournament_rounds=competition_data["tournament_rounds"],
        evolution_count=competition_data["evolution_count"]
    )
    
    response = await model.ainvoke([HumanMessage(content=meta_review_prompt)])
    competition_summary = response.content
    
    # Format final representatives as top scenarios (they're already the best)
    top_scenarios = []
    for i, rep in enumerate(final_representatives[:3]):
        winner = rep.get("winner", {})
        if winner:
            top_scenarios.append({
                "scenario_id": winner.get("scenario_id", f"final_rep_{i}"),
                "research_direction": winner.get("research_direction", "Unknown"),
                "scenario_content": winner.get("scenario_content", ""),
                "competition_rank": i + 1,
                "selection_reasoning": f"Winner of evolution tournament in {winner.get('research_direction', 'unknown')} direction",
                "evolution_type": winner.get("evolution_type", "original")
            })
    
    # Save meta-review results
    if configuration.save_intermediate_results:
        save_co_scientist_output("meta_review.md", response.content, configuration.output_dir)
        
        # Also save the complete competition summary
        full_summary = format_complete_summary(state, top_scenarios, competition_summary)
        save_co_scientist_output("complete_summary.md", full_summary, configuration.output_dir)
    
    return {
        "top_scenarios": top_scenarios,
        "competition_summary": competition_summary
    }

# Helper functions
def parse_research_directions(content: str) -> list:
    """Parse research directions from meta-analysis output."""
    directions = []
    lines = content.split('\n')
    
    current_direction = {}
    for line in lines:
        line = line.strip()
        if line.startswith("Direction"):
            if current_direction:
                directions.append(current_direction)
            current_direction = {"name": line.split(":")[1].strip() if ":" in line else line}
        elif line.startswith("Core Assumption:"):
            current_direction["assumption"] = line.split(":", 1)[1].strip() if ":" in line else ""
        elif line.startswith("Focus:"):
            current_direction["focus"] = line.split(":", 1)[1].strip() if ":" in line else ""
    
    if current_direction:
        directions.append(current_direction)
    
    return directions

def extract_severity_score(content: str) -> int:
    """Extract severity score from critique content."""
    import re
    # Look for patterns like "severity score: 7" or "score: 7/10"
    patterns = [
        r"severity score[:\s]+(\d+)",
        r"score[:\s]+(\d+)",
        r"(\d+)/10",
        r"severity[:\s]+(\d+)"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, content.lower())
        if match:
            return min(int(match.group(1)), 10)
    
    return 5  # Default moderate severity

def get_critique_summary(scenario_id: str, critiques: list) -> str:
    """Get summary of critiques for a specific scenario."""
    relevant_critiques = [c for c in critiques if c.get("scenario_id") == scenario_id]
    
    if not relevant_critiques:
        return "No specific critiques identified."
    
    summary = "Key critiques identified:\n"
    for critique in relevant_critiques:
        domain = critique.get("critique_domain", "Unknown")
        severity = critique.get("severity_score", 5)
        summary += f"- {domain} (severity {severity}/10): "
        # Extract key points from critique content
        content = critique.get("critique_content", "")
        summary += content[:200] + "...\n" if len(content) > 200 else content + "\n"
    
    return summary

def get_competing_scenarios(target_scenario: dict, all_scenarios: list) -> str:
    """Get competing scenarios for inspiration."""
    competing = [s for s in all_scenarios if s["scenario_id"] != target_scenario["scenario_id"]]
    
    if not competing:
        return "No competing scenarios available."
    
    # Take up to 3 competing scenarios
    summary = "Competing approaches for inspiration:\n"
    for i, scenario in enumerate(competing[:3]):
        summary += f"\nApproach {i+1} ({scenario['research_direction']}):\n"
        content = scenario.get("scenario_content", "")
        summary += content[:500] + "...\n" if len(content) > 500 else content + "\n"
    
    return summary

def generate_competition_summary(state: CoScientistState) -> str:
    """Generate summary of the competition process."""
    return f"""
    Research Directions: {len(state.get('research_directions', []))}
    Total Scenarios Generated: {len(state.get('scenario_population', []))}
    Reflection Critiques: {len(state.get('reflection_critiques', []))}
    Tournament Winners: {len(state.get('tournament_winners', []))}
    Evolution Results: {len(state.get('evolved_scenarios', []))}
    """

def format_evolved_scenarios(evolved_scenarios: list) -> str:
    """Format evolved scenarios for presentation."""
    if not evolved_scenarios:
        return "No evolved scenarios available."
    
    summary = "Evolution results:\n"
    for scenario in evolved_scenarios[:5]:  # Limit to top 5
        strategy = scenario.get("strategy", "unknown")
        direction = scenario.get("original_direction", "unknown")
        summary += f"- {strategy.title()} evolution of {direction} approach\n"
    
    return summary

def parse_top_scenarios(content: str, state: CoScientistState) -> list:
    """Parse top 3 scenarios from meta-review output."""
    # This is a simplified parser - in practice, you'd want more robust parsing
    # For now, return the tournament winners as top scenarios
    
    winners = state.get("tournament_winners", [])
    top_scenarios = []
    
    for i, winner_data in enumerate(winners[:3]):
        winner = winner_data.get("winner", {})
        if winner:
            top_scenarios.append({
                "scenario_id": winner.get("scenario_id", f"winner_{i}"),
                "research_direction": winner.get("research_direction", "Unknown"),
                "scenario_content": winner.get("scenario_content", ""),
                "competition_rank": i + 1,
                "selection_reasoning": f"Winner of {winner.get('research_direction', 'unknown')} direction tournament"
            })
    
    return top_scenarios

# Formatting functions for intermediate file outputs
def format_scenario_population(scenarios: list) -> str:
    """Format scenario population for markdown output."""
    content = "# Co-Scientist Scenario Population\n\n"
    content += f"**Total Scenarios Generated:** {len(scenarios)}\n\n"
    
    # Group by research direction
    by_direction = {}
    for scenario in scenarios:
        direction = scenario.get("research_direction", "Unknown")
        if direction not in by_direction:
            by_direction[direction] = []
        by_direction[direction].append(scenario)
    
    for direction, direction_scenarios in by_direction.items():
        content += f"## {direction} ({len(direction_scenarios)} scenarios)\n\n"
        
        for i, scenario in enumerate(direction_scenarios, 1):
            content += f"### Scenario {i} (Team: {scenario.get('team_id', 'Unknown')})\n"
            content += f"**Generated:** {scenario.get('generation_timestamp', 'Unknown')}\n\n"
            scenario_content = scenario.get('scenario_content', 'No content')
            # Truncate for readability
            if len(scenario_content) > 1000:
                content += scenario_content[:1000] + "...\n\n"
            else:
                content += scenario_content + "\n\n"
            content += "---\n\n"
    
    return content

def format_reflection_critiques(critiques: list) -> str:
    """Format reflection critiques for markdown output."""
    content = "# Co-Scientist Reflection Critiques\n\n"
    content += f"**Total Critiques Generated:** {len(critiques)}\n\n"
    
    # Group by domain
    by_domain = {}
    for critique in critiques:
        domain = critique.get("critique_domain", "Unknown")
        if domain not in by_domain:
            by_domain[domain] = []
        by_domain[domain].append(critique)
    
    for domain, domain_critiques in by_domain.items():
        content += f"## {domain.title()} Expert Critiques ({len(domain_critiques)})\n\n"
        
        for critique in domain_critiques:
            severity = critique.get("severity_score", "Unknown")
            scenario_id = critique.get("target_scenario_id", "Unknown")
            content += f"### Scenario {scenario_id[:8]}... (Severity: {severity}/10)\n"
            
            critique_content = critique.get('critique_content', 'No content')
            # Truncate for readability
            if len(critique_content) > 500:
                content += critique_content[:500] + "...\n\n"
            else:
                content += critique_content + "\n\n"
            content += "---\n\n"
    
    return content

def format_tournament_results(winners: list, all_results: list) -> str:
    """Format tournament results for markdown output."""
    content = "# Co-Scientist Tournament Results\n\n"
    content += f"**Number of Tournaments:** {len(winners)}\n\n"
    
    if not winners:
        content += "No tournament winners - likely due to scenario generation failures.\n\n"
        return content
    
    for i, winner in enumerate(winners, 1):
        if not winner:
            content += f"## Tournament {i}: Failed\n"
            content += "**Status:** Tournament failed or no valid participants\n\n"
            continue
            
        direction = winner.get("direction", "Unknown")
        winning_scenario = winner.get("winner", None)
        rounds = winner.get("total_rounds", "Unknown")
        
        content += f"## Tournament {i}: {direction}\n"
        content += f"**Rounds Completed:** {rounds}\n"
        
        if winning_scenario and isinstance(winning_scenario, dict):
            content += f"**Winner Team:** {winning_scenario.get('team_id', 'Unknown')}\n\n"
            
            # Show winner scenario content (truncated)
            scenario_content = winning_scenario.get('scenario_content', 'No content')
            if len(scenario_content) > 800:
                content += scenario_content[:800] + "...\n\n"
            else:
                content += scenario_content + "\n\n"
        else:
            content += "**Winner Team:** No valid winner\n\n"
            content += "No winning scenario content available.\n\n"
            
        content += "---\n\n"
    
    return content

def format_evolution_results(evolved_scenarios: list) -> str:
    """Format evolution results for markdown output."""
    content = "# Co-Scientist Evolution Results\n\n"
    content += f"**Total Evolution Attempts:** {len(evolved_scenarios)}\n\n"
    
    if not evolved_scenarios:
        content += "No evolution attempts were made - likely due to earlier phase failures.\n\n"
        return content
    
    # Group by strategy
    by_strategy = {}
    for evolution in evolved_scenarios:
        strategy = evolution.get("strategy", "Unknown")
        if strategy not in by_strategy:
            by_strategy[strategy] = []
        by_strategy[strategy].append(evolution)
    
    for strategy, strategy_evolutions in by_strategy.items():
        content += f"## {strategy.title()} Evolution ({len(strategy_evolutions)} attempts)\n\n"
        
        for evolution in strategy_evolutions:
            original_direction = evolution.get("original_direction", "Unknown")
            content += f"### {original_direction} - {strategy.title()}\n"
            
            evolved_content = evolution.get('evolved_content', 'No content')
            # Truncate for readability
            if len(evolved_content) > 800:
                content += evolved_content[:800] + "...\n\n"
            else:
                content += evolved_content + "\n\n"
            content += "---\n\n"
    
    return content

def format_complete_summary(state: dict, top_scenarios: list, competition_summary: str) -> str:
    """Format complete competition summary."""
    content = "# Complete Co-Scientist Competition Summary\n\n"
    
    # Overview
    content += "## Process Overview\n"
    content += competition_summary + "\n\n"
    
    # Research directions
    directions = state.get("research_directions", [])
    content += f"## Research Directions Identified ({len(directions)})\n"
    for i, direction in enumerate(directions, 1):
        content += f"### Direction {i}: {direction.get('name', 'Unknown')}\n"
        content += f"- **Assumption:** {direction.get('assumption', 'N/A')}\n"
        content += f"- **Focus:** {direction.get('focus', 'N/A')}\n\n"
    
    # Statistics
    population = state.get("scenario_population", [])
    critiques = state.get("reflection_critiques", [])
    winners = state.get("tournament_winners", [])
    evolved = state.get("evolved_scenarios", [])
    
    content += "## Competition Statistics\n"
    content += f"- **Scenarios Generated:** {len(population)}\n"
    content += f"- **Critiques Produced:** {len(critiques)}\n"
    content += f"- **Tournament Winners:** {len(winners)}\n"
    content += f"- **Evolution Attempts:** {len(evolved)}\n"
    content += f"- **Final Top Scenarios:** {len(top_scenarios)}\n\n"
    
    # Final winners
    content += "## Final Top Scenarios\n"
    for i, scenario in enumerate(top_scenarios, 1):
        direction = scenario.get("research_direction", "Unknown")
        rank = scenario.get("competition_rank", i)
        content += f"### Scenario {i}: {direction} (Rank #{rank})\n"
        reasoning = scenario.get("selection_reasoning", "Selected by tournament")
        content += f"**Selection Reasoning:** {reasoning}\n\n"
    
    return content

def format_evolution_tournament_results(final_representatives: list) -> str:
    """Format evolution tournament results for markdown output."""
    content = "# Co-Scientist Evolution Tournament Results\n\n"
    content += f"**Final Representatives Selected:** {len(final_representatives)}\n\n"
    
    for i, rep in enumerate(final_representatives, 1):
        direction = rep.get("direction", "Unknown").replace("Evolution_", "")
        winner = rep.get("winner", {})
        rounds = rep.get("total_rounds", "Unknown")
        
        content += f"## Evolution Tournament {i}: {direction}\n"
        content += f"**Rounds Completed:** {rounds}\n"
        content += f"**Final Winner:** {winner.get('team_id', 'Unknown')}\n"
        
        evolution_type = winner.get("evolution_type", "original")
        if evolution_type != "original":
            content += f"**Evolution Type:** {evolution_type.title()}\n"
        else:
            content += f"**Result:** Original winner retained\n"
        
        content += "\n"
        
        # Show winning scenario content (truncated)
        scenario_content = winner.get('scenario_content', 'No content')
        if len(scenario_content) > 800:
            content += scenario_content[:800] + "...\n\n"
        else:
            content += scenario_content + "\n\n"
        content += "---\n\n"
    
    return content

def format_research_directions(directions: list) -> str:
    """Format research directions for COMPETITION_SUMMARY_PROMPT."""
    if not directions:
        return "No research directions identified."
    
    formatted = ""
    for i, direction in enumerate(directions, 1):
        formatted += f"Direction {i}: {direction.get('name', 'Unknown')}\n"
        formatted += f"  Assumption: {direction.get('assumption', 'N/A')}\n"
        formatted += f"  Focus: {direction.get('focus', 'N/A')}\n"
    
    return formatted

# Build the co-scientist workflow
co_scientist_builder = StateGraph(CoScientistState, input=CoScientistInputState, config_schema=CoScientistConfiguration)

# Add nodes for each phase
co_scientist_builder.add_node("meta_analysis", meta_analysis_phase)
co_scientist_builder.add_node("scenario_generation", parallel_scenario_generation)
co_scientist_builder.add_node("reflection", reflection_phase)
co_scientist_builder.add_node("tournament", tournament_phase)
co_scientist_builder.add_node("evolution", evolution_phase)
co_scientist_builder.add_node("evolution_tournament", evolution_tournament_phase)
co_scientist_builder.add_node("meta_review", final_meta_review_phase)

# Define the workflow edges
co_scientist_builder.add_edge(START, "meta_analysis")
co_scientist_builder.add_edge("meta_analysis", "scenario_generation")
co_scientist_builder.add_edge("scenario_generation", "reflection")
co_scientist_builder.add_edge("reflection", "tournament")
co_scientist_builder.add_edge("tournament", "evolution")
co_scientist_builder.add_edge("evolution", "evolution_tournament")
co_scientist_builder.add_edge("evolution_tournament", "meta_review")
co_scientist_builder.add_edge("meta_review", END)

# Compile the co-scientist subgraph
co_scientist = co_scientist_builder.compile() 