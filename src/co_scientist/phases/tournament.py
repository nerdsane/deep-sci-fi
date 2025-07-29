"""
Tournament Phase - Competitive Evaluation and Ranking

This module handles the tournament-style competitive evaluation where scenarios
compete head-to-head in elimination brackets. It includes Elo rating systems
for skill tracking and comprehensive comparison analytics.

Key Features:
- Quality-based seeding for fair competition
- Elo rating system for dynamic skill tracking
- Parallel tournament execution across research directions
- Detailed comparison reasoning and analytics
- Comprehensive output management and debugging
"""

import asyncio
import traceback
from datetime import datetime
from typing import Dict, List, Any

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from co_scientist.state import CoScientistState
from co_scientist.configuration import CoScientistConfiguration
from co_scientist.elo_rating import EloTracker
from co_scientist.utils.output_manager import get_output_manager
from co_scientist.utils.content_formatters import format_content
from co_scientist.prompts.tournament_prompts import get_pairwise_prompt
from co_scientist.phases.reflection import integrate_quality_scores


async def tournament_phase(state: CoScientistState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Run tournament brackets for each research direction with quality-based seeding and Elo ratings.
    
    This is the main entry point for the tournament phase. It organizes scenarios into
    tournament brackets by research direction, runs parallel competitions, and tracks
    performance using Elo ratings for dynamic skill assessment.
    
    Args:
        state: Current workflow state containing scenario population and reflection critiques
        config: LangGraph configuration with tournament settings
        
    Returns:
        dict: Updated state with tournament winners, results, and Elo tracker
    """
    configuration = CoScientistConfiguration.from_runnable_config(config)
    
    # Check if we have any scenarios to run tournaments on
    scenario_population = state.get("scenario_population", [])
    if not scenario_population:
        print("No scenarios available for tournaments - returning empty results")
        return {
            "tournament_winners": [],
            "tournament_complete": True
        }
    
    # Integrate quality scores from reflection critiques into scenarios
    reflection_critiques = state.get("reflection_critiques", [])
    scenarios_with_quality = integrate_quality_scores(scenario_population, reflection_critiques)
    
    print(f"Integrated quality scores for {len(scenarios_with_quality)} scenarios")
    
    # Initialize Elo rating system
    elo_tracker = EloTracker(k_factor=32)  # Standard K-factor
    elo_tracker.initialize_from_quality(scenarios_with_quality, quality_weight=0.6)
    
    # Attach initial Elo ratings to scenarios
    for scenario in scenarios_with_quality:
        scenario_id = scenario.get("scenario_id")
        if scenario_id:
            scenario["elo_rating"] = elo_tracker.get_rating(scenario_id)
    
    print(f"Initialized Elo ratings for {len(elo_tracker.ratings)} scenarios")
    elo_stats = elo_tracker.get_statistics()
    print(f"Elo statistics: avg={elo_stats['average']:.0f}, range={elo_stats['min']:.0f}-{elo_stats['max']:.0f}")
    
    # Group scenarios by research direction
    direction_groups = {}
    for scenario in scenarios_with_quality:
        direction = scenario["research_direction"]
        if direction not in direction_groups:
            direction_groups[direction] = []
        direction_groups[direction].append(scenario)
    
    # Apply quality-based seeding within each direction (Elo ratings will be used for bracket display)
    for direction, scenarios in direction_groups.items():
        # Sort by quality score (highest first) for better seeding
        scenarios.sort(key=lambda s: s.get("quality_score", 0), reverse=True)
        
        quality_scores = [s.get("quality_score", 0) for s in scenarios]
        elo_ratings = [s.get("elo_rating", 1500) for s in scenarios]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        avg_elo = sum(elo_ratings) / len(elo_ratings) if elo_ratings else 1500
        
        print(f"Direction '{direction}': {len(scenarios)} scenarios")
        print(f"  Quality: avg={avg_quality:.1f}, range={min(quality_scores)}-{max(quality_scores)}")
        print(f"  Elo: avg={avg_elo:.0f}, range={min(elo_ratings):.0f}-{max(elo_ratings):.0f}")
        
        direction_groups[direction] = scenarios
    
    # Run parallel tournaments for each direction with Elo tracking
    tournament_tasks = []
    for direction, scenarios in direction_groups.items():
        task = run_direction_tournament(direction, scenarios, config, elo_tracker, state)
        tournament_tasks.append(task)
    
    try:
        tournament_results = await asyncio.gather(*tournament_tasks, return_exceptions=True)
    
        print(f"Tournament results gathered: {len(tournament_results)} results")
        for i, result in enumerate(tournament_results):
            if isinstance(result, Exception):
                print(f"Tournament {i} failed with exception: {result}")
                print(f"Tournament {i} traceback:")
                print(traceback.format_exception(type(result), result, result.__traceback__))
            else:
                print(f"Tournament {i} succeeded: direction={result.get('direction', 'unknown')}, winner={result.get('winner', {}).get('scenario_id', 'none')}")
    
        # Collect winners from each direction
        direction_winners = [
            result for result in tournament_results 
            if not isinstance(result, Exception)
        ]
        
        print(f"Successfully collected {len(direction_winners)} direction winners from {len(tournament_results)} tournaments")
        
    except Exception as e:
        print(f"Critical error in tournament execution: {e}")
        print(f"Tournament execution traceback:")
        print(traceback.format_exc())
        direction_winners = []
    
    # Collect final Elo statistics
    final_elo_tracker = None
    if direction_winners:
        print(f"🔍 TOURNAMENT DEBUG: Processing {len(direction_winners)} direction winners")
        # Use the Elo tracker from the first tournament (they should all be the same instance)
        for i, winner in enumerate(direction_winners):
            elo_tracker_obj = winner.get("elo_tracker")
            print(f"🔍 TOURNAMENT DEBUG: Winner {i} elo_tracker type: {type(elo_tracker_obj)}")
            print(f"🔍 TOURNAMENT DEBUG: Winner {i} elo_tracker bool: {bool(elo_tracker_obj)}")
            if elo_tracker_obj is not None:
                print(f"🔍 TOURNAMENT DEBUG: Using elo_tracker from winner {i}")
                final_elo_tracker = elo_tracker_obj
                break
            else:
                print(f"🔍 TOURNAMENT DEBUG: Winner {i} has None elo_tracker")
        
        if final_elo_tracker:
            final_elo_stats = final_elo_tracker.get_statistics()
            print(f"Final Elo statistics: avg={final_elo_stats['average']:.0f}, range={final_elo_stats['min']:.0f}-{final_elo_stats['max']:.0f}")
            
            # Update all tournament winners with final Elo ratings
            for tournament_result in direction_winners:
                winner = tournament_result.get("winner")
                if winner and winner.get("scenario_id"):
                    winner["elo_rating"] = final_elo_tracker.get_rating(winner["scenario_id"])
    
    # Save tournament results
    if configuration.save_intermediate_results:
        # Save tournament data with full reasoning and Elo information
        manager = get_output_manager(configuration.output_dir, configuration.phase)
        
        # Extract individual comparisons from all tournaments for detailed saving
        all_comparisons = []
        for tournament_result in direction_winners:
            tournament_comparisons = tournament_result.get("all_comparisons", [])
            for comparison in tournament_comparisons:
                # Add tournament context to each comparison
                enhanced_comparison = comparison.copy()
                enhanced_comparison["direction"] = tournament_result.get("direction", "Unknown")
                all_comparisons.append(enhanced_comparison)
        
        manager.save_tournament_comparisons(all_comparisons)
        
        # Save raw JSON data for debugging (including Elo data)
        manager.save_structured_data("raw_data", {"tournaments": direction_winners}, filename="tournaments_raw_data.json", subdirectory="raw_data")
        
        # Save Elo rating data and statistics
        if final_elo_tracker:
            elo_export = {
                "final_ratings": final_elo_tracker.ratings,
                "rating_history": final_elo_tracker.rating_history,
                "statistics": final_elo_tracker.get_statistics(),
                "leaderboard": final_elo_tracker.get_leaderboard()
            }
            manager.save_structured_data("raw_data", elo_export, filename="elo_ratings.json", subdirectory="raw_data")
        
        # Note: Tournament summary removed - leaderboard and individual tournament files provide better information
    
    print(f"🔍 TOURNAMENT RETURN DEBUG: final_elo_tracker type: {type(final_elo_tracker)}")
    print(f"🔍 TOURNAMENT RETURN DEBUG: final_elo_tracker bool: {bool(final_elo_tracker)}")
    if final_elo_tracker:
        print(f"🔍 TOURNAMENT RETURN DEBUG: final_elo_tracker has {len(final_elo_tracker.ratings)} ratings")
    else:
        print("🔍 TOURNAMENT RETURN DEBUG: final_elo_tracker is None/False")
    
    return {
        "tournament_rounds": tournament_results,
        "tournament_winners": direction_winners,  # Each winner already contains elo_tracker
        "tournament_complete": True
    }


async def run_direction_tournament(direction: str, scenarios: List[Dict[str, Any]], config: RunnableConfig, elo_tracker: EloTracker, state: CoScientistState = None) -> Dict[str, Any]:
    """
    Run tournament bracket for a single research direction with Elo rating updates.
    
    This function manages the complete tournament bracket for one research direction,
    conducting elimination rounds until a single winner emerges. It tracks all
    comparisons and maintains detailed progression records.
    
    Args:
        direction: Research direction name
        scenarios: List of scenarios competing in this direction
        config: Configuration with tournament settings
        elo_tracker: Elo rating tracker for skill updates
        state: Optional workflow state for context
        
    Returns:
        dict: Tournament results with winner, progression, and comparison data
    """
    if len(scenarios) < 2:
        winner = scenarios[0] if scenarios else None
        return {
            "direction": direction,
            "winner": winner,
            "total_rounds": 0,
            "all_comparisons": [],
            "round_progression": [],
            "elo_tracker": elo_tracker  # Include Elo tracker in results
        }
    
    current_round = scenarios.copy()
    round_number = 1
    all_comparisons = []
    round_progression = []
    
    print(f"Starting tournament for direction '{direction}' with {len(scenarios)} scenarios")
    
    while len(current_round) > 1:
        print(f"Round {round_number} - {len(current_round)} scenarios")
        round_progression.append({
            "round_number": round_number,
            "participants": [s["scenario_id"] for s in current_round],
            "participant_count": len(current_round)
        })
        
        # Create comparison tasks for this round
        round_tasks = []
        for i in range(0, len(current_round), 2):
            if i + 1 < len(current_round):
                # Regular matchup
                task = pairwise_comparison(
                    current_round[i], current_round[i + 1], round_number, config, elo_tracker, state
                )
                round_tasks.append(task)
            else:
                # Bye (odd number of scenarios) - scenario advances automatically
                bye_result = {
                    "round": round_number,
                    "scenario1_id": current_round[i]["scenario_id"],
                    "scenario2_id": None,
                    "winner": current_round[i],
                    "winner_number": 1,
                    "reasoning": "Automatic bye (odd number of scenarios)",
                    "timestamp": datetime.now().isoformat(),
                    "elo_data": {"bye": True}
                }
                round_tasks.append(bye_result)
        
        # Wait for all comparisons in this round to complete
        if any(asyncio.iscoroutine(task) for task in round_tasks):
            # Some tasks are coroutines, gather them
            coroutine_tasks = [task for task in round_tasks if asyncio.iscoroutine(task)]
            non_coroutine_results = [task for task in round_tasks if not asyncio.iscoroutine(task)]
            
            if coroutine_tasks:
                round_results = await asyncio.gather(*coroutine_tasks, return_exceptions=True)
                round_results.extend(non_coroutine_results)
            else:
                round_results = non_coroutine_results
        else:
            # All tasks are already results (bye scenarios)
            round_results = round_tasks
        
        # Process round results and advance winners
        next_round = []
        for result in round_results:
            if isinstance(result, Exception):
                print(f"Comparison failed in round {round_number}: {result}")
                # In case of failure, advance the first scenario arbitrarily
                if len(current_round) > 0:
                    next_round.append(current_round[0])
            else:
                all_comparisons.append(result)
                next_round.append(result["winner"])
        
        current_round = next_round
        round_number += 1
    
    # Tournament complete
    winner = current_round[0] if current_round else None
    
    print(f"Tournament complete for direction '{direction}'. Winner: {winner['scenario_id'] if winner else 'None'}")
    
    return {
        "direction": direction,
        "winner": winner,
        "total_rounds": round_number - 1,
        "all_comparisons": all_comparisons,
        "round_progression": round_progression,
        "elo_tracker": elo_tracker  # Include Elo tracker in results
    }


async def pairwise_comparison(scenario1: Dict[str, Any], scenario2: Dict[str, Any], round_number: int, config: RunnableConfig, elo_tracker: EloTracker, state: CoScientistState = None) -> Dict[str, Any]:
    """
    Compare two scenarios head-to-head with Elo rating updates.
    
    This function conducts a detailed comparison between two scenarios using an LLM judge.
    It includes context from the overall project state and updates Elo ratings based on
    the outcome, tracking upsets and expected results.
    
    Args:
        scenario1: First scenario to compare
        scenario2: Second scenario to compare
        round_number: Current tournament round number
        config: Configuration with comparison settings
        elo_tracker: Elo rating tracker for skill updates
        state: Optional workflow state for additional context
        
    Returns:
        dict: Comparison result with winner, reasoning, and Elo data
    """
    configuration = CoScientistConfiguration.from_runnable_config(config)
    
    # Import model factory and retry logic
    from co_scientist.co_scientist import llm_call_with_retry
    from co_scientist.utils.model_factory import create_model_factory
    
    # Create model using centralized factory
    model_factory = create_model_factory(configuration)
    llm = model_factory.create_phase_model("tournament")
    
    # Get pre-comparison Elo ratings
    scenario1_id = scenario1["scenario_id"]
    scenario2_id = scenario2["scenario_id"]
    scenario1_elo_before = elo_tracker.get_rating(scenario1_id)
    scenario2_elo_before = elo_tracker.get_rating(scenario2_id)
    
    # Get the appropriate prompt for this use case
    use_case = configuration.use_case.value if hasattr(configuration.use_case, 'value') else str(configuration.use_case)
    
    # Extract projection context if available
    baseline_world_state = None
    years_in_future = None
    storyline = None
    chapter_arc = None
    if state:
        baseline_world_state = state.get("baseline_world_state")
        years_in_future = state.get("years_in_future")
        storyline = state.get("storyline")
        chapter_arc = state.get("chapter_arc")
    
    pairwise_prompt_template = get_pairwise_prompt(use_case, baseline_world_state, years_in_future, storyline, chapter_arc)
    
    # Prepare prompt parameters with baseline context if available
    prompt_params = {
        "scenario1_content": scenario1["scenario_content"],
        "direction1": scenario1["research_direction"],
        "scenario2_content": scenario2["scenario_content"],
        "direction2": scenario2["research_direction"],
        "baseline_world_state": baseline_world_state or "No baseline world state provided",
        "years_in_future": years_in_future or "unspecified timeframe",
        "storyline": storyline or "No storyline context provided",
        "chapter_arc": chapter_arc or "No chapter arc provided"
    }
    
    comparison_prompt = pairwise_prompt_template.format(**prompt_params)
    
    response = await llm_call_with_retry(llm, [HumanMessage(content=comparison_prompt)])
    
    # More robust winner determination
    response_text = response.content.lower()
    
    # Look for the decision pattern
    if "better scenario: 1" in response_text:
        winner = scenario1
        loser = scenario2
        winner_number = 1
    elif "better scenario: 2" in response_text:
        winner = scenario2
        loser = scenario1
        winner_number = 2
    else:
        # Fallback: look for any mention of scenario numbers at the end
        if "scenario 1" in response_text.split()[-20:]:  # Check last 20 words
            winner = scenario1
            loser = scenario2
            winner_number = 1
        else:
            winner = scenario2
            loser = scenario1
            winner_number = 2
    
    # Update Elo ratings based on the outcome
    winner_id = winner["scenario_id"]
    loser_id = loser["scenario_id"]
    elo_update = elo_tracker.update_ratings(winner_id, loser_id)
    
    # Update scenarios with new Elo ratings
    winner["elo_rating"] = elo_update["winner_rating_after"]
    loser["elo_rating"] = elo_update["loser_rating_after"]
    
    return {
        "round": round_number,
        "scenario1_id": scenario1_id,
        "scenario2_id": scenario2_id,
        "winner": winner,
        "winner_number": winner_number,
        "reasoning": response.content,
        "timestamp": datetime.now().isoformat(),
        # Elo rating information
        "elo_data": {
            "scenario1_elo_before": scenario1_elo_before,
            "scenario2_elo_before": scenario2_elo_before,
            "winner_elo_before": elo_update["winner_rating_before"],
            "winner_elo_after": elo_update["winner_rating_after"],
            "winner_elo_change": elo_update["winner_change"],
            "loser_elo_before": elo_update["loser_rating_before"],
            "loser_elo_after": elo_update["loser_rating_after"],
            "loser_elo_change": elo_update["loser_change"],
            "winner_expected": elo_update["winner_expected"],
            "upset": elo_update["upset"]
        }
    } 