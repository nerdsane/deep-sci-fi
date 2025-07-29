"""
Ranking Phase - Elo-based Leaderboard Compilation and Analytics

This module handles the compilation of comprehensive Elo-based leaderboards for all
tournament participants, including detailed performance analytics and statistics.

Key Features:
- Comprehensive Elo leaderboard compilation
- Detailed performance metrics and analytics
- Direction-based performance analysis
- Upset detection and volatility analysis
- Performance tier categorization
- Competition statistics and insights
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Any, Literal

from langchain_core.runnables import RunnableConfig

from co_scientist.state import CoScientistState
from co_scientist.configuration import CoScientistConfiguration
from co_scientist.utils.output_manager import get_output_manager
from co_scientist.utils.content_formatters import format_content


async def ranking_phase(state: CoScientistState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Compile comprehensive Elo-based leaderboard for all tournament participants.
    
    This phase analyzes all tournament results and creates detailed rankings using
    Elo rating systems, including comprehensive analytics about performance patterns,
    direction-based comparisons, and competition insights.
    
    Args:
        state: Current workflow state containing tournament results and Elo data
        config: Configuration with ranking settings
        
    Returns:
        dict: Updated state with comprehensive leaderboard data and analytics
    """
    configuration = CoScientistConfiguration.from_runnable_config(config)
    
    print("🔍 RANKING DEBUG: Ranking phase started!")
    print(f"🔍 RANKING DEBUG: State contains keys: {list(state.keys())}")
    
    # Get tournament data and Elo tracker
    tournament_winners = state.get("tournament_winners", [])
    scenario_population = state.get("scenario_population", [])
    
    print(f"🔍 RANKING DEBUG: Found {len(tournament_winners)} tournament winners")
    print(f"🔍 RANKING DEBUG: Found {len(scenario_population)} scenarios")
    
    # Simple approach: Use existing elo_tracker from tournament winners
    elo_tracker = None
    if tournament_winners:
        for winner in tournament_winners:
            winner_elo_tracker = winner.get("elo_tracker")
            if winner_elo_tracker and hasattr(winner_elo_tracker, 'ratings'):
                elo_tracker = winner_elo_tracker
                print(f"🔍 RANKING DEBUG: Using elo_tracker from winner with {len(elo_tracker.ratings)} ratings")
                break
    
    # Fallback: Read from saved file if we didn't find elo_tracker in winners
    if not elo_tracker:
        print("🔍 RANKING DEBUG: No elo_tracker in winners, trying file fallback...")
        try:
            # Try to load from the elo_ratings.json file that tournament phase saves
            import json
            import os
            elo_file_path = os.path.join(configuration.output_dir, "raw_data", "elo_ratings.json")
            if os.path.exists(elo_file_path):
                with open(elo_file_path, 'r') as f:
                    elo_data = json.load(f)
                    
                from co_scientist.elo_rating import EloTracker
                elo_tracker = EloTracker(k_factor=32)
                elo_tracker.ratings = elo_data.get("final_ratings", {})
                elo_tracker.rating_history = elo_data.get("rating_history", {})
                print(f"🔍 RANKING DEBUG: Loaded elo_tracker from file with {len(elo_tracker.ratings)} ratings")
        except Exception as e:
            print(f"🔍 RANKING DEBUG: File fallback failed: {e}")
    
    # Final check - if we still don't have elo_tracker, return empty results
    if not elo_tracker:
        print("❌ RANKING DEBUG: No Elo tracker available for ranking")
        print(f"❌ RANKING DEBUG: tournament_winners length: {len(tournament_winners)}")
        print(f"❌ RANKING DEBUG: state keys: {list(state.keys())}")
        if tournament_winners:
            print(f"❌ RANKING DEBUG: First tournament winner keys: {list(tournament_winners[0].keys())}")
            # Check what's actually in the elo_tracker field
            first_winner_elo = tournament_winners[0].get("elo_tracker")
            print(f"❌ RANKING DEBUG: First winner elo_tracker type: {type(first_winner_elo)}")
        return {
            "leaderboard_data": {},
            "ranking_complete": True
        }
    
    print(f"Compiling Elo leaderboard for {len(elo_tracker.ratings)} scenarios")
    
    # Get comprehensive leaderboard from Elo tracker
    leaderboard = elo_tracker.get_leaderboard()
    elo_stats = elo_tracker.get_statistics()
    
    # Build detailed leaderboard with enhanced metrics
    detailed_leaderboard = []
    
    for rank, (scenario_id, final_rating) in enumerate(leaderboard, 1):
        # Find the original scenario data
        scenario_data = None
        for scenario in scenario_population:
            if scenario.get("scenario_id") == scenario_id:
                scenario_data = scenario
                break
        
        if not scenario_data:
            continue
            
        # Get rating history for this scenario
        rating_history = elo_tracker.get_rating_history(scenario_id)
        initial_rating = rating_history[0]['rating'] if rating_history else 1500
        rating_change = final_rating - initial_rating
        
        # Calculate performance metrics from rating history
        total_matches = len(rating_history) - 1  # Subtract initial rating
        wins = sum(1 for entry in rating_history[1:] if "Beat" in entry.get('reason', ''))
        losses = total_matches - wins
        win_rate = (wins / total_matches * 100) if total_matches > 0 else 0
        
        # Find biggest single rating change
        biggest_gain = 0
        biggest_loss = 0
        if len(rating_history) > 1:
            for i in range(1, len(rating_history)):
                change = rating_history[i]['rating'] - rating_history[i-1]['rating']
                if change > biggest_gain:
                    biggest_gain = change
                if change < biggest_loss:
                    biggest_loss = change
        
        # Check if this scenario won its direction tournament
        direction_winner = False
        tournament_placement = "Eliminated"
        for tournament in tournament_winners:
            winner = tournament.get("winner", {})
            if winner.get("scenario_id") == scenario_id:
                direction_winner = True
                tournament_placement = f"Winner - {winner.get('research_direction', 'Unknown')}"
                break
        
        # Compile detailed entry
        leaderboard_entry = {
            "rank": rank,
            "scenario_id": scenario_id,
            "team_id": scenario_data.get("team_id", "Unknown"),
            "research_direction": scenario_data.get("research_direction", "Unknown"),
            "core_assumption": scenario_data.get("core_assumption", ""),
            
            # Elo metrics
            "final_elo_rating": round(final_rating, 1),
            "initial_elo_rating": round(initial_rating, 1),
            "elo_change": round(rating_change, 1),
            "elo_change_percentage": round((rating_change / initial_rating * 100), 1) if initial_rating > 0 else 0,
            
            # Performance metrics
            "total_matches": total_matches,
            "wins": wins,
            "losses": losses,
            "win_rate": round(win_rate, 1),
            "biggest_gain": round(biggest_gain, 1),
            "biggest_loss": round(biggest_loss, 1),
            
            # Quality and tournament data
            "quality_score": scenario_data.get("quality_score", 0),
            "tournament_placement": tournament_placement,
            "direction_winner": direction_winner,
            
            # Performance categories
            "performance_tier": _categorize_performance(rank, len(leaderboard)),
            "rating_volatility": round(abs(biggest_gain) + abs(biggest_loss), 1),
            "upset_potential": initial_rating > final_rating and direction_winner  # Low seed winner
        }
        
        detailed_leaderboard.append(leaderboard_entry)
    
    # Calculate additional analytics
    leaderboard_analytics = _calculate_leaderboard_analytics(detailed_leaderboard, elo_stats)
    
    # Compile comprehensive leaderboard data
    leaderboard_data = {
        "rankings": detailed_leaderboard,
        "analytics": leaderboard_analytics,
        "elo_statistics": elo_stats,
        "total_participants": len(detailed_leaderboard),
        "timestamp": datetime.now().isoformat()
    }
    
    # Save leaderboard outputs
    if configuration.save_intermediate_results:
        print(f"💾 Saving Elo leaderboard with {len(detailed_leaderboard)} scenarios...")
        manager = get_output_manager(configuration.output_dir, configuration.phase)
        manager.save_leaderboard(leaderboard_data)
    
    print(f"Ranking complete: {len(detailed_leaderboard)} scenarios ranked")
    print(f"Top performer: {detailed_leaderboard[0]['team_id'] if detailed_leaderboard else 'None'} "
          f"({detailed_leaderboard[0]['final_elo_rating']:.0f} Elo)" if detailed_leaderboard else "")
    
    # Debug: Confirm what we're returning
    print(f"🔍 DEBUG RANKING: Returning leaderboard_data with {len(detailed_leaderboard)} rankings")
    print(f"🔍 DEBUG RANKING: Leaderboard data keys: {list(leaderboard_data.keys())}")
    if detailed_leaderboard:
        print(f"🔍 DEBUG RANKING: Sample ranking entry: team_id={detailed_leaderboard[0].get('team_id')}, rank={detailed_leaderboard[0].get('rank')}")
    
    return {
        "leaderboard_data": leaderboard_data,
        "ranking_complete": True
    }


