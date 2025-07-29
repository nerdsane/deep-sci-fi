"""
Evolution Phase - Scenario Improvement and Enhancement

This module handles the evolution phase where winning scenarios are enhanced using
multiple improvement strategies. It includes competitive tournaments between original
and evolved scenarios to determine the best representatives.

Key Features:
- Multiple evolution strategies (enhancement, refinement, extension)
- Comprehensive feedback integration from critiques and debates
- Evolution tournaments (original vs evolved scenarios)
- Parallel evolution processing for efficiency
- Detailed evolution tracking and metadata
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Any

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from co_scientist.state import CoScientistState
from co_scientist.configuration import CoScientistConfiguration
from co_scientist.utils.output_manager import get_output_manager
from co_scientist.utils.content_formatters import format_content
from co_scientist.prompts.evolution_prompts import get_evolution_prompt
from co_scientist.utils.feedback_utils import get_comprehensive_feedback_summary


async def evolution_phase(state: CoScientistState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Evolve winning scenarios using multiple enhancement strategies.
    
    This is the main entry point for the evolution phase. It takes tournament winners
    and applies various enhancement strategies to improve their quality and depth,
    creating evolved variants for further competition.
    
    Args:
        state: Current workflow state containing tournament winners
        config: LangGraph configuration with evolution settings
        
    Returns:
        dict: Updated state with evolved scenarios and completion status
    """
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
    evolution_strategies = configuration.get_evolution_strategies()
    
    print(f"Starting evolution for {len(winners)} winners using {len(evolution_strategies)} strategies")
    
    for winner in winners:
        for strategy in evolution_strategies:
            task = evolve_scenario(winner, strategy, state, config)
            evolution_tasks.append(task)
    
    print(f"Created {len(evolution_tasks)} evolution tasks")
    
    # Execute all evolution in parallel
    evolution_results = await asyncio.gather(*evolution_tasks, return_exceptions=True)
    
    # Filter valid evolution results
    evolved_scenarios = []
    failed_evolutions = []
    
    for i, result in enumerate(evolution_results):
        if isinstance(result, Exception):
            failed_evolutions.append(f"Task {i}: {str(result)}")
            print(f"Evolution failed for task {i}: {result}")
        else:
            evolved_scenarios.append(result)
    
    print(f"Evolution complete: {len(evolved_scenarios)} successful, {len(failed_evolutions)} failed")
    if failed_evolutions:
        print("Failed evolutions:", failed_evolutions)
    
    # Save evolution results
    if configuration.save_intermediate_results:
        # Save evolution attempts with full prompts and reasoning
        manager = get_output_manager(configuration.output_dir, configuration.phase)
        manager.save_evolution_attempts(evolved_scenarios)
        
        # Save raw JSON data for debugging
        manager.save_structured_data("raw_data", {"evolutions": evolved_scenarios}, filename="evolutions_raw_data.json", subdirectory="raw_data")
        
        # Save summary
        evolution_content = format_content("evolution_results", evolved_scenarios)
        manager.save_simple_content("evolution_results_summary.md", evolution_content)
    
    return {
        "evolved_scenarios": evolved_scenarios,
        "evolution_complete": True
    }


