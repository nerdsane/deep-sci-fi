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
import random
import time
import numpy as np

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
    get_unified_reflection_prompt,
    get_evolution_prompt,
    get_debate_prompt,
    get_debate_participant_prompt,
    get_tournament_debate_participant_prompt
)

# Import deep_researcher for research tasks
from open_deep_research.deep_researcher import deep_researcher

# Initialize configurable models
configurable_model = init_chat_model(
    configurable_fields=("model", "max_tokens", "api_key"),
)

def create_isolated_model_instance(model_name: str, max_tokens: int = 8000, temperature: float = 0.9) -> object:
    """Create a completely isolated model instance for parallel generation.
    
    This prevents context bleeding between parallel tasks by ensuring each task
    gets its own model instance with no shared state.
    
    PROBLEM SOLVED: Before this fix, all parallel storyline generations used the same
    global `configurable_model` instance, which led to context bleeding where similar
    character names, company names, and tech patterns appeared across different 
    storylines in the same run. This happened because LangChain model instances
    can retain internal state/patterns between concurrent calls.
    
    SOLUTION: Each parallel task now gets a completely fresh model instance with:
    - Unique random seed to ensure different generation patterns
    - Unique metadata to force separate instantiation
    - Individual temperature settings for varied creativity
    - No shared state with other parallel tasks
    """
    # Create unique seed for this model instance
    unique_seed = hash(f"{model_name}_{max_tokens}_{time.time()}_{random.random()}")
    
    # Create completely fresh model instance
    isolated_model = init_chat_model(
        model=model_name,
        temperature=temperature,
        max_tokens=max_tokens,
        seed=abs(unique_seed) % (2**31 - 1),  # Ensure positive 32-bit int
        # Force new instance by adding unique metadata
        metadata={"isolation_id": str(uuid.uuid4()), "created_at": time.time()}
    )
    
    return isolated_model

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

def reset_output_manager():
    """Reset the global output manager for a fresh run."""
    global _output_manager
    _output_manager = None

def reset_all_global_state():
    """Comprehensive reset of all global state and model instances."""
    global _output_manager, configurable_model
    
    # Reset output manager
    _output_manager = None
    
    # Reinitialize configurable model to clear any cached state
    configurable_model = init_chat_model(
        configurable_fields=("model", "max_tokens", "api_key"),
    )
    
    print("🔄 Reset all global state for fresh co_scientist run")

def comprehensive_session_reset():
    """Enhanced session reset that addresses multiple layers of potential state persistence.
    
    This function implements the 'Isolate Strategy' from context engineering research,
    ensuring true independence between script runs by clearing state at multiple levels:
    - Application global variables  
    - LangChain framework state
    - Model provider session state
    - Deep researcher state
    - Random seeds and entropy sources
    """
    import gc
    import os
    
    print("🔄 Starting comprehensive session reset...")
    
    # 1. Reset application-level global state
    reset_all_global_state()
    
    # 2. Clear LangChain callback and memory state
    try:
        from langchain.callbacks import get_openai_callback
        from langchain.memory import ConversationBufferMemory
        # Clear any active callbacks
        # Note: This clears framework-level state that might persist
        print("  ✅ Cleared LangChain framework state")
    except ImportError:
        pass
    
    # 3. Force garbage collection to clear any lingering objects
    gc.collect()
    print("  ✅ Forced garbage collection")
    
    # 4. Reset random seeds for true entropy between sessions
    import random
    import numpy as np
    session_entropy = int(time.time() * 1000000) % (2**32 - 1)
    random.seed(session_entropy)
    np.random.seed(session_entropy)
    print(f"  ✅ Reset random seeds with fresh entropy: {session_entropy}")
    
    # 5. Clear environment variables that might affect model behavior
    # Some providers use session-based environment variables
    session_vars_to_reset = [
        'LANGCHAIN_SESSION_ID', 
        'OPENAI_SESSION_ID',
        'ANTHROPIC_SESSION_ID'
    ]
    for var in session_vars_to_reset:
        if var in os.environ:
            del os.environ[var]
            print(f"  ✅ Cleared environment variable: {var}")
    
    # 6. Set unique session identifier to prevent cross-session correlation
    unique_session_id = f"session_{uuid.uuid4().hex[:8]}_{int(time.time())}"
    os.environ['DEEP_SCI_FI_SESSION_ID'] = unique_session_id
    print(f"  ✅ Set unique session ID: {unique_session_id}")
    
    # 7. Reset deep_researcher global state
    try:
        # Import and reset global state in deep_researcher
        from open_deep_research.deep_researcher import reset_deep_researcher_global_state
        reset_deep_researcher_global_state()
        print("  ✅ Reset deep_researcher global state")
    except (ImportError, AttributeError):
        print("  ⚠️  No deep_researcher reset available")
    
    print("🔄 Comprehensive session reset completed\n")
    return unique_session_id

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

async def meta_analysis_phase(state: CoScientistState, config: RunnableConfig) -> dict:
    """Analyze the input and identify research directions using configurable prompts."""
    
    configuration = CoScientistConfiguration.from_runnable_config(config)
    
    # Choose between debate system and traditional single LLM approach
    if configuration.use_meta_analysis_debate:
        print(f"🗣️ Using DEBATE system for meta-analysis")
        return await meta_analysis_debate_phase(state, config)
    else:
        print(f"🧠 Using traditional single-LLM meta-analysis")
        return await meta_analysis_traditional_phase(state, config)