def _categorize_performance(rank: int, total: int) -> str:
    """
    Categorize performance tier based on ranking position.
    
    Args:
        rank: The ranking position (1-based)
        total: Total number of participants
        
    Returns:
        str: Performance tier category
    """
    percentile = (rank - 1) / total if total > 0 else 0
    
    if percentile <= 0.1:
        return "Elite"
    elif percentile <= 0.25:
        return "High Performer"
    elif percentile <= 0.5:
        return "Above Average"
    elif percentile <= 0.75:
        return "Average"
    else:
        return "Below Average"


def _calculate_leaderboard_analytics(leaderboard: List[Dict[str, Any]], elo_stats: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate comprehensive analytics from the leaderboard.
    
    Args:
        leaderboard: List of detailed leaderboard entries
        elo_stats: Elo rating statistics
        
    Returns:
        dict: Comprehensive analytics including direction performance, upsets, and metrics
    """
    if not leaderboard:
        return {}
    
    # Direction performance analysis
    direction_performance = {}
    for entry in leaderboard:
        direction = entry["research_direction"]
        if direction not in direction_performance:
            direction_performance[direction] = {
                "participants": 0,
                "total_elo": 0,
                "winner_rank": None,
                "best_rank": float('inf'),
                "worst_rank": 0
            }
        
        direction_stats = direction_performance[direction]
        direction_stats["participants"] += 1
        direction_stats["total_elo"] += entry["final_elo_rating"]
        direction_stats["best_rank"] = min(direction_stats["best_rank"], entry["rank"])
        direction_stats["worst_rank"] = max(direction_stats["worst_rank"], entry["rank"])
        
        if entry["direction_winner"]:
            direction_stats["winner_rank"] = entry["rank"]
    
    # Calculate direction averages
    for direction, stats in direction_performance.items():
        if stats["participants"] > 0:
            stats["average_elo"] = round(stats["total_elo"] / stats["participants"], 1)
    
    # Upset analysis
    upsets = [entry for entry in leaderboard if entry["upset_potential"]]
    biggest_upsets = sorted(leaderboard, key=lambda x: x["elo_change"], reverse=True)[:3]
    biggest_falls = sorted(leaderboard, key=lambda x: x["elo_change"])[:3]
    
    # Performance distribution
    elite_count = len([e for e in leaderboard if e["performance_tier"] == "Elite"])
    high_performer_count = len([e for e in leaderboard if e["performance_tier"] == "High Performer"])
    
    # Win rate analysis
    win_rates = [e["win_rate"] for e in leaderboard if e["total_matches"] > 0]
    avg_win_rate = sum(win_rates) / len(win_rates) if win_rates else 0
    
    return {
        "direction_performance": direction_performance,
        "upset_analysis": {
            "total_upsets": len(upsets),
            "biggest_rating_gains": [
                {
                    "team": entry["team_id"],
                    "direction": entry["research_direction"],
                    "gain": entry["elo_change"],
                    "final_rank": entry["rank"]
                }
                for entry in biggest_upsets
            ],
            "biggest_rating_falls": [
                {
                    "team": entry["team_id"],
                    "direction": entry["research_direction"],
                    "loss": entry["elo_change"],
                    "final_rank": entry["rank"]
                }
                for entry in biggest_falls
            ]
        },
        "performance_distribution": {
            "elite": elite_count,
            "high_performer": high_performer_count,
            "above_average": len([e for e in leaderboard if e["performance_tier"] == "Above Average"]),
            "average": len([e for e in leaderboard if e["performance_tier"] == "Average"]),
            "below_average": len([e for e in leaderboard if e["performance_tier"] == "Below Average"])
        },
        "competition_metrics": {
            "average_win_rate": round(avg_win_rate, 1),
            "total_matches_played": sum(e["total_matches"] for e in leaderboard),
            "most_active_participant": max(leaderboard, key=lambda x: x["total_matches"])["team_id"] if leaderboard else None,
            "highest_volatility": max(leaderboard, key=lambda x: x["rating_volatility"])["team_id"] if leaderboard else None
        }
    } 