async def evolution_tournament_phase(state: CoScientistState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Run tournament between original winners and their evolved variants within each direction.
    
    This phase conducts competitive tournaments where original winning scenarios
    compete against their evolved variants to determine the final representatives
    for each research direction.
    
    Args:
        state: Current workflow state containing evolved scenarios and tournament winners
        config: LangGraph configuration with tournament settings
        
    Returns:
        dict: Updated state with final representatives and evolution tournament results
    """
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
    
    print(f"Starting evolution tournaments for {len(original_winners)} directions")
    print(f"Evolved scenarios available for {len(evolved_by_direction)} directions")
    
    # Run evolution tournament for each direction
    evolution_tournament_tasks = []
    
    for original_winner in original_winners:
        direction = original_winner.get("research_direction", "Unknown")
        
        # Get evolved variants for this direction
        evolved_variants = evolved_by_direction.get(direction, [])
        
        if not evolved_variants:
            print(f"No evolved variants for direction '{direction}', skipping evolution tournament")
            continue
        
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
        
        print(f"Direction '{direction}': {len(competitors)} competitors (1 original + {len(evolved_variants)} evolved)")
        
        # Run tournament for this direction (original + evolved)
        task = run_evolution_tournament_with_metadata(direction, original_winner, competitors, config, state)
        evolution_tournament_tasks.append(task)
    
    print(f"Created {len(evolution_tournament_tasks)} evolution tournament tasks")
    
    # Execute all evolution tournaments in parallel
    evolution_results = await asyncio.gather(*evolution_tournament_tasks, return_exceptions=True)
    
    # Collect final representatives
    final_representatives = []
    failed_tournaments = []
    
    for i, result in enumerate(evolution_results):
        if isinstance(result, Exception):
            failed_tournaments.append(f"Tournament {i}: {str(result)}")
            print(f"Evolution tournament failed for task {i}: {result}")
        else:
            final_representatives.append(result)
    
    print(f"Evolution tournaments complete: {len(final_representatives)} successful, {len(failed_tournaments)} failed")
    
    # Save evolution tournament results
    if configuration.save_intermediate_results:
        # Save detailed evolution tournament comparisons
        manager = get_output_manager(configuration.output_dir, configuration.phase)
        manager.save_tournament_comparisons(evolution_results, "evolution_tournaments")
        
        # Save raw JSON data for debugging
        manager.save_structured_data("raw_data", {"evolution_tournaments": evolution_results}, filename="evolution_tournaments_raw_data.json", subdirectory="raw_data")
        
        # Save summary
        tournament_content = format_content("evolution_tournament_results", final_representatives)
        manager.save_simple_content("evolution_tournaments_summary.md", tournament_content)
    
    return {
        "evolution_tournament_results": evolution_results,
        "final_representatives": final_representatives,
        "evolution_tournament_complete": True
    }


async def run_evolution_tournament_with_metadata(direction: str, original_winner: Dict[str, Any], competitors: List[Dict[str, Any]], config: RunnableConfig, state: CoScientistState = None) -> Dict[str, Any]:
    """
    Run evolution tournament and add metadata about original vs evolved scenarios.
    
    This function conducts a tournament between the original winner and its evolved
    variants, tracking whether each comparison is between original/evolved scenarios
    and providing detailed metadata about the competition dynamics.
    
    Args:
        direction: Research direction name
        original_winner: Original winning scenario
        competitors: List including original winner and evolved variants
        config: Configuration with tournament settings
        state: Optional workflow state for context
        
    Returns:
        dict: Tournament results with original vs evolved metadata
    """
    # Import the tournament function (will be from tournament module)
    from co_scientist.phases.tournament import run_direction_tournament
    
    # Run the tournament
    tournament_result = await run_direction_tournament(f"Evolution_{direction}", competitors, config, None, state)
    
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
    
    print(f"Evolution tournament for '{direction}' complete. Final winner: {final_winner_type}")
    
    return {
        "direction": direction,
        "original_winner": original_winner,
        "final_winner": enhanced_final_winner,
        "comparisons": enhanced_comparisons,
        "total_rounds": tournament_result.get("total_rounds", 0),
        "round_progression": tournament_result.get("round_progression", []),
        "tournament_successful": True
    }


async def evolve_scenario(scenario: Dict[str, Any], strategy: str, state: CoScientistState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Evolve a single scenario using the specified enhancement strategy.
    
    This function applies a specific evolution strategy to improve a scenario,
    incorporating comprehensive feedback from critiques and debates to guide
    the enhancement process.
    
    Args:
        scenario: Scenario dictionary to evolve
        strategy: Evolution strategy to apply
        state: Current workflow state with feedback data
        config: Configuration with evolution settings
        
    Returns:
        dict: Evolution result with original content, evolved content, and metadata
    """
    configuration = CoScientistConfiguration.from_runnable_config(config)
    
    # Collect comprehensive feedback for evolution - includes both critiques AND debate results
    debate_summary = state.get("debate_summary_for_evolution")
    debate_winner_id = None
    if state.get("debate_winner"):
        debate_winner_id = state["debate_winner"].get("scenario_id")
    
    critique_summary = get_comprehensive_feedback_summary(
        scenario["scenario_id"], 
        state["reflection_critiques"],
        debate_summary,
        debate_winner_id
    )
    
    # Get world state context if available
    world_state_context = ""
    if "world_state_context" in state:
        world_state_context = state["world_state_context"]
    elif "baseline_world_state" in state:
        world_state_context = state["baseline_world_state"]
    
    print(f"Evolving scenario {scenario['scenario_id']} using {strategy} strategy")
    
    # Create evolution prompt using the new use case-specific templates
    evolution_prompt = get_evolution_prompt(
        use_case=configuration.use_case.value,
        original_content=scenario["scenario_content"],
        research_direction=scenario["research_direction"],
        critique_summary=critique_summary,
        world_state_context=world_state_context
    )
    
    # Import model factory and retry logic
    from co_scientist.co_scientist import llm_call_with_retry
    from co_scientist.utils.model_factory import create_model_factory
    
    # Create model using centralized factory
    model_factory = create_model_factory(configuration)
    llm = model_factory.create_phase_model("evolution")
    
    try:
        response = await llm_call_with_retry(llm, [HumanMessage(content=evolution_prompt)])
        evolved_content = response.content
        print(f"Successfully evolved scenario {scenario['scenario_id']} using {strategy} strategy, content length: {len(evolved_content)}")
    except Exception as e:
        print(f"Failed to evolve scenario {scenario['scenario_id']} with {strategy}: {e}")
        evolved_content = f"Evolution failed for {strategy} strategy on scenario {scenario['scenario_id']}. Error: {str(e)}"
    
    return {
        "evolution_id": str(uuid.uuid4()),
        "original_scenario_id": scenario["scenario_id"],
        "original_scenario_content": scenario["scenario_content"],
        "evolution_prompt": evolution_prompt,
        "strategy": strategy,
        "evolved_content": evolved_content,
        "original_direction": scenario["research_direction"],
        "critique_summary": critique_summary,
        "world_state_context": world_state_context,
        "timestamp": datetime.now().isoformat()
    } 