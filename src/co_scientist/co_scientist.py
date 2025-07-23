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
    PAIRWISE_RANKING_PROMPT,
    META_REVIEW_PROMPT,
    get_meta_analysis_prompt,
    get_generation_prompt,
    get_pairwise_prompt,
    get_unified_reflection_prompt
)

# Import deep_researcher for research tasks
from open_deep_research.deep_researcher import deep_researcher

# Initialize configurable models
configurable_model = init_chat_model(
    configurable_fields=("model", "max_tokens", "api_key"),
)

# === Elo Rating System ===

class EloTracker:
    """Elo rating system for scenario competitions."""
    
    def __init__(self, k_factor: int = 32):
        """
        Initialize Elo tracker.
        
        Args:
            k_factor: Rating change sensitivity (16=conservative, 32=standard, 64=volatile)
        """
        self.ratings = {}  # scenario_id -> elo_rating
        self.k_factor = k_factor
        self.rating_history = {}  # scenario_id -> list of (timestamp, rating, reason)
        self.default_rating = 1500  # Standard starting Elo rating
    
    def initialize_from_quality(self, scenarios: list, quality_weight: float = 0.6) -> None:
        """
        Initialize Elo ratings based on reflection quality scores.
        
        Args:
            scenarios: List of scenarios with quality_score field
            quality_weight: How much quality influences initial rating (0.0-1.0)
        """
        for scenario in scenarios:
            scenario_id = scenario.get("scenario_id")
            quality_score = scenario.get("quality_score", 50)  # Default neutral quality
            
            if scenario_id:
                # Convert quality score (0-100) to Elo rating adjustment
                # Quality 50 → no adjustment (1500)
                # Quality 100 → +300 points (1800) 
                # Quality 0 → -300 points (1200)
                quality_adjustment = (quality_score - 50) * 6 * quality_weight  # Max ±180 at full weight
                initial_rating = self.default_rating + quality_adjustment
                
                # Keep within reasonable bounds
                initial_rating = max(1200, min(1800, initial_rating))
                
                self.ratings[scenario_id] = initial_rating
                self._record_rating_change(scenario_id, initial_rating, f"Initial rating from quality score {quality_score}")
    
    def get_rating(self, scenario_id: str) -> float:
        """Get current Elo rating for a scenario."""
        return self.ratings.get(scenario_id, self.default_rating)
    
    def update_ratings(self, winner_id: str, loser_id: str, margin: float = 1.0) -> dict:
        """
        Update Elo ratings after a pairwise comparison.
        
        Args:
            winner_id: Scenario ID of the winner
            loser_id: Scenario ID of the loser  
            margin: Victory margin multiplier (for future enhancements)
            
        Returns:
            Dict with rating changes and new ratings
        """
        # Get current ratings
        winner_rating = self.get_rating(winner_id)
        loser_rating = self.get_rating(loser_id)
        
        # Calculate expected scores (probability of winning)
        winner_expected = 1 / (1 + 10**((loser_rating - winner_rating) / 400))
        loser_expected = 1 - winner_expected
        
        # Actual scores (1 for win, 0 for loss)
        winner_actual = 1.0 * margin
        loser_actual = 0.0
        
        # Calculate rating changes
        winner_change = self.k_factor * (winner_actual - winner_expected)
        loser_change = self.k_factor * (loser_actual - loser_expected)
        
        # Update ratings
        new_winner_rating = winner_rating + winner_change
        new_loser_rating = loser_rating + loser_change
        
        self.ratings[winner_id] = new_winner_rating
        self.ratings[loser_id] = new_loser_rating
        
        # Record changes
        self._record_rating_change(winner_id, new_winner_rating, f"Beat {loser_id} (+{winner_change:.1f})")
        self._record_rating_change(loser_id, new_loser_rating, f"Lost to {winner_id} ({loser_change:.1f})")
        
        return {
            "winner_id": winner_id,
            "loser_id": loser_id,
            "winner_rating_before": winner_rating,
            "winner_rating_after": new_winner_rating,
            "winner_change": winner_change,
            "loser_rating_before": loser_rating,
            "loser_rating_after": new_loser_rating,
            "loser_change": loser_change,
            "winner_expected": winner_expected,
            "upset": winner_expected < 0.5  # Underdog victory
        }
    
    def _record_rating_change(self, scenario_id: str, new_rating: float, reason: str) -> None:
        """Record rating change in history."""
        if scenario_id not in self.rating_history:
            self.rating_history[scenario_id] = []
        
        self.rating_history[scenario_id].append({
            "timestamp": datetime.now().isoformat(),
            "rating": new_rating,
            "reason": reason
        })
    
    def get_rating_history(self, scenario_id: str) -> list:
        """Get rating history for a scenario."""
        return self.rating_history.get(scenario_id, [])
    
    def get_leaderboard(self, scenarios: list = None) -> list:
        """
        Get scenarios sorted by Elo rating.
        
        Args:
            scenarios: Optional list to filter ratings by
            
        Returns:
            List of (scenario_id, rating) tuples sorted by rating desc
        """
        if scenarios:
            # Filter to only provided scenarios
            relevant_ratings = {s.get("scenario_id"): self.get_rating(s.get("scenario_id")) 
                              for s in scenarios if s.get("scenario_id")}
        else:
            relevant_ratings = self.ratings
        
        return sorted(relevant_ratings.items(), key=lambda x: x[1], reverse=True)
    
    def get_statistics(self) -> dict:
        """Get Elo rating statistics."""
        if not self.ratings:
            return {"count": 0, "average": 0, "min": 0, "max": 0, "std_dev": 0}
        
        ratings = list(self.ratings.values())
        count = len(ratings)
        average = sum(ratings) / count
        min_rating = min(ratings)
        max_rating = max(ratings)
        
        # Calculate standard deviation
        variance = sum((r - average) ** 2 for r in ratings) / count
        std_dev = variance ** 0.5
        
        return {
            "count": count,
            "average": average,
            "min": min_rating,
            "max": max_rating,
            "std_dev": std_dev,
            "range": max_rating - min_rating
        }

# === Output Management ===

class CoScientistOutputManager:
    """Manages detailed output for co-scientist runs with timestamped directories."""
    
    def __init__(self, base_output_dir: str = "output", phase: str = None):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        phase_suffix = f"_{phase}" if phase else ""
        self.run_dir = Path(base_output_dir) / f"{self.timestamp}_coscientist{phase_suffix}"
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

def get_output_manager(output_dir: str = "output", phase: str = None) -> CoScientistOutputManager:
    """Get or create the output manager for this run."""
    global _output_manager
    if _output_manager is None:
        _output_manager = CoScientistOutputManager(output_dir, phase)
    return _output_manager

def save_co_scientist_output(filename: str, content: str, output_dir: str = "output", phase: str = None):
    """Save co_scientist intermediate results to markdown files."""
    manager = get_output_manager(output_dir, phase)
    numbered_filename = manager.get_next_filename(filename)
    manager.save_file(numbered_filename, content)

def save_individual_scenarios(scenarios: list, output_dir: str = "output", phase: str = None):
    """Save detailed individual scenario files for debugging and analysis."""
    manager = get_output_manager(output_dir, phase)
    
    for scenario in scenarios:
        scenario_id = scenario.get("scenario_id", "unknown")
        direction = scenario.get("research_direction", "Unknown")
        team_id = scenario.get("team_id", "unknown")
        
        content = f"# Scenario: {scenario_id}\n\n"
        content += f"**Direction:** {direction}\n"
        content += f"**Team:** {team_id}\n"
        content += f"**Generated:** {scenario.get('generation_timestamp', 'Unknown')}\n\n"
        content += "## Content\n\n"
        content += scenario.get("scenario_content", "No content available")
        
        # Add quality information if available
        if scenario.get("quality_score"):
            content += f"\n\n## Quality Information\n\n"
            content += f"**Quality Score:** {scenario.get('quality_score', 0)}/100\n"
            content += f"**Advancement Recommendation:** {scenario.get('advancement_recommendation', 'N/A')}\n"
        
        filename = f"scenario_{scenario_id}_{team_id}.md"
        manager.save_file(filename, content, "scenarios")

def save_individual_critiques(critiques: list, output_dir: str = "output", phase: str = None):
    """Save detailed individual critique files for debugging and analysis."""
    manager = get_output_manager(output_dir, phase)
    
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
            
            # Include research query if available
            if 'research_query' in critique:
                content += "## Research Query\n\n"
                content += critique.get('research_query', 'No research query available')
                content += "\n\n"
            
            content += "## Critique Content\n\n"
            content += critique.get('critique_content', 'No critique content available')
            
            # Include raw research result if available
            if 'raw_research_result' in critique:
                content += "\n\n## Raw Research Output\n\n"
                content += critique.get('raw_research_result', 'No raw research result')
            
            filename = f"critique_{critique_counter:03d}_{domain}_{scenario_id[:8]}_sev{severity}.md"
            manager.save_file(filename, content, "critiques")
            critique_counter += 1

def save_individual_tournament_comparisons(all_tournament_data: list, output_dir: str = "output", phase: str = None):
    """Save each tournament comparison individually with full reasoning."""
    manager = get_output_manager(output_dir, phase)
    
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