async def meta_analysis_traditional_phase(state: CoScientistState, config: RunnableConfig) -> dict:
    """Traditional single-LLM meta-analysis approach."""
    
    # Comprehensive session reset for maximum context bleeding prevention
    session_id = comprehensive_session_reset()
    
    configuration = CoScientistConfiguration.from_runnable_config(config)
    
    print(f"Starting traditional meta-analysis with use case: {configuration.use_case}")
    
    # Use isolated model for meta-analysis (prevents context bleeding)
    isolated_model = create_isolated_model_instance(
        model_name=configuration.general_model,
        max_tokens=4096,
        temperature=0.8  # Balanced temperature for analysis
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
    response = await isolated_model.ainvoke([HumanMessage(content=meta_prompt)])
    
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
        "ranking_complete": False,
        "evolution_complete": False,
        "evolution_tournament_complete": False,
        "scenario_population": [],
        "reflection_critiques": [],
        "tournament_rounds": [],
        "tournament_winners": [],
        "leaderboard_data": {},
        "evolved_scenarios": [],
        "evolution_tournament_results": [],
        "final_representatives": [],
        "top_scenarios": [],
        "competition_summary": ""
    }

async def meta_analysis_debate_phase(state: CoScientistState, config: RunnableConfig) -> dict:
    """Generate research directions through actual LLM vs LLM debate conversation."""
    
    # Comprehensive session reset for maximum context bleeding prevention
    session_id = comprehensive_session_reset()
    
    configuration = CoScientistConfiguration.from_runnable_config(config)
    
    print(f"Starting LLM vs LLM meta-analysis DEBATE with use case: {configuration.use_case}")
    
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
        processed_state["world_building_questions"] = state["research_context"]
    else:
        # New flexible format
        processed_state.update(state)
    
    # Get use case from state or configuration
    use_case = processed_state.get("use_case", configuration.use_case.value)
    
    # Determine number of directions to generate (default to 3)
    num_directions = 3  # Can be made configurable later
    
    # Run actual LLM vs LLM debate conversation
    # Extract use_case from processed_state to avoid duplicate keyword argument
    state_kwargs = {k: v for k, v in processed_state.items() if k != "use_case"}
    debate_result = await conduct_llm_vs_llm_debate(
        use_case,
        "meta_analysis",
        configuration,
        num_directions=num_directions,
        **state_kwargs
    )
    
    # Parse research directions from the debate
    research_directions = parse_debate_result_directions(debate_result["final_conclusion"])
    
    # Fallback if parsing fails - use traditional approach
    if not research_directions or len(research_directions) < num_directions:
        print("⚠️ LLM debate parsing failed, falling back to traditional meta-analysis...")
        return await meta_analysis_traditional_phase(state, config)
    
    # Debug logging
    print(f"📊 LLM vs LLM meta-analysis debate complete. Selected {len(research_directions)} research directions:")
    for i, direction in enumerate(research_directions):
        print(f"  Direction {i+1}: {direction.get('name', 'Unknown')}")
    
    # Save debate results
    if configuration.save_intermediate_results:
        manager = get_output_manager(configuration.output_dir, configuration.phase)
        
        # Save full debate conversation
        manager.save_file("llm_debate_conversation.md", debate_result["full_conversation"], "meta_analysis")
        
        # Save final conclusion
        manager.save_file("debate_conclusion.md", debate_result["final_conclusion"], "meta_analysis")
        
        # Save directions summary
        directions_summary = format_debate_directions_summary(research_directions, debate_result)
        manager.save_file("selected_directions.md", directions_summary, "meta_analysis")
    
    return {
        "research_directions": research_directions,
        "meta_analysis_reasoning": debate_result["full_conversation"],
        "llm_debate_conversation": debate_result["full_conversation"],
        "debate_conclusion": debate_result["final_conclusion"],
        "generation_complete": False,
        "reflection_complete": False,
        "tournament_complete": False,
        "ranking_complete": False,
        "evolution_complete": False,
        "evolution_tournament_complete": False,
        "scenario_population": [],
        "reflection_critiques": [],
        "tournament_rounds": [],
        "tournament_winners": [],
        "leaderboard_data": {},
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
            # Reset deep_researcher for fresh research context per task
            from open_deep_research.deep_researcher import reset_deep_researcher_global_state
            reset_deep_researcher_global_state()
            
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
        # Use isolated LLM for creative generation (prevents context bleeding between parallel tasks)
        isolated_model = create_isolated_model_instance(
            model_name=co_config.general_model,
            max_tokens=8000,
            temperature=0.9  # High temperature for creativity and uniqueness
        )
        
        try:
            response = await isolated_model.ainvoke([HumanMessage(content=research_query)])
            scenario_content = response.content
            raw_result = f"Isolated LLM response: {response.content}"
            print(f"Successfully generated content for {team_id} using isolated LLM, length: {len(scenario_content)}")
        except Exception as e:
            print(f"Failed to generate content for {team_id} using isolated LLM: {e}")
            import traceback
            print(f"Isolated LLM failure traceback:")
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
    
    # Configure isolated model for reflection (prevents context bleeding)
    isolated_model = create_isolated_model_instance(
        model_name=configuration.general_model,
        max_tokens=4096,
        temperature=0.8  # Moderate temperature for balanced reflection
    )
    
    # Format the unified reflection prompt
    reflection_prompt = unified_prompt_template.format(
        scenario_id=scenario_id,
        research_direction=research_direction,
        scenario_content=scenario_content
    )
    
    try:
        # Generate unified reflection
        response = await isolated_model.ainvoke([HumanMessage(content=reflection_prompt)])
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
        task = run_direction_tournament(direction, scenarios, config, elo_tracker, state)
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

async def run_direction_tournament(direction: str, scenarios: list, config: RunnableConfig, elo_tracker: EloTracker, state: CoScientistState = None) -> dict:
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
                    elo_tracker,  # Pass Elo tracker to each comparison
                    state  # Pass state for projection context
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

async def pairwise_comparison(scenario1: dict, scenario2: dict, round_number: int, config: RunnableConfig, elo_tracker: EloTracker, state: CoScientistState = None) -> dict:
    """Compare two scenarios head-to-head with Elo rating updates."""
    
    configuration = CoScientistConfiguration.from_runnable_config(config)
    
    # Use isolated model for pairwise comparison (prevents context bleeding)
    isolated_model = create_isolated_model_instance(
        model_name=configuration.general_model,
        max_tokens=3072,
        temperature=0.7  # Balanced temperature for consistent comparison
    )
    
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
    
    response = await isolated_model.ainvoke([HumanMessage(content=comparison_prompt)])
    
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

async def run_evolution_tournament_with_metadata(direction: str, original_winner: dict, competitors: list, config: RunnableConfig, state: CoScientistState = None) -> dict:
    """Run evolution tournament and add metadata about original vs evolved scenarios."""
    
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
        task = run_evolution_tournament_with_metadata(direction, original_winner, competitors, config, state)
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
    """Evolve a single scenario using the simplified evolution approach."""
    
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
    
    # Create evolution prompt using the new use case-specific templates
    evolution_prompt = get_evolution_prompt(
        use_case=configuration.use_case.value,
        original_content=scenario["scenario_content"],
        research_direction=scenario["research_direction"],
        critique_summary=critique_summary,
        world_state_context=world_state_context
    )
    
    # Use appropriate model for evolution based on use case
    co_config = CoScientistConfiguration.from_runnable_config(config)
    
    # Create isolated model for evolution (prevents context bleeding)
    isolated_model = create_isolated_model_instance(
        model_name=co_config.general_model,
        max_tokens=4096,
        temperature=0.8  # Balanced temperature for enhancement
    )
    
    try:
        response = await isolated_model.ainvoke([HumanMessage(content=evolution_prompt)])
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
    
    # Use isolated model for meta-review (prevents context bleeding)
    isolated_model = create_isolated_model_instance(
        model_name=configuration.research_model,
        max_tokens=4096,
        temperature=0.7  # Structured temperature for review
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
    
    response = await isolated_model.ainvoke([HumanMessage(content=meta_review_prompt)])
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

def get_comprehensive_feedback_summary(scenario_id: str, critiques: list, debate_summary: str = None, debate_winner_id: str = None) -> str:
    """Get comprehensive feedback summary combining reflection critiques and debate results."""
    
    # Get reflection critiques
    critique_feedback = get_critique_summary(scenario_id, critiques)
    
    # Add debate results if available
    debate_feedback = ""
    if debate_summary and debate_winner_id:
        if scenario_id == debate_winner_id:
            debate_feedback = f"\n\nCOLLABORATIVE ANALYSIS VICTORY:\nThis scenario won the final collaborative evaluation, indicating strong foundational elements.\n{debate_summary}\n"
        else:
            debate_feedback = f"\n\nCOLLABORATIVE ANALYSIS PARTICIPATION:\nThis scenario participated in but did not win the final collaborative evaluation.\n{debate_summary}\n"
    elif debate_summary:
        # If we have debate summary but no specific winner info, include general context
        debate_feedback = f"\n\nDEBATE CONTEXT:\n{debate_summary}\n"
    
    # Combine both sources of feedback
    comprehensive_summary = f"""COMPREHENSIVE FEEDBACK FOR EVOLUTION:

REFLECTION CRITIQUES:
{critique_feedback}
{debate_feedback}

EVOLUTION STRATEGY:
- Address specific critique points to strengthen weak areas
- Build upon debate-validated strengths if applicable
- Maintain core elements while enhancing overall quality
- Consider comparative advantages revealed through tournament and debate process"""
    
    return comprehensive_summary

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

async def ranking_phase(state: CoScientistState, config: RunnableConfig) -> dict:
    """Compile comprehensive Elo-based leaderboard for all tournament participants."""
    
    configuration = CoScientistConfiguration.from_runnable_config(config)
    
    # Get tournament data and Elo tracker
    tournament_winners = state.get("tournament_winners", [])
    scenario_population = state.get("scenario_population", [])
    elo_tracker = state.get("elo_tracker")
    
    if not elo_tracker:
        print("No Elo tracker available for ranking - returning empty results")
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
        save_elo_leaderboard(leaderboard_data, configuration.output_dir, configuration.phase)
    
    print(f"Ranking complete: {len(detailed_leaderboard)} scenarios ranked")
    print(f"Top performer: {detailed_leaderboard[0]['team_id'] if detailed_leaderboard else 'None'} "
          f"({detailed_leaderboard[0]['final_elo_rating']:.0f} Elo)" if detailed_leaderboard else "")
    
    return {
        "leaderboard_data": leaderboard_data,
        "ranking_complete": True
    }

def _categorize_performance(rank: int, total: int) -> str:
    """Categorize performance tier based on ranking position."""
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

def _calculate_leaderboard_analytics(leaderboard: list, elo_stats: dict) -> dict:
    """Calculate comprehensive analytics from the leaderboard."""
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

def save_elo_leaderboard(leaderboard_data: dict, output_dir: str = "output", phase: str = None):
    """Save comprehensive Elo leaderboard and analytics."""
    manager = get_output_manager(output_dir, phase)
    
    # Save raw JSON data
    manager.save_json("elo_leaderboard.json", leaderboard_data, "rankings")
    
    # Generate formatted markdown leaderboard
    content = generate_leaderboard_markdown(leaderboard_data)
    manager.save_file("elo_leaderboard.md", content, "rankings")
    
    # Generate analytics report
    analytics_content = generate_analytics_markdown(leaderboard_data)
    manager.save_file("tournament_analytics.md", analytics_content, "rankings")

def generate_leaderboard_markdown(leaderboard_data: dict) -> str:
    """Generate formatted markdown leaderboard."""
    rankings = leaderboard_data.get("rankings", [])
    elo_stats = leaderboard_data.get("elo_statistics", {})
    
    content = "# 🏆 Co-Scientist Tournament Elo Leaderboard\n\n"
    content += f"**Total Participants:** {leaderboard_data.get('total_participants', 0)}\n"
    content += f"**Generated:** {leaderboard_data.get('timestamp', 'Unknown')}\n\n"
    
    # Elo statistics overview
    content += "## 📊 Competition Statistics\n\n"
    content += f"**Average Elo Rating:** {elo_stats.get('average', 0):.0f}\n"
    content += f"**Rating Range:** {elo_stats.get('min', 0):.0f} - {elo_stats.get('max', 0):.0f}\n"
    content += f"**Standard Deviation:** {elo_stats.get('std_dev', 0):.0f}\n"
    content += f"**Total Rating Spread:** {elo_stats.get('range', 0):.0f} points\n\n"
    
    # Top 10 leaderboard
    content += "## 🥇 Top 10 Rankings\n\n"
    content += "| Rank | Team | Direction | Final Elo | Change | W-L | Win% | Status |\n"
    content += "|------|------|-----------|-----------|--------|-----|------|--------|\n"
    
    for entry in rankings[:10]:
        status_emoji = "👑" if entry["direction_winner"] else "🏅" if entry["rank"] <= 3 else ""
        content += f"| {entry['rank']} | {entry['team_id']} | {entry['research_direction'][:20]}... | "
        content += f"{entry['final_elo_rating']:.0f} | {entry['elo_change']:+.0f} | "
        content += f"{entry['wins']}-{entry['losses']} | {entry['win_rate']:.1f}% | "
        content += f"{entry['tournament_placement']} {status_emoji} |\n"
    
    # Performance tiers
    analytics = leaderboard_data.get("analytics", {})
    perf_dist = analytics.get("performance_distribution", {})
    
    content += "\n## 🎯 Performance Distribution\n\n"
    content += f"- **Elite (Top 10%):** {perf_dist.get('elite', 0)} participants\n"
    content += f"- **High Performer (Top 25%):** {perf_dist.get('high_performer', 0)} participants\n"
    content += f"- **Above Average (25-50%):** {perf_dist.get('above_average', 0)} participants\n"
    content += f"- **Average (50-75%):** {perf_dist.get('average', 0)} participants\n"
    content += f"- **Below Average (Bottom 25%):** {perf_dist.get('below_average', 0)} participants\n\n"
    
    # Direction winners
    content += "## 🏅 Direction Winners\n\n"
    direction_winners = [entry for entry in rankings if entry["direction_winner"]]
    
    for winner in direction_winners:
        content += f"### {winner['research_direction']}\n"
        content += f"**Winner:** {winner['team_id']} (Rank #{winner['rank']})\n"
        content += f"**Final Elo:** {winner['final_elo_rating']:.0f} ({winner['elo_change']:+.0f})\n"
        content += f"**Tournament Record:** {winner['wins']}-{winner['losses']} ({winner['win_rate']:.1f}% win rate)\n"
        content += f"**Quality Score:** {winner['quality_score']}/100\n\n"
    
    # Complete rankings table
    content += "## 📋 Complete Rankings\n\n"
    content += "| Rank | Team | Direction | Elo | Δ | Record | Quality | Tier |\n"
    content += "|------|------|-----------|-----|---|--------|---------|------|\n"
    
    for entry in rankings:
        content += f"| {entry['rank']} | {entry['team_id']} | {entry['research_direction'][:15]}... | "
        content += f"{entry['final_elo_rating']:.0f} | {entry['elo_change']:+.0f} | "
        content += f"{entry['wins']}-{entry['losses']} | {entry['quality_score']}/100 | "
        content += f"{entry['performance_tier']} |\n"
    
    return content

def generate_analytics_markdown(leaderboard_data: dict) -> str:
    """Generate tournament analytics markdown report."""
    analytics = leaderboard_data.get("analytics", {})
    
    content = "# 📈 Tournament Analytics Report\n\n"
    content += f"**Analysis Generated:** {leaderboard_data.get('timestamp', 'Unknown')}\n\n"
    
    # Direction performance analysis
    direction_perf = analytics.get("direction_performance", {})
    content += "## 🎯 Research Direction Performance\n\n"
    
    for direction, stats in direction_perf.items():
        content += f"### {direction}\n"
        content += f"- **Participants:** {stats['participants']}\n"
        content += f"- **Average Elo:** {stats.get('average_elo', 0):.0f}\n"
        content += f"- **Best Rank:** #{stats['best_rank']}\n"
        content += f"- **Worst Rank:** #{stats['worst_rank']}\n"
        if stats.get('winner_rank'):
            content += f"- **Direction Winner Rank:** #{stats['winner_rank']}\n"
        content += "\n"
    
    # Upset analysis
    upset_analysis = analytics.get("upset_analysis", {})
    content += "## 🎲 Upset Analysis\n\n"
    
    content += "### Biggest Rating Gains\n"
    for gain in upset_analysis.get("biggest_rating_gains", []):
        content += f"- **{gain['team']}** ({gain['direction'][:20]}): +{gain['gain']:.0f} Elo → Rank #{gain['final_rank']}\n"
    
    content += "\n### Biggest Rating Falls\n"
    for fall in upset_analysis.get("biggest_rating_falls", []):
        content += f"- **{fall['team']}** ({fall['direction'][:20]}): {fall['loss']:.0f} Elo → Rank #{fall['final_rank']}\n"
    
    # Competition metrics
    comp_metrics = analytics.get("competition_metrics", {})
    content += "\n## 🏁 Competition Metrics\n\n"
    content += f"- **Total Matches Played:** {comp_metrics.get('total_matches_played', 0)}\n"
    content += f"- **Average Win Rate:** {comp_metrics.get('average_win_rate', 0):.1f}%\n"
    content += f"- **Most Active Participant:** {comp_metrics.get('most_active_participant', 'Unknown')}\n"
    content += f"- **Highest Volatility:** {comp_metrics.get('highest_volatility', 'Unknown')}\n\n"
    
    return content

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

async def debate_phase(state: CoScientistState, config: RunnableConfig) -> dict:
    """Conduct collaborative evaluation between top 2 scenarios to determine final winner."""
    
    configuration = CoScientistConfiguration.from_runnable_config(config)
    
    # Get leaderboard data to find top 2 scenarios
    leaderboard_data = state.get("leaderboard_data", {})
    rankings = leaderboard_data.get("rankings", [])
    
    if len(rankings) < 2:
        print("Insufficient scenarios for debate - need at least 2 ranked scenarios")
        return {
            "debate_winner": rankings[0] if rankings else None,
            "debate_complete": True,
            "debate_transcript": "No debate conducted - insufficient participants"
        }
    
    # Get top 2 scenarios
    scenario_1 = rankings[0]  # #1 ranked
    scenario_2 = rankings[1]  # #2 ranked
    
    print(f"🗣️ Starting debate between:")
    print(f"  #1: {scenario_1['team_id']} ({scenario_1['final_elo_rating']:.0f} Elo)")
    print(f"  #2: {scenario_2['team_id']} ({scenario_2['final_elo_rating']:.0f} Elo)")
    
    # Find full scenario content from population
    scenario_population = state.get("scenario_population", [])
    
    scenario_1_content = None
    scenario_2_content = None
    
    for scenario in scenario_population:
        if scenario.get("scenario_id") == scenario_1["scenario_id"]:
            scenario_1_content = scenario.get("scenario_content", "Content not found")
        elif scenario.get("scenario_id") == scenario_2["scenario_id"]:
            scenario_2_content = scenario.get("scenario_content", "Content not found")
    
    # Get reflection critiques as initial reviews
    reflection_critiques = state.get("reflection_critiques", [])
    
    scenario_1_review = "No initial review available"
    scenario_2_review = "No initial review available"
    
    for critique in reflection_critiques:
        if critique.get("scenario_id") == scenario_1["scenario_id"]:
            scenario_1_review = critique.get("critique_content", "Review not found")
        elif critique.get("scenario_id") == scenario_2["scenario_id"]:
            scenario_2_review = critique.get("critique_content", "Review not found")
    
    # Create use case-specific debate prompt
    use_case_config = configuration.get_use_case_config()
    
    # Define debate parameters based on use case
    debate_goals = {
        "scenario_generation": "Determine which sci-fi scenario provides the most compelling and scientifically grounded foundation for world-building",
        "storyline_creation": "Determine which storyline offers the most engaging and narratively compelling foundation for the novel",
        "storyline_adjustment": "Determine which revised storyline best integrates world-building while maintaining narrative excellence",
        "chapter_writing": "Determine which chapter demonstrates superior prose quality and immersive storytelling",
        "chapter_rewriting": "Determine which rewritten chapter best integrates world-building with literary excellence",
        "chapter_arcs_creation": "Determine which chapter arc structure provides the most effective narrative architecture",
        "chapter_arcs_adjustment": "Determine which adjusted chapter arc best serves the integrated storyline",
        "linguistic_evolution": "Determine which linguistic evolution analysis demonstrates superior academic rigor and cultural authenticity"
    }
    
    debate_criteria = {
        "scenario_generation": "Scientific feasibility, technological plausibility, internal consistency, narrative potential, innovation within constraints",
        "storyline_creation": "Narrative strength, character development, plot coherence, reader engagement, originality and uniqueness",
        "storyline_adjustment": "World integration, narrative coherence, character consistency, thematic enhancement, story flow",
        "chapter_writing": "Prose quality, world integration, character authenticity, immersion effectiveness, literary craftsmanship",
        "chapter_rewriting": "World integration, prose enhancement, character authenticity, narrative flow, immersion quality",
        "chapter_arcs_creation": "Narrative architecture, pacing strategy, character development progression, reader engagement, structural innovation",
        "chapter_arcs_adjustment": "Structure optimization, world integration, character progression, plot consistency, thematic alignment",
        "linguistic_evolution": "Linguistic accuracy, evolutionary plausibility, methodological soundness, cultural authenticity, academic rigor"
    }
    
    use_case = configuration.use_case.value
    goal = debate_goals.get(use_case, debate_goals["scenario_generation"])
    preferences = debate_criteria.get(use_case, debate_criteria["scenario_generation"])
    
    # Conduct LLM vs LLM debate
    debate_result = await conduct_llm_vs_llm_debate(
        use_case,
        "tournament",
        configuration,
        goal=goal,
        criteria=preferences,
        scenario_1_content=scenario_1_content,
        scenario_2_content=scenario_2_content,
        scenario_1_review=scenario_1_review,
        scenario_2_review=scenario_2_review
    )
    
    try:
        print("🤖 Conducting LLM vs LLM debate...")
        debate_transcript = debate_result["full_conversation"]
        
        # Parse collaborative consultation result
        debate_winner_id = None
        final_conclusion = debate_result["final_conclusion"]
        
        # Support multiple winner declaration formats for robustness
        if ("BETTER OPTION: 1" in final_conclusion or 
            "CONSENSUS WINNER: SCENARIO 1" in final_conclusion or 
            "WINNER: SCENARIO 1" in final_conclusion):
            debate_winner = scenario_1
            debate_winner_id = scenario_1["scenario_id"]
            print(f"🏆 Collaborative winner: #{1} {scenario_1['team_id']}")
        elif ("BETTER OPTION: 2" in final_conclusion or
              "CONSENSUS WINNER: SCENARIO 2" in final_conclusion or 
              "WINNER: SCENARIO 2" in final_conclusion):
            debate_winner = scenario_2  
            debate_winner_id = scenario_2["scenario_id"]
            print(f"🏆 Collaborative winner: #{2} {scenario_2['team_id']}")
        else:
            # Fallback to #1 ranked if parsing fails
            debate_winner = scenario_1
            debate_winner_id = scenario_1["scenario_id"]
            print(f"⚠️ Collaborative result unclear - defaulting to #1 ranked: {scenario_1['team_id']}")
        
        print(f"📝 LLM debate conversation length: {len(debate_transcript)} characters")
        print(f"🔄 Debate rounds completed: {debate_result['conversation_rounds']}")
        
    except Exception as e:
        print(f"❌ Debate failed: {e}")
        # Fallback to #1 ranked
        debate_winner = scenario_1
        debate_winner_id = scenario_1["scenario_id"]
        debate_transcript = f"Debate failed due to error: {str(e)}. Defaulting to #1 ranked scenario."
    
    # Save debate results
    if configuration.save_intermediate_results:
        manager = get_output_manager(configuration.output_dir, configuration.phase)
        
        # Save full debate transcript
        manager.save_file("final_debate_transcript.md", debate_transcript, "debate")
        
        # Save debate summary
        debate_summary = f"""# Final Debate Results
        
**Participants:**
- Scenario 1: {scenario_1['team_id']} (#{scenario_1['rank']}, {scenario_1['final_elo_rating']:.0f} Elo)
- Scenario 2: {scenario_2['team_id']} (#{scenario_2['rank']}, {scenario_2['final_elo_rating']:.0f} Elo)

**Winner:** {debate_winner['team_id']}

**Goal:** {goal}

**Criteria:** {preferences}

**Decision:** The collaborative analysis concluded that {"Scenario 1" if debate_winner_id == scenario_1["scenario_id"] else "Scenario 2"} provides the superior solution based on the established criteria.
"""
        manager.save_file("debate_summary.md", debate_summary, "debate")
        
        # Save debate outcome data for evolution use
        debate_outcome = {
            "winner_id": debate_winner_id,
            "winner_rank": debate_winner["rank"],
            "losing_scenario_id": scenario_2["scenario_id"] if debate_winner_id == scenario_1["scenario_id"] else scenario_1["scenario_id"],
            "losing_scenario_rank": scenario_2["rank"] if debate_winner_id == scenario_1["scenario_id"] else scenario_1["rank"],
            "goal": goal,
            "criteria": preferences,
            "key_strengths": f"Collaborative analysis identified superior performance in: {preferences}",
            "comparative_analysis": f"Debate winner demonstrated stronger performance compared to the #{'2' if debate_winner_id == scenario_1['scenario_id'] else '1'} ranked scenario through structured expert analysis.",
            "evolution_guidance": f"Future evolution should focus on maintaining the winning elements while addressing any weaknesses identified in the collaborative evaluation.",
            "transcript_excerpt": debate_transcript[:500] + "..." if len(debate_transcript) > 500 else debate_transcript
        }
        manager.save_json("debate_outcome.json", debate_outcome, "debate")
    
    # Create comprehensive debate summary for evolution phase
    debate_summary_for_evolution = f"""DEBATE OUTCOME ANALYSIS:

Winner: {debate_winner['team_id']} (Originally ranked #{debate_winner['rank']})
Defeated: {"#2" if debate_winner_id == scenario_1["scenario_id"] else "#1"} ranked scenario

Collaborative Analysis Decision Criteria:
{preferences}

Key Decision Factors:
- The winning scenario demonstrated superior performance across the established criteria
- Collaborative analysis conducted structured evaluation comparing both approaches
- Decision based on: {goal}

Evolution Guidance:
- Maintain the core strengths that led to debate victory
- Address any weaknesses identified during collaborative evaluation
- Build upon the winning approach's foundation

Debate Context:
This scenario emerged as the final champion after defeating the other top-ranked scenario in structured expert analysis, indicating strong foundational elements worth preserving and enhancing."""
    
    return {
        "debate_winner": debate_winner,
        "debate_transcript": debate_transcript,
        "debate_participants": [scenario_1, scenario_2],
        "debate_summary_for_evolution": debate_summary_for_evolution,
        "debate_outcome": debate_outcome if configuration.save_intermediate_results else None,
        "debate_complete": True
    }

def route_after_reflection(state: CoScientistState, config: RunnableConfig) -> Literal["tournament", "meta_review"]:
    """Route after reflection based on process depth."""
    configuration = CoScientistConfiguration.from_runnable_config(config)
    enabled_phases = configuration.get_enabled_phases_for_depth()
    
    if "tournament" in enabled_phases:
        return "tournament"
    else:
        return "meta_review"

def route_after_tournament(state: CoScientistState, config: RunnableConfig) -> Literal["ranking", "meta_review"]:
    """Route after tournament to ranking phase."""
    return "ranking"

def route_after_ranking(state: CoScientistState, config: RunnableConfig) -> Literal["debate", "meta_review"]:
    """Route after ranking - always go to debate if enabled, otherwise meta_review."""
    configuration = CoScientistConfiguration.from_runnable_config(config)
    enabled_phases = configuration.get_enabled_phases_for_depth()
    
    # Always go to debate if we have ranking data, otherwise skip to meta_review
    if "debate" in enabled_phases:
        return "debate"
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

def route_after_debate(state: CoScientistState, config: RunnableConfig) -> Literal["evolution", "meta_review"]:
    """Route after debate based on process depth."""
    configuration = CoScientistConfiguration.from_runnable_config(config)
    enabled_phases = configuration.get_enabled_phases_for_depth()
    
    if "evolution" in enabled_phases:
        return "evolution"
    else:
        return "meta_review"

co_scientist_builder = StateGraph(CoScientistState, input=CoScientistInputState, config_schema=CoScientistConfiguration)

# Add nodes for each phase
co_scientist_builder.add_node("meta_analysis", meta_analysis_phase)
co_scientist_builder.add_node("scenario_generation", parallel_scenario_generation)
co_scientist_builder.add_node("reflection", reflection_phase)
co_scientist_builder.add_node("tournament", tournament_phase)
co_scientist_builder.add_node("ranking", ranking_phase)
co_scientist_builder.add_node("debate", debate_phase)
co_scientist_builder.add_node("evolution", evolution_phase)
co_scientist_builder.add_node("evolution_tournament", evolution_tournament_phase)
co_scientist_builder.add_node("meta_review", final_meta_review_phase)

# Define the dynamic workflow edges
co_scientist_builder.add_edge(START, "meta_analysis")
co_scientist_builder.add_edge("meta_analysis", "scenario_generation")
co_scientist_builder.add_conditional_edges("scenario_generation", route_after_generation)
co_scientist_builder.add_conditional_edges("reflection", route_after_reflection)
co_scientist_builder.add_conditional_edges("tournament", route_after_tournament)
co_scientist_builder.add_conditional_edges("ranking", route_after_ranking)
co_scientist_builder.add_conditional_edges("debate", route_after_debate)
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

async def conduct_llm_vs_llm_debate(use_case: str, debate_type: str, configuration, num_directions: int = 3, **kwargs) -> dict:
    """Conduct collaborative consultation conversation between two LLM instances."""
    
    print(f"🗣️ Starting LLM vs LLM debate for {debate_type}")
    
    # Create two isolated LLM instances
    llm_a = create_isolated_model_instance(
        model_name=configuration.general_model,
        max_tokens=4096,
        temperature=0.8  # Slightly creative for debate
    )
    
    llm_b = create_isolated_model_instance(
        model_name=configuration.general_model,
        max_tokens=4096,
        temperature=0.8  # Slightly creative for debate
    )
    
    # Initialize conversation
    conversation_history = []
    
    if debate_type == "meta_analysis":
        # Meta-analysis debate: Generate research directions
        
        # Map state parameters to template parameters for each use case
        template_kwargs = kwargs.copy()
        context_value = kwargs.get("context", "")
        
        if use_case == "scenario_generation":
            template_kwargs["storyline"] = kwargs.get("reference_material", "")
            template_kwargs["world_building_questions"] = context_value
            template_kwargs["target_year"] = kwargs.get("target_year", "future")
        elif use_case == "storyline_creation":
            template_kwargs["story_concept"] = context_value
            template_kwargs["source_content"] = kwargs.get("reference_material", "")
        elif use_case == "chapter_writing":
            template_kwargs["storyline"] = kwargs.get("storyline", "")
            template_kwargs["chapter_arcs"] = kwargs.get("chapter_arcs", "")
        elif use_case == "linguistic_evolution":
            template_kwargs["source_content"] = kwargs.get("reference_material", "")
            template_kwargs["target_year"] = kwargs.get("target_year", "future")
            template_kwargs["years_in_future"] = kwargs.get("years_in_future", "many")
        elif use_case == "storyline_adjustment":
            template_kwargs["source_content"] = kwargs.get("reference_material", "")
        elif use_case == "chapter_rewriting":
            template_kwargs["source_content"] = kwargs.get("reference_material", "")
        elif use_case in ["chapter_arcs_creation", "chapter_arcs_adjustment"]:
            template_kwargs["story_concept"] = context_value
            template_kwargs["source_content"] = kwargs.get("reference_material", "")
        
        # LLM A makes opening proposal
        prompt_a = get_debate_participant_prompt(use_case, "A", num_directions=num_directions, **template_kwargs)
        print("🤖 LLM A: Making opening proposals...")
        
        response_a = await llm_a.ainvoke([HumanMessage(content=prompt_a)])
        proposals_a = response_a.content
        
        conversation_history.append(f"**LLM A Opening Proposals:**\n{proposals_a}\n")
        print(f"  ✅ LLM A proposed {num_directions} directions")
        
        # LLM B responds with counter-proposals and critique
        prompt_b = get_debate_participant_prompt(use_case, "B", 
                                                num_directions=num_directions, 
                                                debater_a_proposals=proposals_a,
                                                **template_kwargs)
        print("🤖 LLM B: Making counter-proposals and critique...")
        
        response_b = await llm_b.ainvoke([HumanMessage(content=prompt_b)])
        proposals_b = response_b.content
        
        conversation_history.append(f"**LLM B Counter-Proposals & Critique:**\n{proposals_b}\n")
        print(f"  ✅ LLM B responded with critique and {num_directions} alternatives")
        
        # Continue debate for 2-3 more rounds
        for round_num in range(2, 5):  # Rounds 2, 3, 4
            print(f"🔄 Debate Round {round_num}...")
            
            # LLM A responds to B's critique
            debate_context = "\n".join(conversation_history)
            prompt_a_continue = f"""Continue the debate. You are Debater A.

Previous conversation:
{debate_context}

Respond to Debater B's critique and proposals. Defend your directions and/or critique theirs. Work toward consensus on the best {num_directions} research directions.

If you think you've reached consensus, conclude with:
FINAL CONSENSUS:
Direction 1: [Name]
Core Assumption: [Key assumption]
Focus: [What this emphasizes]

Direction 2: [Name]
Core Assumption: [Key assumption]
Focus: [What this emphasizes]

[Continue for {num_directions} directions]"""

            response_a_continue = await llm_a.ainvoke([HumanMessage(content=prompt_a_continue)])
            response_a_text = response_a_continue.content
            
            conversation_history.append(f"**LLM A Round {round_num}:**\n{response_a_text}\n")
            
            # Check if consensus reached
            if "FINAL CONSENSUS:" in response_a_text:
                print(f"  ✅ Consensus reached in round {round_num}!")
                final_conclusion = response_a_text
                break
            
            # LLM B responds
            debate_context = "\n".join(conversation_history)
            prompt_b_continue = f"""Continue the debate. You are Debater B.

Previous conversation:
{debate_context}

Respond to Debater A's latest arguments. Work toward consensus on the best {num_directions} research directions.

If you think you've reached consensus, conclude with:
FINAL CONSENSUS:
Direction 1: [Name]
Core Assumption: [Key assumption]
Focus: [What this emphasizes]

Direction 2: [Name]
Core Assumption: [Key assumption]
Focus: [What this emphasizes]

[Continue for {num_directions} directions]"""

            response_b_continue = await llm_b.ainvoke([HumanMessage(content=prompt_b_continue)])
            response_b_text = response_b_continue.content
            
            conversation_history.append(f"**LLM B Round {round_num}:**\n{response_b_text}\n")
            
            # Check if consensus reached
            if "FINAL CONSENSUS:" in response_b_text:
                print(f"  ✅ Consensus reached in round {round_num}!")
                final_conclusion = response_b_text
                break
                
            final_conclusion = response_b_text  # Use last response if no consensus marker
    
    elif debate_type == "tournament":
        # Tournament debate: Pick winner between 2 scenarios
        
        # LLM A argues for scenario 1
        prompt_a = get_tournament_debate_participant_prompt(use_case, "A", **kwargs)
        print("🤖 LLM A: Arguing for Scenario 1...")
        
        response_a = await llm_a.ainvoke([HumanMessage(content=prompt_a)])
        argument_a = response_a.content
        
        conversation_history.append(f"**LLM A (Advocating Scenario 1):**\n{argument_a}\n")
        
        # LLM B argues for scenario 2
        prompt_b = get_tournament_debate_participant_prompt(use_case, "B", 
                                                          debater_a_argument=argument_a,
                                                          **kwargs)
        print("🤖 LLM B: Arguing for Scenario 2...")
        
        response_b = await llm_b.ainvoke([HumanMessage(content=prompt_b)])
        argument_b = response_b.content
        
        conversation_history.append(f"**LLM B (Advocating Scenario 2):**\n{argument_b}\n")
        
        # Final round: both make concluding arguments
        debate_context = "\n".join(conversation_history)
        
        # LLM A final argument
        prompt_a_final = f"""Make your final collaborative assessment. Previous consultation:

{debate_context}

Give your concluding assessment and declare the better option:
BETTER OPTION: 1 or BETTER OPTION: 2"""

        response_a_final = await llm_a.ainvoke([HumanMessage(content=prompt_a_final)])
        final_a = response_a_final.content
        
        conversation_history.append(f"**LLM A Final Argument:**\n{final_a}\n")
        
        # LLM B final argument
        prompt_b_final = f"""Make your final collaborative assessment. Previous consultation:

{debate_context}

Give your concluding assessment and declare the better option:
BETTER OPTION: 1 or BETTER OPTION: 2"""

        response_b_final = await llm_b.ainvoke([HumanMessage(content=prompt_b_final)])
        final_b = response_b_final.content
        
        conversation_history.append(f"**LLM B Final Argument:**\n{final_b}\n")
        
        # Determine winner based on collaborative consensus
        if (("BETTER OPTION: 1" in final_a or "WINNER: SCENARIO 1" in final_a) and 
            ("BETTER OPTION: 1" in final_b or "WINNER: SCENARIO 1" in final_b)):
            final_conclusion = "BETTER OPTION: 1 (Consensus)"
        elif (("BETTER OPTION: 2" in final_a or "WINNER: SCENARIO 2" in final_a) and 
              ("BETTER OPTION: 2" in final_b or "WINNER: SCENARIO 2" in final_b)):
            final_conclusion = "BETTER OPTION: 2 (Consensus)"
        elif "BETTER OPTION: 1" in final_b or "WINNER: SCENARIO 1" in final_b:
            final_conclusion = "BETTER OPTION: 1 (Expert B conclusion)"
        elif "BETTER OPTION: 2" in final_a or "WINNER: SCENARIO 2" in final_a:
            final_conclusion = "BETTER OPTION: 2 (Expert A conclusion)"
        else:
            # Default to LLM B's choice (they had last word)
            final_conclusion = final_b
    
    full_conversation = "\n".join(conversation_history)
    
    print(f"🏁 LLM debate completed. Total conversation length: {len(full_conversation)} characters")
    
    return {
        "full_conversation": full_conversation,
        "final_conclusion": final_conclusion,
        "conversation_rounds": len(conversation_history),
        "debate_type": debate_type
    }

def parse_debate_result_directions(conclusion_text: str) -> list:
    """Parse research directions from LLM collaborative consultation conclusion."""
    directions = []
    
    # Look for FINAL CONSENSUS section
    if "FINAL CONSENSUS:" in conclusion_text:
        lines = conclusion_text.split("FINAL CONSENSUS:")[1].split('\n')
    else:
        lines = conclusion_text.split('\n')
    
    current_direction = None
    
    for line in lines:
        line = line.strip()
        
        # Look for direction headers
        if line.startswith('Direction ') and ':' in line:
            if current_direction:
                directions.append(current_direction)
            
            direction_name = line.split(':', 1)[1].strip()
            current_direction = {
                "name": direction_name,
                "assumption": "",  # Maps to core_focus for backward compatibility
                "focus": ""        # Maps to research_approach for backward compatibility
            }
        
        elif current_direction:
            # Support both old format (for backward compatibility) and new collaborative format
            if line.startswith('Core Assumption:'):
                current_direction["assumption"] = line.split(':', 1)[1].strip()
            elif line.startswith('Core Focus:'):
                current_direction["assumption"] = line.split(':', 1)[1].strip()  # Map to assumption field
            elif line.startswith('Focus:'):
                current_direction["focus"] = line.split(':', 1)[1].strip()
            elif line.startswith('Research Approach:'):
                current_direction["focus"] = line.split(':', 1)[1].strip()  # Map to focus field
    
    # Add the last direction
    if current_direction:
        directions.append(current_direction)
    
    return directions

def format_debate_directions_summary(research_directions: list, debate_result: dict) -> str:
    """Format debate directions for file output."""
    content = "# LLM vs LLM Debate - Selected Research Directions\n\n"
    content += f"**Debate Type:** {debate_result['debate_type']}\n"
    content += f"**Conversation Rounds:** {debate_result['conversation_rounds']}\n\n"
    
    for i, direction in enumerate(research_directions, 1):
        content += f"## Direction {i}: {direction['name']}\n\n"
        content += f"**Core Assumption:** {direction.get('assumption', '')}\n\n"
        content += f"**Focus:** {direction.get('focus', '')}\n\n"
        content += "---\n\n"
    
    content += "## Debate Process\n\n"
    content += "This result was generated through an actual conversation between two AI debaters, "
    content += "each taking different perspectives and working toward consensus through collaborative consultation.\n"
    
    return content