def save_individual_evolution_attempts(evolutions: list, output_dir: str = "output", phase: str = None):
    """Save each evolution attempt individually with full prompts and reasoning."""
    manager = get_output_manager(output_dir, phase)
    
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
        
        # Include raw research result if available
        if 'raw_research_result' in evolution:
            content += "\n\n## Raw Research Output\n\n"
            content += evolution.get('raw_research_result', 'No raw research result')
        
        filename = f"evolution_{evolution_counter:03d}_{strategy}_{original_scenario_id[:8]}_{evolution_id[:8]}.md"
        manager.save_file(filename, content, "evolution_attempts")
        evolution_counter += 1

def save_tournament_brackets(all_tournament_data: list, output_dir: str = "output", phase: str = None):
    """Save detailed tournament bracket progression for each direction with quality and Elo metrics."""
    manager = get_output_manager(output_dir, phase)
    
    for i, tournament in enumerate(all_tournament_data, 1):
        if not tournament or isinstance(tournament, Exception):
            continue
            
        direction = tournament.get('direction', 'unknown')
        rounds = tournament.get('round_progression', [])
        winner = tournament.get('winner', {})
        elo_tracker = tournament.get('elo_tracker')
        
        content = f"# Tournament Bracket {i}: {direction}\n\n"
        content += f"**Direction:** {direction}\n"
        content += f"**Total Rounds:** {len(rounds)}\n"
        content += f"**Final Winner:** {winner.get('team_id', 'unknown')} ({winner.get('scenario_id', 'unknown')})\n"
        
        # Add final winner quality and Elo info
        if winner.get('quality_score'):
            content += f"**Final Winner Quality:** {winner.get('quality_score', 0)}/100\n"
        if winner.get('elo_rating'):
            content += f"**Final Winner Elo:** {winner.get('elo_rating', 1500):.0f}\n"
        content += "\n"
        
        # Add Elo statistics if available
        if elo_tracker:
            elo_stats = elo_tracker.get_statistics()
            content += f"## Elo Rating Statistics\n\n"
            content += f"**Post-Tournament Elo Statistics:**\n"
            content += f"- Average Rating: {elo_stats['average']:.0f}\n"
            content += f"- Rating Range: {elo_stats['min']:.0f} - {elo_stats['max']:.0f}\n"
            content += f"- Standard Deviation: {elo_stats['std_dev']:.0f}\n"
            content += f"- Total Scenarios: {elo_stats['count']}\n\n"
        
        content += "## Bracket Progression\n\n"
        for round_num, round_data in enumerate(rounds, 1):
            content += f"### Round {round_num}\n\n"
            participants = round_data.get('participants', [])
            winners = round_data.get('winners', [])
            bye_advancements = round_data.get('bye_advancements', [])
            total_advancing = round_data.get('total_advancing', len(winners))
            
            content += f"**Participants:** {len(participants)}\n"
            for participant in participants:
                team_id = participant.get('team_id', 'unknown')
                scenario_id = participant.get('scenario_id', 'unknown')[:8]
                quality_score = participant.get('quality_score', 0)
                elo_rating = participant.get('elo_rating', 1500)
                advancement_rec = participant.get('advancement_recommendation', 'N/A')
                
                content += f"- {team_id} ({scenario_id}) | Quality: {quality_score}/100 | Elo: {elo_rating:.0f} | Rec: {advancement_rec}\n"
            
            content += f"\n**Comparison Winners:** {len(winners)}\n"
            for winner_item in winners:
                team_id = winner_item.get('team_id', 'unknown')
                scenario_id = winner_item.get('scenario_id', 'unknown')[:8]
                quality_score = winner_item.get('quality_score', 0)
                elo_rating = winner_item.get('elo_rating', 1500)
                
                content += f"- {team_id} ({scenario_id}) | Quality: {quality_score}/100 | Elo: {elo_rating:.0f}\n"
                
            if bye_advancements:
                content += f"\n**Bye Advancements:** {len(bye_advancements)}\n"
                for bye_participant in bye_advancements:
                    team_id = bye_participant.get('team_id', 'unknown')
                    scenario_id = bye_participant.get('scenario_id', 'unknown')[:8]
                    quality_score = bye_participant.get('quality_score', 0)
                    elo_rating = bye_participant.get('elo_rating', 1500)
                    
                    content += f"- {team_id} ({scenario_id}) | Quality: {quality_score}/100 | Elo: {elo_rating:.0f} [bye]\n"
            
            content += f"\n**Total Advancing to Next Round:** {total_advancing}\n"
            content += "\n"
        
        content += "## Final Winner Details\n\n"
        content += f"**Team ID:** {winner.get('team_id', 'unknown')}\n"
        content += f"**Scenario ID:** {winner.get('scenario_id', 'unknown')}\n"
        content += f"**Research Direction:** {winner.get('research_direction', 'unknown')}\n"
        
        # Add quality and Elo information for final winner
        quality_score = winner.get('quality_score', 0)
        elo_rating = winner.get('elo_rating', 1500)
        advancement_rec = winner.get('advancement_recommendation', 'N/A')
        
        if quality_score > 0:
            content += f"**Quality Score:** {quality_score}/100\n"
            content += f"**Pre-Tournament Assessment:** {advancement_rec}\n"
            
            # Show dimension breakdown if available
            quality_scores = winner.get('quality_scores', {})
            if quality_scores and len(quality_scores) > 1:
                content += f"**Quality Breakdown:**\n"
                for dimension, score in quality_scores.items():
                    if dimension != "overall_quality_score":
                        dimension_display = dimension.replace('_', ' ').title()
                        content += f"  - {dimension_display}: {score}/100\n"
        
        if elo_rating:
            content += f"**Final Elo Rating:** {elo_rating:.0f}\n"
            
            # Show Elo progression if available
            if elo_tracker:
                rating_history = elo_tracker.get_rating_history(winner.get('scenario_id', ''))
                if len(rating_history) > 1:
                    initial_rating = rating_history[0]['rating']
                    rating_change = elo_rating - initial_rating
                    content += f"**Elo Change:** {rating_change:+.0f} (from {initial_rating:.0f})\n"
        
        content += "\n**Winning Scenario Content:**\n\n"
        content += winner.get('scenario_content', 'No scenario content available')
        
        filename = f"bracket_{i:02d}_{direction.replace(' ', '_')}.md"
        manager.save_file(filename, content, "tournament_brackets")

def save_evolution_tournament_details(evolution_tournaments: list, output_dir: str = "output", phase: str = None):
    """Save detailed evolution tournament comparisons."""
    manager = get_output_manager(output_dir, phase)
    
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

def save_tournament_details(tournaments: list, output_dir: str = "output", phase: str = None):
    """Save detailed tournament results."""
    manager = get_output_manager(output_dir, phase)
    
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

def save_evolution_details(evolutions: list, output_dir: str = "output", phase: str = None):
    """Save detailed evolution results."""
    manager = get_output_manager(output_dir, phase)
    
    evolution_counter = 1
    for evolution in evolutions:
        strategy = evolution.get('strategy', 'unknown')
        original_direction = evolution.get('original_direction', 'unknown')
        
        content = f"# Evolution {evolution_counter:03d}\n\n"
        content += f"**Strategy:** {strategy}\n"
        content += f"**Original Direction:** {original_direction}\n"
        content += f"**Generated:** {datetime.now().isoformat()}\n\n"
        
        content += "## Original Scenario\n\n"
        content += evolution.get('original_scenario_content', 'No original scenario')
        
        content += "\n\n## Evolution Prompt\n\n"
        content += evolution.get('evolution_prompt', 'No evolution prompt')
        
        content += "\n\n## Evolved Content\n\n"
        content += evolution.get('evolved_content', 'No evolved content')
        
        filename = f"evolution_{evolution_counter:03d}_{strategy}_{original_direction.replace(' ', '_')}.md"
        manager.save_file(filename, content, "evolutions")
        evolution_counter += 1

async def meta_analysis_phase(state: CoScientistInputState, config: RunnableConfig) -> dict:
    """Meta-analysis to identify distinct approaches for competition."""
    
    configuration = CoScientistConfiguration.from_runnable_config(config)
    
    # Configure model for meta-analysis
    model = configurable_model.with_config(
        configurable={
            "model": configuration.research_model,
            "max_tokens": 4096,
        }
    )
    
    # Handle backward compatibility - convert old format to new format
    processed_state = {}
    if state.get("research_context"):
        # Legacy scenario generation format
        processed_state.update({
            "task_description": f"Generate scenarios for {state.get('target_year', 'future')}",
            "context": state["research_context"],
            "storyline": state.get("storyline", ""),
            "target_year": state.get("target_year"),
            "baseline_world_state": state.get("baseline_world_state"),
            "years_in_future": state.get("years_in_future"),
            "use_case": "scenario_generation"
        })
    else:
        # New flexible format
        processed_state.update(state)
    
    # Get use case from state or configuration
    use_case = processed_state.get("use_case", configuration.use_case.value)
    
    # Choose appropriate meta-analysis prompt
    if use_case == "scenario_generation" and processed_state.get("baseline_world_state") and processed_state.get("years_in_future"):
        # Use incremental prompt for scenario generation with baseline
        meta_prompt = INCREMENTAL_META_ANALYSIS_PROMPT.format(
            storyline=processed_state.get("storyline", ""),
            world_building_questions=processed_state.get("context", processed_state.get("research_context", "")),
            baseline_world_state=processed_state["baseline_world_state"],
            years_in_future=processed_state["years_in_future"]
        )
    else:
        # Use flexible template system
        meta_prompt = get_meta_analysis_prompt(use_case, processed_state, config)
    
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
        save_co_scientist_output("meta_analysis.md", response.content, configuration.output_dir, configuration.phase)
    
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
    """Generate content in parallel for each direction."""
    
    configuration = CoScientistConfiguration.from_runnable_config(config)
    
    # Create tasks for parallel generation
    generation_tasks = []
    
    scenarios_per_direction = configuration.get_scenarios_per_direction()
    use_case_config = configuration.get_use_case_config()
    output_name = use_case_config.get("output_name", "scenarios")
    
    print(f"Starting {output_name} generation: {len(state['research_directions'])} directions, {scenarios_per_direction} items per direction")
    
    try:
        for direction_idx, direction in enumerate(state["research_directions"]):
            print(f"Processing direction {direction_idx}: {direction.get('name', 'Unknown')}")
            # Create multiple research teams per direction
            for team_idx in range(scenarios_per_direction):
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
                # Log the full exception details
                import traceback
                print(f"Full exception traceback for task {i}:")
                print(traceback.format_exception(type(scenario), scenario, scenario.__traceback__))
            else:
                valid_scenarios.append(scenario)
        
        # Log results
        print(f"Scenario generation complete: {len(valid_scenarios)} successful, {len(failed_scenarios)} failed")
        if failed_scenarios:
            print("Failed scenarios:", failed_scenarios)
        
    except Exception as e:
        print(f"Critical error in parallel_scenario_generation: {e}")
        import traceback
        print(f"Full traceback:")
        print(traceback.format_exc())
        # Return minimal valid state to prevent total failure
        valid_scenarios = []
    
    # Save scenario generation results
    if configuration.save_intermediate_results:
        # Save individual scenarios with full content
        save_individual_scenarios(valid_scenarios, configuration.output_dir, configuration.phase)
        
        # Save raw JSON data for debugging
        manager = get_output_manager(configuration.output_dir)
        manager.save_json("scenarios_raw_data.json", {"scenarios": valid_scenarios}, "raw_data")
        
        # Save summary
        scenario_content = format_scenario_population(valid_scenarios)
        save_co_scientist_output("scenario_population_summary.md", scenario_content, configuration.output_dir, configuration.phase)
    
    return {
        "scenario_population": valid_scenarios,
        "generation_complete": True
    }

async def generate_single_scenario(direction: dict, team_id: str, state: CoScientistState, config: RunnableConfig) -> dict:
    """Generate a single content item using deep research."""
    
    configuration = CoScientistConfiguration.from_runnable_config(config)
    use_case_config = configuration.get_use_case_config()
    output_name = use_case_config.get("output_name", "scenarios")
    
    print(f"Generating {output_name.rstrip('s')} for {team_id} in direction: {direction.get('name', 'Unknown')}")
    
    try:
        # Handle backward compatibility - convert old format to new format
        processed_state = {}
        if state.get("research_context"):
            # Legacy scenario generation format
            processed_state.update({
                "task_description": f"Generate scenarios for {state.get('target_year', 'future')}",
                "context": state["research_context"],
                "storyline": state.get("storyline", ""),
                "target_year": state.get("target_year"),
                "baseline_world_state": state.get("baseline_world_state"),
                "years_in_future": state.get("years_in_future"),
                "use_case": "scenario_generation"
            })
        else:
            # New flexible format
            processed_state.update(state)
        
        # Get use case from state or configuration
        use_case = processed_state.get("use_case", configuration.use_case.value)
        
        print(f"Debug - generate_single_scenario for {team_id}:")
        print(f"  use_case: {use_case}")
        print(f"  direction keys: {list(direction.keys()) if direction else 'None'}")
        print(f"  direction name: {direction.get('name', 'MISSING')}")
        print(f"  direction assumption: {direction.get('assumption', 'MISSING')}")
        print(f"  processed_state keys: {list(processed_state.keys())}")
        
        # Choose appropriate generation prompt
        if use_case == "scenario_generation" and processed_state.get("baseline_world_state") and processed_state.get("years_in_future"):
            # Use incremental prompt for scenario generation with baseline
            try:
                research_query = INCREMENTAL_SCENARIO_GENERATION_PROMPT.format(
                    research_direction=direction.get("name", ""),
                    core_assumption=direction.get("assumption", ""),
                    team_id=team_id,
                    research_context=processed_state.get("context", processed_state.get("research_context", "")),
                    storyline=processed_state.get("storyline", ""),
                    baseline_world_state=processed_state["baseline_world_state"],
                    years_in_future=processed_state["years_in_future"]
                )
                print(f"Successfully formatted incremental prompt for {team_id}")
            except KeyError as e:
                print(f"KeyError in incremental prompt formatting for {team_id}: {e}")
                print(f"Available keys in processed_state: {list(processed_state.keys())}")
                raise e
            except Exception as e:
                print(f"Error formatting incremental prompt for {team_id}: {e}")
                raise e
        else:
            # Use flexible template system
            try:
                research_query = get_generation_prompt(use_case, processed_state, direction, team_id, config)
                print(f"Successfully got generation prompt for {team_id} using flexible system")
            except Exception as e:
                print(f"Error getting generation prompt for {team_id}: {e}")
                print(f"  use_case: {use_case}")
                print(f"  processed_state keys: {list(processed_state.keys())}")
                print(f"  direction: {direction}")
                print(f"  config type: {type(config)}")
                raise e
        
    except Exception as e:
        print(f"Error in prompt preparation for {team_id}: {e}")
        import traceback
        print(f"Full traceback:")
        print(traceback.format_exc())
        raise e
    
    # Use either deep_researcher or regular LLM based on configuration
    co_config = CoScientistConfiguration.from_runnable_config(config)
    
    if co_config.use_deep_researcher:
        # Use deep_researcher for research-based generation
        research_config = config.copy()
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
            scenario_content = research_result.get("final_report", "")
            raw_result = str(research_result)
            print(f"Successfully generated content for {team_id} using deep_researcher, length: {len(scenario_content)}")
        except Exception as e:
            print(f"Failed to generate content for {team_id} using deep_researcher: {e}")
            import traceback
            print(f"Deep researcher failure traceback:")
            print(traceback.format_exc())
            raise e
    else:
        # Use regular LLM for creative generation
        model = configurable_model.with_config(
            configurable={
                "model": co_config.general_model,
                "max_tokens": 8000,
            }
        )
        
        try:
            response = await model.ainvoke([HumanMessage(content=research_query)])
            scenario_content = response.content
            raw_result = f"Direct LLM response: {response.content}"
            print(f"Successfully generated content for {team_id} using direct LLM, length: {len(scenario_content)}")
        except Exception as e:
            print(f"Failed to generate content for {team_id} using direct LLM: {e}")
            import traceback
            print(f"Direct LLM failure traceback:")
            print(traceback.format_exc())
            raise e
    
    return {
        "scenario_id": str(uuid.uuid4()),
        "team_id": team_id,
        "research_direction": direction.get("name", ""),
        "core_assumption": direction.get("assumption", ""),
        "scenario_content": scenario_content,
        "research_query": research_query,
        "raw_research_result": raw_result,
        "generation_timestamp": datetime.now().isoformat(),
        "quality_score": None,
        "critiques": []
    }

async def reflection_phase(state: CoScientistState, config: RunnableConfig) -> dict:
    """Conduct unified reflection/critique of all scenarios."""
    
    configuration = CoScientistConfiguration.from_runnable_config(config)
    
    # Check if we have any scenarios to critique
    scenario_population = state.get("scenario_population", [])
    if not scenario_population:
        print("No scenarios available for reflection - returning empty results")
        return {
            "reflection_critiques": [],
            "reflection_complete": True
        }
    
    # Create unified reflection tasks - one per scenario instead of multiple per domain
    reflection_tasks = []
    
    print(f"Starting unified reflection for {len(scenario_population)} scenarios")
    
    for scenario in scenario_population:
        # Create one comprehensive reflection task per scenario
        task = generate_unified_reflection(
            scenario=scenario,
            config=config
        )
        reflection_tasks.append(task)
    
    print(f"Created {len(reflection_tasks)} unified reflection tasks")
    
    # Execute all reflections in parallel
    reflection_results = await asyncio.gather(*reflection_tasks, return_exceptions=True)
    
    # Filter valid critiques and log results
    valid_critiques = []
    failed_critiques = []
    
    for i, critique in enumerate(reflection_results):
        if isinstance(critique, Exception):
            failed_critiques.append(f"Task {i}: {str(critique)}")
            print(f"Unified reflection failed for task {i}: {critique}")
        else:
            valid_critiques.append(critique)
    
    print(f"Unified reflection complete: {len(valid_critiques)} successful, {len(failed_critiques)} failed")
    
    # Save reflection results
    if configuration.save_intermediate_results:
        # Save individual critiques with full content
        save_individual_critiques(valid_critiques, configuration.output_dir, configuration.phase)
        
        # Save raw JSON data for debugging
        manager = get_output_manager(configuration.output_dir, configuration.phase)
        manager.save_json("unified_critiques_raw_data.json", {"critiques": valid_critiques}, "raw_data")
        
        # Save summary with quality scores
        critique_content = format_unified_reflection_critiques(valid_critiques)
        save_co_scientist_output("unified_reflection_summary.md", critique_content, configuration.output_dir, configuration.phase)
    
    return {
        "reflection_critiques": valid_critiques,
        "reflection_complete": True
    }

async def generate_unified_reflection(scenario: dict, config: RunnableConfig) -> dict:
    """Generate unified comprehensive reflection with quality scoring."""
    
    configuration = CoScientistConfiguration.from_runnable_config(config)
    
    # Get scenario information with defaults for missing fields
    scenario_id = scenario.get("scenario_id", f"missing_id_{uuid.uuid4().hex[:8]}")
    research_direction = scenario.get("research_direction", "Unknown Direction")
    scenario_content = scenario.get("scenario_content", "No scenario content available")
    
    # Get use case from configuration
    use_case = configuration.use_case.value if hasattr(configuration.use_case, 'value') else str(configuration.use_case)
    
    # Get appropriate unified prompt for this use case
    unified_prompt_template = get_unified_reflection_prompt(use_case)
    
    # Configure model for reflection
    model = configurable_model.with_config(
        configurable={
            "model": configuration.general_model,
            "max_tokens": 4096,
        }
    )
    
    # Format the unified reflection prompt
    reflection_prompt = unified_prompt_template.format(
        scenario_id=scenario_id,
        research_direction=research_direction,
        scenario_content=scenario_content
    )
    
    try:
        # Generate unified reflection
        response = await model.ainvoke([HumanMessage(content=reflection_prompt)])
        reflection_content = response.content
        
        # Parse quality scores from the reflection
        quality_scores = parse_quality_scores(reflection_content)
        overall_score = quality_scores.get("overall_quality_score", 50)
        
        # Parse advancement recommendation
        advancement_recommendation = parse_advancement_recommendation(reflection_content)
        
        return {
            "critique_id": f"unified_{uuid.uuid4().hex[:8]}",
            "target_scenario_id": scenario_id,
            "critique_domain": "unified_reflection",
            "critique_content": reflection_content,
            "quality_scores": quality_scores,
            "overall_quality_score": overall_score,
            "advancement_recommendation": advancement_recommendation,
            "severity_score": max(1, 11 - (overall_score // 10))  # Convert 1-100 to 10-1 severity scale
        }
        
    except Exception as e:
        print(f"Error in unified reflection for scenario {scenario_id}: {e}")
        return {
            "critique_id": f"error_{uuid.uuid4().hex[:8]}",
            "target_scenario_id": scenario_id,
            "critique_domain": "unified_reflection",
            "critique_content": f"Error generating reflection: {str(e)}",
            "quality_scores": {},
            "overall_quality_score": 25,  # Low default score for errors
            "advancement_recommendation": "REVISE",
            "severity_score": 8
        }

def parse_quality_scores(reflection_content: str) -> dict:
    """Parse quality scores from unified reflection output."""
    import re
    
    quality_scores = {}
    
    # Extract overall quality score
    overall_match = re.search(r'\*\*Overall Quality Score:\s*(\d+)/100\*\*', reflection_content)
    if overall_match:
        quality_scores["overall_quality_score"] = int(overall_match.group(1))
    
    # Extract individual dimension scores (flexible patterns for different use cases)
    score_patterns = [
        r'- ([^:]+):\s*(\d+)/100',
        r'\*\*([^:]+)\*\*\s*\(1-100\):\s*(\d+)',
        r'(\w+(?:\s+\w+)*):\s*(\d+)/100'
    ]
    
    for pattern in score_patterns:
        matches = re.findall(pattern, reflection_content)
        for match in matches:
            dimension_name = match[0].strip().lower().replace(' ', '_')
            score = int(match[1])
            quality_scores[dimension_name] = score
    
    return quality_scores

def parse_advancement_recommendation(reflection_content: str) -> str:
    """Parse advancement recommendation from unified reflection output."""
    import re
    
    # Look for advancement recommendation
    advancement_match = re.search(r'\*\*Advancement Recommendation:\*\*\s*(\w+)', reflection_content)
    if advancement_match:
        return advancement_match.group(1).upper()
    
    # Fallback: look for ADVANCE/REVISE/REJECT anywhere in text
    if 'ADVANCE' in reflection_content.upper():
        return "ADVANCE"
    elif 'REJECT' in reflection_content.upper():
        return "REJECT"
    else:
        return "REVISE"

def integrate_quality_scores(scenarios: list, reflection_critiques: list) -> list:
    """Integrate quality scores from reflection critiques into scenario data."""
    
    # Create a mapping from scenario_id to quality data
    quality_mapping = {}
    for critique in reflection_critiques:
        scenario_id = critique.get("target_scenario_id")
        if scenario_id:
            quality_mapping[scenario_id] = {
                "quality_score": critique.get("overall_quality_score", 50),
                "quality_scores": critique.get("quality_scores", {}),
                "advancement_recommendation": critique.get("advancement_recommendation", "REVISE"),
                "critique_summary": critique.get("critique_content", "")[:200] + "..." if len(critique.get("critique_content", "")) > 200 else critique.get("critique_content", "")
            }
    
    # Attach quality data to scenarios
    enhanced_scenarios = []
    for scenario in scenarios:
        scenario_id = scenario.get("scenario_id")
        enhanced_scenario = scenario.copy()
        
        if scenario_id in quality_mapping:
            # Attach quality data from reflection
            quality_data = quality_mapping[scenario_id]
            enhanced_scenario.update(quality_data)
        else:
            # Default quality data for scenarios without reflection
            enhanced_scenario.update({
                "quality_score": 50,  # Default neutral score
                "quality_scores": {},
                "advancement_recommendation": "REVISE",
                "critique_summary": "No reflection critique available"
            })
        
        enhanced_scenarios.append(enhanced_scenario)
    
    return enhanced_scenarios

async def tournament_phase(state: CoScientistState, config: RunnableConfig) -> dict:
    """Run tournament brackets for each research direction with quality-based seeding and Elo ratings."""
    
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
        task = run_direction_tournament(direction, scenarios, config, elo_tracker)
        tournament_tasks.append(task)
    
    try:
        tournament_results = await asyncio.gather(*tournament_tasks, return_exceptions=True)
        
        print(f"Tournament results gathered: {len(tournament_results)} results")
        for i, result in enumerate(tournament_results):
            if isinstance(result, Exception):
                print(f"Tournament {i} failed with exception: {result}")
                import traceback
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
        import traceback
        print(f"Tournament execution traceback:")
        print(traceback.format_exc())
        direction_winners = []
    
    # Collect final Elo statistics
    if direction_winners:
        # Use the Elo tracker from the first tournament (they should all be the same instance)
        final_elo_tracker = None
        for winner in direction_winners:
            if winner.get("elo_tracker"):
                final_elo_tracker = winner["elo_tracker"]
                break
        
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
        # Save individual tournament comparisons with full reasoning and Elo data
        save_individual_tournament_comparisons(direction_winners, configuration.output_dir, configuration.phase)
        
        # Save tournament bracket progressions with Elo information
        save_tournament_brackets(direction_winners, configuration.output_dir, configuration.phase)
        
        # Save individual tournament details (existing function)
        save_tournament_details(direction_winners, configuration.output_dir, configuration.phase)
        
        # Save raw JSON data for debugging (including Elo data)
        manager = get_output_manager(configuration.output_dir, configuration.phase)
        manager.save_json("tournaments_raw_data.json", {"tournaments": direction_winners}, "raw_data")
        
        # Save Elo rating data and statistics
        if final_elo_tracker:
            elo_export = {
                "final_ratings": final_elo_tracker.ratings,
                "rating_history": final_elo_tracker.rating_history,
                "statistics": final_elo_tracker.get_statistics(),
                "leaderboard": final_elo_tracker.get_leaderboard()
            }
            manager.save_json("elo_ratings.json", elo_export, "raw_data")
        
        # Save summary with Elo information
        tournament_content = format_tournament_results(direction_winners, tournament_results)
        save_co_scientist_output("tournament_results_summary.md", tournament_content, configuration.output_dir, configuration.phase)
    
    
    return {
        "tournament_rounds": tournament_results,
        "tournament_winners": direction_winners,
        "tournament_complete": True,
        "elo_tracker": final_elo_tracker  # Include final Elo tracker in state
    }

async def run_direction_tournament(direction: str, scenarios: list, config: RunnableConfig, elo_tracker: EloTracker) -> dict:
    """Run tournament bracket for a single direction with Elo rating updates."""
    
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
                    config,
                    elo_tracker  # Pass Elo tracker to each comparison
                )
                comparison_tasks.append(task)
            else:
                # Odd number of scenarios, this one advances automatically
                next_round.append(current_round[i])
        
        # Execute all comparisons for this round in parallel
        round_results = await asyncio.gather(*comparison_tasks, return_exceptions=True)
        
        # Collect winners and store comparison data
        round_winners = []
        for i, result in enumerate(round_results):
            if isinstance(result, Exception):
                print(f"Warning: Comparison {i} failed with exception: {result}")
            elif not result:
                print(f"Warning: Comparison {i} returned empty result")
            else:
                winner = result.get("winner")
                if winner:
                    # Update winner with latest Elo rating
                    winner_id = winner.get("scenario_id")
                    if winner_id:
                        winner["elo_rating"] = elo_tracker.get_rating(winner_id)
                    
                    next_round.append(winner)
                    round_winners.append(winner)
                    all_comparisons.append(result)
                else:
                    print(f"Warning: Round {round_number}, comparison {i}: no winner in result")
        
        # Store round progression
        round_progression.append({
            "round": round_number,
            "participants": round_participants,
            "winners": round_winners,
            "bye_advancements": [p for p in next_round if p not in round_winners] if len(current_round) % 2 == 1 else [],
            "total_advancing": len(next_round),
            "comparisons_count": len([r for r in round_results if not isinstance(r, Exception)])
        })
        
        current_round = next_round
        round_number += 1
    
    final_winner = current_round[0] if current_round else None
    
    # Update final winner with latest Elo rating
    if final_winner:
        winner_id = final_winner.get("scenario_id")
        if winner_id:
            final_winner["elo_rating"] = elo_tracker.get_rating(winner_id)
    
    return {
        "direction": direction,
        "winner": final_winner,
        "total_rounds": round_number - 1,
        "all_comparisons": all_comparisons,
        "round_progression": round_progression,
        "elo_tracker": elo_tracker  # Include Elo tracker in results
    }

async def pairwise_comparison(scenario1: dict, scenario2: dict, round_number: int, config: RunnableConfig, elo_tracker: EloTracker) -> dict:
    """Compare two scenarios head-to-head with Elo rating updates."""
    
    configuration = CoScientistConfiguration.from_runnable_config(config)
    
    model = configurable_model.with_config(
        configurable={
            "model": configuration.general_model,
            "max_tokens": 3072,
        }
    )
    
    # Get pre-comparison Elo ratings
    scenario1_id = scenario1["scenario_id"]
    scenario2_id = scenario2["scenario_id"]
    scenario1_elo_before = elo_tracker.get_rating(scenario1_id)
    scenario2_elo_before = elo_tracker.get_rating(scenario2_id)
    
    # Get the appropriate prompt for this use case
    use_case = configuration.use_case.value if hasattr(configuration.use_case, 'value') else str(configuration.use_case)
    pairwise_prompt_template = get_pairwise_prompt(use_case)
    
    comparison_prompt = pairwise_prompt_template.format(
        scenario1_content=scenario1["scenario_content"],
        direction1=scenario1["research_direction"],
        scenario2_content=scenario2["scenario_content"],
        direction2=scenario2["research_direction"]
    )
    
    response = await model.ainvoke([HumanMessage(content=comparison_prompt)])
    
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
    evolution_strategies = configuration.get_evolution_strategies()
    
    for winner in winners:
        for strategy in evolution_strategies:
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
        save_individual_evolution_attempts(evolved_scenarios, configuration.output_dir, configuration.phase)
        
        # Save individual evolution details (existing function)
        save_evolution_details(evolved_scenarios, configuration.output_dir, configuration.phase)
        
        # Save raw JSON data for debugging
        manager = get_output_manager(configuration.output_dir, configuration.phase)
        manager.save_json("evolutions_raw_data.json", {"evolutions": evolved_scenarios}, "raw_data")
        
        # Save summary
        evolution_content = format_evolution_results(evolved_scenarios)
        save_co_scientist_output("evolution_results_summary.md", evolution_content, configuration.output_dir, configuration.phase)
    
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
        save_evolution_tournament_details(evolution_results, configuration.output_dir, configuration.phase)
        
        # Save raw JSON data for debugging
        manager = get_output_manager(configuration.output_dir, configuration.phase)
        manager.save_json("evolution_tournaments_raw_data.json", {"evolution_tournaments": evolution_results}, "raw_data")
        
        # Save summary
        tournament_content = format_evolution_tournament_results(final_representatives)
        save_co_scientist_output("evolution_tournaments_summary.md", tournament_content, configuration.output_dir, configuration.phase)
    
    return {
        "evolution_tournament_results": evolution_results,
        "final_representatives": final_representatives,
        "evolution_tournament_complete": True
    }

async def evolve_scenario(scenario: dict, strategy: str, state: CoScientistState, config: RunnableConfig) -> dict:
    """Evolve a single scenario using specified strategy with deep research."""
    
    configuration = CoScientistConfiguration.from_runnable_config(config)
    
    # Collect critiques and competing scenarios as needed
    critique_summary = ""
    competing_scenarios = ""
    
    # ALWAYS get critiques for evolution - critical for improvement
    critique_summary = get_critique_summary(scenario["scenario_id"], state["reflection_critiques"])
    
    if strategy in ["creativity", "synthesis"]:
        competing_scenarios = get_competing_scenarios(scenario, state["scenario_population"])
    
    # Create research query based on evolution strategy
    if strategy == "feasibility":
        research_query = f"""Conduct deep research to improve the scientific feasibility and realism of this sci-fi scenario.

Original Scenario: {scenario["scenario_content"]}
Research Direction: {scenario["research_direction"]}
Expert Critiques Identified: {critique_summary}

Research Tasks:
1. Investigate current scientific literature relevant to the technologies mentioned
2. Research recent breakthroughs that could support the scenario's assumptions
3. Find evidence for realistic implementation timelines and pathways
4. Research current technical limitations and how they might be overcome
5. Look up cutting-edge research that addresses the identified critiques

Evolution Goals:
- Address specific scientific critiques with evidence-based solutions
- Strengthen technological feasibility using current research trends
- Improve timeline realism based on actual development trajectories
- Enhance internal consistency across technological systems
- Provide specific implementation details supported by research

Research-Based Improvements:
- Cite recent scientific papers or technological developments
- Explain how current trends enable the proposed future
- Address potential obstacles with realistic, research-backed solutions
- Provide more specific technical implementation details

Generate an improved, more scientifically grounded version of the scenario."""

    elif strategy == "creativity":
        research_query = f"""Conduct research to creatively enhance this scenario with novel approaches while addressing expert critiques.

Original Scenario: {scenario["scenario_content"]}
Research Direction: {scenario["research_direction"]}
Expert Critiques to Address: {critique_summary}
Inspiration from Competing Approaches: {competing_scenarios}

Research Tasks:
1. Investigate emerging technologies and research frontiers in relevant fields
2. Research novel approaches and paradigm shifts that address the identified critiques
3. Find interdisciplinary research that could inspire creative solutions to critique issues
4. Look up recent breakthroughs that open new possibilities while maintaining rigor
5. Research unconventional applications that could enhance creativity without sacrificing quality

Creative Enhancement Goals:
- Discover emerging research that suggests new directions while addressing critiques
- Find novel interdisciplinary approaches that enhance the scenario and resolve issues
- Research cutting-edge developments that inspire creative additions and improvements
- Identify breakthrough technologies that could transform the narrative positively

Generate a creatively enhanced version that incorporates both innovative ideas and addresses expert feedback."""

    elif strategy == "synthesis":
        research_query = f"""Conduct comprehensive research to synthesize the best elements while addressing critiques.

Original Scenario: {scenario["scenario_content"]}
Research Direction: {scenario["research_direction"]}
Expert Critiques: {critique_summary}
Alternative Approaches: {competing_scenarios}

Research Tasks:
1. Research solutions that address expert critiques while maintaining innovation
2. Investigate how competing approaches could be integrated scientifically
3. Find evidence for the most promising technological pathways
4. Research interdisciplinary solutions that combine different approaches
5. Look up recent developments that bridge different technological paradigms

Synthesis Goals:
- Research evidence to address scientific critiques effectively
- Find ways to integrate strengths from competing scenarios
- Research technological convergence points for different approaches
- Discover scientific bridges between different technological paradigms

Generate a synthesized scenario that combines the best research-backed elements."""

    # Handle narrative evolution strategies with appropriate prompts
    elif strategy in ["narrative_enhancement", "world_integration", "character_consistency", "thematic_depth", 
                      "character_depth", "narrative_flow", "prose_enhancement", "structural_improvement"]:
        research_query = f"""Enhance this narrative content using the {strategy} approach while addressing expert critiques.

Original Content: {scenario["scenario_content"]}
Content Direction: {scenario["research_direction"]}
Expert Critiques to Address: {critique_summary}

Enhancement Focus: {strategy}

Task: Apply {strategy} improvements while directly addressing the expert feedback provided. Focus on resolving identified issues and strengthening the content according to the critique guidance.

Strategy-Specific Goals:
- narrative_enhancement: Improve story flow, pacing, and narrative structure based on critique feedback
- world_integration: Better integrate world-building elements and ensure consistency with established world state
- character_consistency: Strengthen character development and ensure authentic behavior within world constraints
- thematic_depth: Deepen thematic elements and ensure coherent thematic progression
- character_depth: Develop more complex, authentic character psychology and relationships
- narrative_flow: Improve pacing, transitions, and overall story progression
- prose_enhancement: Strengthen writing quality, voice, and stylistic elements
- structural_improvement: Optimize chapter structure, scene organization, and narrative architecture

Generate an improved version that specifically addresses the expert critiques while enhancing the {strategy} aspects."""

    else:
        # Default to detail enhancement with critique-informed research
        research_query = f"""Conduct research to add depth and technical detail while addressing expert critiques.

Original Scenario: {scenario["scenario_content"]}
Research Direction: {scenario["research_direction"]}
Expert Critiques to Address: {critique_summary}

Research Tasks:
1. Research specific technical details that address identified critique issues
2. Investigate current research on implementation challenges highlighted in critiques
3. Find evidence for detailed specifications that resolve technical concerns
4. Research infrastructure requirements and pathways that address feasibility issues
5. Look up recent developments that add realistic detail and resolve critique points

Enhancement Goals:
- Add research-backed technical specifications that address critique concerns
- Include realistic infrastructure details that resolve identified issues
- Provide evidence-based parameters that address feasibility critiques
- Add scientific depth that directly responds to expert feedback

Generate a more detailed and technically rich version that addresses all expert critiques."""

    # Use appropriate model for evolution based on strategy type
    co_config = CoScientistConfiguration.from_runnable_config(config)
    
    # Narrative evolution strategies use regular LLM for creative writing
    if strategy in ["narrative_enhancement", "world_integration", "character_consistency", "thematic_depth", 
                    "character_depth", "narrative_flow", "prose_enhancement", "structural_improvement"]:
        
        model = configurable_model.with_config(
            configurable={
                "model": co_config.general_model,
                "max_tokens": 4096,
            }
        )
        
        try:
            response = await model.ainvoke([HumanMessage(content=research_query)])
            evolved_content = response.content
            print(f"Successfully evolved content {scenario['scenario_id']} using {strategy} narrative strategy, content length: {len(evolved_content)}")
        except Exception as e:
            print(f"Failed to evolve content {scenario['scenario_id']} with {strategy}: {e}")
            evolved_content = f"Narrative evolution failed for {strategy} strategy on content {scenario['scenario_id']}. Error: {str(e)}"
            
        research_result = {"final_report": evolved_content}  # For consistency with deep_researcher format
    
    else:
        # Research evolution strategies use deep_researcher for scientific analysis
        research_config = config.copy()
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
            evolved_content = research_result.get("final_report", "No evolution results available")
            print(f"Successfully evolved scenario {scenario['scenario_id']} using {strategy} research strategy, content length: {len(evolved_content)}")
        except Exception as e:
            print(f"Failed to evolve scenario {scenario['scenario_id']} with {strategy}: {e}")
            # Fallback to basic evolution without research
            evolved_content = f"Research evolution failed for {strategy} strategy on scenario {scenario['scenario_id']}. Error: {str(e)}"
    
    return {
        "evolution_id": str(uuid.uuid4()),
        "original_scenario_id": scenario["scenario_id"],
        "original_scenario_content": scenario["scenario_content"],
        "evolution_prompt": research_query,
        "strategy": strategy,
        "evolved_content": evolved_content,
        "original_direction": scenario["research_direction"],
        "critique_summary": critique_summary,
        "competing_scenarios": competing_scenarios if competing_scenarios else "",
        "raw_research_result": str(research_result) if 'research_result' in locals() else "No research result",
        "timestamp": datetime.now().isoformat()
    }

async def final_meta_review_phase(state: CoScientistState, config: RunnableConfig) -> dict:
    """Meta-review agent: synthesize insights from competition process for optimization."""
    
    configuration = CoScientistConfiguration.from_runnable_config(config)
    
    
    # Get direction winners (not final representatives)
    tournament_winners = state.get("tournament_winners", [])
    direction_winners = []
    
    # Extract all direction winners (up to number of research directions)
    for i, tournament_result in enumerate(tournament_winners):
        winner = tournament_result.get("winner", {})
        if winner:
            direction_winners.append({
                "scenario_id": winner.get("scenario_id", f"direction_{i}_winner"),
                "research_direction": winner.get("research_direction", "Unknown"),
                "scenario_content": winner.get("scenario_content", ""),
                "core_assumption": winner.get("core_assumption", ""),
                "team_id": winner.get("team_id", ""),
                "quality_score": winner.get("quality_score", 0),
                "quality_scores": winner.get("quality_scores", {}),
                "advancement_recommendation": winner.get("advancement_recommendation", "N/A"),
                "competition_rank": i + 1,
                "selection_reasoning": f"Tournament winner from {winner.get('research_direction', 'unknown')} direction"
            })
    
    if not direction_winners:
        print("No direction winners available for meta-review - generating process analysis with available data")
        return {
            "direction_winners": [],
            "process_analysis": "Competition completed but no direction winners were identified.",
            "competition_summary": "Process analysis: No winners to analyze."
        }
    
    model = configurable_model.with_config(
        configurable={
            "model": configuration.research_model,
            "max_tokens": 4096,
        }
    )
    
    # Prepare competition process data for meta-analysis
    tournament_data = format_tournament_analysis(state.get("tournament_comparisons", []))
    reflection_data = format_reflection_analysis(state.get("reflection_critiques", []))
    evolution_data = format_evolution_analysis(state.get("evolved_scenarios", []))
    
    # Format direction winners summary dynamically
    direction_winners_summary = ""
    quality_scores = []
    
    for i, winner in enumerate(direction_winners, 1):
        direction_winners_summary += f"Direction {i} Winner: {winner.get('research_direction', 'Unknown')}\n"
        direction_winners_summary += f"  - Core Assumption: {winner.get('core_assumption', 'N/A')}\n"
        direction_winners_summary += f"  - Team: {winner.get('team_id', 'Unknown')}\n"
        
        # Add quality metrics
        quality_score = winner.get('quality_score', 0)
        advancement_rec = winner.get('advancement_recommendation', 'N/A')
        if quality_score > 0:
            direction_winners_summary += f"  - Quality Score: {quality_score}/100\n"
            direction_winners_summary += f"  - Pre-Tournament Assessment: {advancement_rec}\n"
            quality_scores.append(quality_score)
        
        direction_winners_summary += "\n"
    
    if not direction_winners_summary:
        direction_winners_summary = "No direction winners available.\n"
    else:
        # Add overall quality statistics
        if quality_scores:
            avg_quality = sum(quality_scores) / len(quality_scores)
            direction_winners_summary += f"Overall Quality Statistics:\n"
            direction_winners_summary += f"  - Average Winner Quality: {avg_quality:.1f}/100\n"
            direction_winners_summary += f"  - Quality Range: {min(quality_scores)}-{max(quality_scores)}/100\n"
            direction_winners_summary += f"  - Total Winners with Quality Data: {len(quality_scores)}\n\n"

    # Use the new process-focused meta review prompt
    meta_review_prompt = META_REVIEW_PROMPT.format(
        competition_summary=format_competition_process_summary(state),
        direction_winners_summary=direction_winners_summary,
        tournament_data=tournament_data,
        reflection_data=reflection_data,
        evolution_data=evolution_data
    )
    
    response = await model.ainvoke([HumanMessage(content=meta_review_prompt)])
    process_analysis = response.content
    
    # Generate a brief competition summary for user presentation
    competition_summary = generate_user_competition_summary(state, direction_winners)
    
    # Save meta-review results
    if configuration.save_intermediate_results:
        save_co_scientist_output("meta_review_process_analysis.md", process_analysis, configuration.output_dir, configuration.phase)
        save_co_scientist_output("competition_summary.md", competition_summary, configuration.output_dir, configuration.phase)
    
    
    return {
        "direction_winners": direction_winners,
        "process_analysis": process_analysis,
        "competition_summary": competition_summary
    }

def format_tournament_analysis(tournament_comparisons: list) -> str:
    """Format tournament comparison data for meta-analysis."""
    if not tournament_comparisons:
        return "No tournament comparisons available."
    
    analysis = f"Tournament Analysis: {len(tournament_comparisons)} pairwise comparisons conducted.\n"
    analysis += "Key patterns in decision-making and reasoning quality observed in tournament process."
    return analysis

def format_reflection_analysis(reflection_critiques: list) -> str:
    """Format reflection critique data for meta-analysis."""
    if not reflection_critiques:
        return "No reflection critiques available."
    
    analysis = f"Reflection Analysis: {len(reflection_critiques)} expert critiques conducted.\n"
    analysis += "Domain expert analysis patterns and quality assessments from reflection phase."
    return analysis

def format_evolution_analysis(evolved_scenarios: list) -> str:
    """Format evolution data for meta-analysis."""
    if not evolved_scenarios:
        return "No evolution attempts available."
    
    analysis = f"Evolution Analysis: {len(evolved_scenarios)} evolution attempts conducted.\n"
    analysis += "Enhancement strategy effectiveness and improvement patterns from evolution phase."
    return analysis

def format_competition_process_summary(state: dict) -> str:
    """Format overall competition process summary for meta-analysis."""
    directions = state.get("research_directions", [])
    scenarios = state.get("scenario_population", [])
    
    summary = f"Competition Process Summary:\n"
    summary += f"- {len(directions)} research directions explored\n"
    summary += f"- {len(scenarios)} total scenarios generated\n"
    summary += f"- Tournament, reflection, and evolution phases completed\n"
    summary += f"- Process methodology and agent performance data available for analysis"
    
    return summary

def generate_user_competition_summary(state: dict, direction_winners: list) -> str:
    """Generate a brief summary for user presentation."""
    summary = "# Co-Scientist Competition Summary\n\n"
    summary += f"The competition explored {len(state.get('research_directions', []))} different approaches "
    summary += f"and generated {len(state.get('scenario_population', []))} total variations.\n\n"
    
    summary += "## Direction Winners\n\n"
    for i, winner in enumerate(direction_winners, 1):
        summary += f"**Option {i}: {winner.get('research_direction', 'Unknown')}**\n"
        summary += f"- Approach: {winner.get('core_assumption', 'No assumption available')}\n"
        summary += f"- Team: {winner.get('team_id', 'Unknown')}\n\n"
    
    summary += f"These represent the {len(direction_winners)} strongest approaches from the competitive process. "
    summary += f"Please review all {len(direction_winners)} options and select your preferred direction.\n"
    
    return summary

def save_final_winners(top_scenarios: list, state: dict, output_dir: str = "output", phase: str = None):
    """Save the final winning scenarios as complete standalone files."""
    manager = get_output_manager(output_dir, phase)
    
    if not top_scenarios:
        print("No final winning scenarios to save")
        return
    
    for i, scenario in enumerate(top_scenarios, 1):
        scenario_id = scenario.get('scenario_id', f'winner_{i}')
        research_direction = scenario.get('research_direction', 'Unknown Direction')
        evolution_type = scenario.get('evolution_type', 'unknown')
        competition_rank = scenario.get('competition_rank', i)
        
        content = f"# Final Winner {competition_rank}: {research_direction}\n\n"
        content += f"**Competition Rank:** #{competition_rank} of 3 Final Winners\n"
        content += f"**Research Direction:** {research_direction}\n"
        content += f"**Scenario ID:** {scenario_id}\n"
        content += f"**Evolution Type:** {evolution_type}\n"
        content += f"**Selection Process:** {scenario.get('selection_reasoning', 'Won evolution tournament')}\n"
        content += f"**Generated:** {datetime.now().isoformat()}\n\n"
        
        content += "## Complete Scenario\n\n"
        content += scenario.get('scenario_content', 'No scenario content available')
        
        # Add competition context
        content += "\n\n## Competition Journey\n\n"
        content += f"This scenario emerged as the winner through co-scientist's competitive process:\n\n"
        content += f"1. **Initial Generation**: One of 6 scenarios in the '{research_direction}' research direction\n"
        content += f"2. **Expert Reflection**: Critiqued by 5 domain experts across physics, biology, engineering, social science, and economics\n"
        content += f"3. **Tournament Victory**: Won tournament bracket against other scenarios in its direction\n"
        content += f"4. **Evolution Enhancement**: Improved through 4 evolution strategies (feasibility, creativity, synthesis, detail enhancement)\n"
        content += f"5. **Evolution Tournament**: Final contest between original winner and 4 evolved variants\n"
        content += f"6. **Meta-Review**: Selected as one of 3 final representatives\n\n"
        
        # Add competition statistics
        total_scenarios = len(state.get("scenario_population", []))
        total_critiques = len(state.get("reflection_critiques", []))
        total_evolutions = len(state.get("evolved_scenarios", []))
        
        content += "## Competition Statistics\n\n"
        content += f"- **Total Scenarios Generated:** {total_scenarios}\n"
        content += f"- **Expert Critiques Produced:** {total_critiques}\n"
        content += f"- **Evolution Attempts:** {total_evolutions}\n"
        content += f"- **Final Selection Rate:** {competition_rank}/3 from {total_scenarios} initial scenarios ({(1/total_scenarios)*100:.2f}% selection rate)\n\n"
        
        # Add research directions context
        research_directions = state.get("research_directions", [])
        if research_directions:
            content += "## Research Directions Explored\n\n"
            for j, direction in enumerate(research_directions, 1):
                direction_name = direction.get('name', f'Direction {j}')
                direction_assumption = direction.get('assumption', 'No assumption listed')
                marker = "🏆 **WINNER** - " if direction_name == research_direction else ""
                content += f"{j}. {marker}**{direction_name}**\n"
                content += f"   - Core Assumption: {direction_assumption}\n\n"
        
        filename = f"winner_{competition_rank:02d}_{research_direction.replace(' ', '_')}_{scenario_id[:8]}.md"
        manager.save_file(filename, content, "final_winners")
        print(f"Saved final winner #{competition_rank}: {filename}")

# Helper functions
def parse_research_directions(content: str) -> list:
    """Parse research directions from meta-analysis output.
    
    Handles the format specified in the prompt:
    Direction 1: [Name]
    Core Assumption: [Key narrative assumption] 
    Focus: [What this approach emphasizes]
    
    Also handles markdown formatting that LLMs often add and multi-line content.
    """
    directions = []
    lines = content.split('\n')
    
    current_direction = {}
    current_field = None
    current_content = []
    
    print(f"DEBUG: Parsing {len(lines)} lines of meta-analysis content...")
    
    for line_num, line in enumerate(lines):
        line = line.strip()
        
        # Skip empty lines
        if not line:
            continue
            
        # Remove markdown formatting
        clean_line = line.replace("###", "").replace("**", "").strip()
        
        # Look for Direction lines (e.g., "Direction 1: Name" or "### Direction 1: **Name**")
        if clean_line.lower().startswith("direction") and ":" in clean_line:
            # Save previous field content if we have one
            if current_field and current_content:
                content_text = " ".join(current_content).strip()
                if current_direction and content_text:
                    current_direction[current_field] = content_text
                current_content = []
            
            # Save previous direction if complete
            if current_direction:
                print(f"  Adding direction: {current_direction.get('name', 'NO_NAME')}")
                directions.append(current_direction)
            
            # Start new direction
            name_part = clean_line.split(":", 1)[1].strip()
            current_direction = {"name": name_part}
            current_field = None
            print(f"  Found direction: {name_part}")
        
        # Look for Core Assumption lines
        elif clean_line.lower().startswith("core assumption") and ":" in clean_line:
            # Save previous field content
            if current_field and current_content:
                content_text = " ".join(current_content).strip()
                if current_direction and content_text:
                    current_direction[current_field] = content_text
                current_content = []
            
            # Start Core Assumption field
            current_field = "assumption"
            assumption_text = clean_line.split(":", 1)[1].strip()
            current_content = [assumption_text] if assumption_text else []
            print(f"    Found Core Assumption start")
        
        # Look for Focus lines  
        elif clean_line.lower().startswith("focus") and ":" in clean_line:
            # Save previous field content
            if current_field and current_content:
                content_text = " ".join(current_content).strip()
                if current_direction and content_text:
                    current_direction[current_field] = content_text
                current_content = []
            
            # Start Focus field
            current_field = "focus"
            focus_text = clean_line.split(":", 1)[1].strip()
            current_content = [focus_text] if focus_text else []
            print(f"    Found Focus start")
        
        # Look for Reasoning line (end of directions)
        elif clean_line.lower().startswith("reasoning") and ":" in clean_line:
            # Save current field content
            if current_field and current_content:
                content_text = " ".join(current_content).strip()
                if current_direction and content_text:
                    current_direction[current_field] = content_text
            
            # Save final direction
            if current_direction:
                print(f"  Adding final direction: {current_direction.get('name', 'NO_NAME')}")
                directions.append(current_direction)
            
            # Stop parsing at reasoning
            break
        
        # Otherwise, if we're in a field, accumulate content
        elif current_field and clean_line:
            current_content.append(clean_line)
    
    # Handle case where content doesn't end with "Reasoning:"
    if current_field and current_content:
        content_text = " ".join(current_content).strip()
        if current_direction and content_text:
            current_direction[current_field] = content_text
    
    # Add the last direction if it exists and wasn't added yet
    if current_direction and current_direction not in directions:
        print(f"  Adding last direction: {current_direction.get('name', 'NO_NAME')}")
        directions.append(current_direction)
    
    # Debug logging
    print(f"DEBUG: Parsed {len(directions)} directions from LLM response:")
    for i, direction in enumerate(directions):
        print(f"  Direction {i+1}: {direction.get('name', 'NO_NAME')}")
        print(f"    Assumption: {direction.get('assumption', 'MISSING')[:50]}...")
        print(f"    Focus: {direction.get('focus', 'MISSING')[:50]}...")
    
    return directions

def extract_integration_score(content: str) -> int:
    """Extract integration score from world integration analysis content."""
    import re
    # Look for patterns like "integration score: 8" or "score: 8/10"
    patterns = [
        r"integration score[:\s]+(\d+)",
        r"world integration[:\s]+(\d+)",
        r"score[:\s]+(\d+)",
        r"(\d+)/10"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, content.lower())
        if match:
            score = min(int(match.group(1)), 10)
            return max(score, 1)  # Ensure minimum score of 1
    
    return 5  # Default moderate integration score

def get_critique_summary(scenario_id: str, critiques: list) -> str:
    """Get summary of critiques for a specific scenario."""
    relevant_critiques = [c for c in critiques if c.get("target_scenario_id") == scenario_id]
    
    if not relevant_critiques:
        return "No specific critiques identified."
    
    summary = "Key critiques identified:\n"
    for critique in relevant_critiques:
        domain = critique.get("critique_domain", "Unknown")
        severity = critique.get("severity_score", 5)
        summary += f"- {domain} (severity {severity}/10): "
        # Include full critique content - no truncation for evolution
        content = critique.get("critique_content", "")
        summary += content + "\n"
    
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
        # Include full scenario content - no truncation for evolution
        summary += content + "\n"
    
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
    """Format tournament results for markdown output with quality and Elo metrics."""
    content = "# Co-Scientist Tournament Results\n\n"
    content += f"**Number of Tournaments:** {len(winners)}\n\n"
    
    if not winners:
        content += "No tournament winners - likely due to scenario generation failures.\n\n"
        return content
    
    # Calculate overall quality and Elo statistics
    all_quality_scores = []
    all_elo_ratings = []
    elo_tracker = None
    
    for winner in winners:
        winning_scenario = winner.get("winner", {})
        if winning_scenario and isinstance(winning_scenario, dict):
            quality_score = winning_scenario.get("quality_score", 0)
            elo_rating = winning_scenario.get("elo_rating", 0)
            
            if quality_score > 0:
                all_quality_scores.append(quality_score)
            if elo_rating > 0:
                all_elo_ratings.append(elo_rating)
        
        # Get Elo tracker from any tournament result
        if not elo_tracker and winner.get("elo_tracker"):
            elo_tracker = winner["elo_tracker"]
    
    # Display summary statistics
    if all_quality_scores:
        avg_quality = sum(all_quality_scores) / len(all_quality_scores)
        content += f"**Average Winner Quality Score:** {avg_quality:.1f}/100\n"
        content += f"**Quality Range:** {min(all_quality_scores)}-{max(all_quality_scores)}/100\n"
    
    if all_elo_ratings:
        avg_elo = sum(all_elo_ratings) / len(all_elo_ratings)
        content += f"**Average Winner Elo Rating:** {avg_elo:.0f}\n"
        content += f"**Elo Range:** {min(all_elo_ratings):.0f}-{max(all_elo_ratings):.0f}\n"
    
    if elo_tracker:
        elo_stats = elo_tracker.get_statistics()
        content += f"**Overall Elo Statistics (All Scenarios):**\n"
        content += f"- Total Scenarios: {elo_stats['count']}\n"
        content += f"- Average Rating: {elo_stats['average']:.0f}\n" 
        content += f"- Standard Deviation: {elo_stats['std_dev']:.0f}\n"
    
    content += "\n"
    
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
            team_id = winning_scenario.get('team_id', 'Unknown')
            quality_score = winning_scenario.get("quality_score", 0)
            elo_rating = winning_scenario.get("elo_rating", 1500)
            advancement_rec = winning_scenario.get("advancement_recommendation", "N/A")
            
            content += f"**Winner Team:** {team_id}\n"
            content += f"**Quality Score:** {quality_score}/100\n"
            content += f"**Final Elo Rating:** {elo_rating:.0f}\n"
            
            # Show Elo progression
            if elo_tracker:
                rating_history = elo_tracker.get_rating_history(winning_scenario.get("scenario_id", ""))
                if len(rating_history) > 1:
                    initial_rating = rating_history[0]['rating']
                    rating_change = elo_rating - initial_rating
                    content += f"**Elo Change:** {rating_change:+.0f} (from {initial_rating:.0f})\n"
            
            content += f"**Pre-Tournament Assessment:** {advancement_rec}\n"
            
            # Show individual dimension scores if available
            quality_scores = winning_scenario.get("quality_scores", {})
            if quality_scores and len(quality_scores) > 1:  # More than just overall score
                content += f"**Quality Breakdown:**\n"
                for dimension, score in quality_scores.items():
                    if dimension != "overall_quality_score":
                        dimension_display = dimension.replace('_', ' ').title()
                        content += f"  - {dimension_display}: {score}/100\n"
            
            # Show reflection summary if available
            critique_summary = winning_scenario.get("critique_summary", "")
            if critique_summary and critique_summary != "No reflection critique available":
                content += f"**Reflection Summary:** {critique_summary}\n"
            
            content += "\n"
            
            # Show winner scenario content (truncated)
            scenario_content = winning_scenario.get('scenario_content', 'No content')
            if len(scenario_content) > 600:  # Reduced to make room for Elo info
                content += f"**Winning Scenario:** {scenario_content[:600]}...\n\n"
            else:
                content += f"**Winning Scenario:** {scenario_content}\n\n"
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
    """Format research directions for meta-analysis."""
    if not directions:
        return "No research directions identified."
    
    formatted = ""
    for i, direction in enumerate(directions, 1):
        formatted += f"Direction {i}: {direction.get('name', 'Unknown')}\n"
        formatted += f"  Assumption: {direction.get('assumption', 'N/A')}\n"
        formatted += f"  Focus: {direction.get('focus', 'N/A')}\n"
    
    return formatted

# Build the co-scientist workflow
# Routing functions for dynamic phase control
def route_after_generation(state: CoScientistState, config: RunnableConfig) -> Literal["reflection", "tournament", "meta_review"]:
    """Route after scenario generation based on process depth."""
    configuration = CoScientistConfiguration.from_runnable_config(config)
    enabled_phases = configuration.get_enabled_phases_for_depth()
    
    if "reflection" in enabled_phases:
        return "reflection"
    elif "tournament" in enabled_phases:
        return "tournament"
    else:
        return "meta_review"

def route_after_reflection(state: CoScientistState, config: RunnableConfig) -> Literal["tournament", "meta_review"]:
    """Route after reflection based on process depth."""
    configuration = CoScientistConfiguration.from_runnable_config(config)
    enabled_phases = configuration.get_enabled_phases_for_depth()
    
    if "tournament" in enabled_phases:
        return "tournament"
    else:
        return "meta_review"

def route_after_tournament(state: CoScientistState, config: RunnableConfig) -> Literal["evolution", "meta_review"]:
    """Route after tournament based on process depth."""
    configuration = CoScientistConfiguration.from_runnable_config(config)
    enabled_phases = configuration.get_enabled_phases_for_depth()
    
    if "evolution" in enabled_phases:
        return "evolution"
    else:
        return "meta_review"

def route_after_evolution(state: CoScientistState, config: RunnableConfig) -> Literal["evolution_tournament", "meta_review"]:
    """Route after evolution based on process depth."""
    configuration = CoScientistConfiguration.from_runnable_config(config)
    enabled_phases = configuration.get_enabled_phases_for_depth()
    
    if "evolution_tournament" in enabled_phases:
        return "evolution_tournament"
    else:
        return "meta_review"

co_scientist_builder = StateGraph(CoScientistState, input=CoScientistInputState, config_schema=CoScientistConfiguration)

# Add nodes for each phase
co_scientist_builder.add_node("meta_analysis", meta_analysis_phase)
co_scientist_builder.add_node("scenario_generation", parallel_scenario_generation)
co_scientist_builder.add_node("reflection", reflection_phase)
co_scientist_builder.add_node("tournament", tournament_phase)
co_scientist_builder.add_node("evolution", evolution_phase)
co_scientist_builder.add_node("evolution_tournament", evolution_tournament_phase)
co_scientist_builder.add_node("meta_review", final_meta_review_phase)

# Define the dynamic workflow edges
co_scientist_builder.add_edge(START, "meta_analysis")
co_scientist_builder.add_edge("meta_analysis", "scenario_generation")
co_scientist_builder.add_conditional_edges("scenario_generation", route_after_generation)
co_scientist_builder.add_conditional_edges("reflection", route_after_reflection)
co_scientist_builder.add_conditional_edges("tournament", route_after_tournament)
co_scientist_builder.add_conditional_edges("evolution", route_after_evolution)
co_scientist_builder.add_edge("evolution_tournament", "meta_review")
co_scientist_builder.add_edge("meta_review", END)

# Compile the co-scientist subgraph
co_scientist = co_scientist_builder.compile() 

def format_unified_reflection_critiques(critiques: list) -> str:
    """Format unified reflection critiques for display including quality scores."""
    
    if not critiques:
        return "No unified reflection critiques available."
    
    content = "# Unified Reflection Analysis Summary\n\n"
    content += f"**Total Scenarios Evaluated:** {len(critiques)}\n\n"
    
    # Calculate summary statistics
    quality_scores = [c.get("overall_quality_score", 0) for c in critiques]
    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
    
    advancement_counts = {}
    for critique in critiques:
        recommendation = critique.get("advancement_recommendation", "UNKNOWN")
        advancement_counts[recommendation] = advancement_counts.get(recommendation, 0) + 1
    
    content += "## Summary Statistics\n\n"
    content += f"**Average Quality Score:** {avg_quality:.1f}/100\n"
    content += f"**Quality Range:** {min(quality_scores)}-{max(quality_scores)}/100\n\n"
    
    content += "**Advancement Recommendations:**\n"
    for recommendation, count in advancement_counts.items():
        content += f"- {recommendation}: {count} scenarios\n"
    content += "\n"
    
    # Group critiques by quality tier
    high_quality = [c for c in critiques if c.get("overall_quality_score", 0) >= 80]
    medium_quality = [c for c in critiques if 60 <= c.get("overall_quality_score", 0) < 80]
    low_quality = [c for c in critiques if c.get("overall_quality_score", 0) < 60]
    
    content += "## Quality Distribution\n\n"
    content += f"**High Quality (80-100):** {len(high_quality)} scenarios\n"
    content += f"**Medium Quality (60-79):** {len(medium_quality)} scenarios\n"
    content += f"**Low Quality (0-59):** {len(low_quality)} scenarios\n\n"
    
    # Detailed critique analysis
    content += "## Detailed Reflections\n\n"
    
    # Sort by quality score descending
    sorted_critiques = sorted(critiques, key=lambda c: c.get("overall_quality_score", 0), reverse=True)
    
    for i, critique in enumerate(sorted_critiques, 1):
        scenario_id = critique.get("target_scenario_id", "Unknown")
        quality_score = critique.get("overall_quality_score", 0)
        recommendation = critique.get("advancement_recommendation", "UNKNOWN")
        
        content += f"### {i}. Scenario {scenario_id}\n\n"
        content += f"**Overall Quality Score:** {quality_score}/100\n"
        content += f"**Advancement Recommendation:** {recommendation}\n\n"
        
        # Include individual dimension scores if available
        quality_scores = critique.get("quality_scores", {})
        if quality_scores and len(quality_scores) > 1:  # More than just overall score
            content += "**Dimension Scores:**\n"
            for dimension, score in quality_scores.items():
                if dimension != "overall_quality_score":
                    dimension_display = dimension.replace('_', ' ').title()
                    content += f"- {dimension_display}: {score}/100\n"
            content += "\n"
        
        # Include reflection content (truncated)
        reflection_content = critique.get("critique_content", "No content available")
        if len(reflection_content) > 500:
            content += f"**Key Insights:** {reflection_content[:500]}...\n\n"
        else:
            content += f"**Full Analysis:** {reflection_content}\n\n"
        
        content += "---\n\n"
    
    return content

