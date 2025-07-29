"""
Elo Rating System - Competitive Ranking for Co-Scientist Scenarios

This module provides a robust Elo rating system for tracking scenario performance
in tournament competitions. It's extracted from the main co_scientist module to
improve organization and make the rating system reusable.

Key Features:
- Standard Elo rating algorithm with configurable K-factor
- Quality-based initialization for fair starting ratings
- Complete rating history tracking for analysis
- Statistical analysis tools for leaderboard generation
- Clean, well-documented interface for easy integration

Usage Example:
    elo_tracker = EloTracker(k_factor=32)
    elo_tracker.initialize_from_quality(scenarios, quality_weight=0.6)
    result = elo_tracker.update_ratings(winner_id, loser_id)
    leaderboard = elo_tracker.get_leaderboard()
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any


class EloTracker:
    """
    Elo rating system for scenario competitions.
    
    This class implements the standard Elo rating algorithm used in chess and other
    competitive games, adapted for Co-Scientist scenario evaluation. It provides:
    - Fair rating initialization based on quality scores
    - Dynamic rating updates based on tournament results
    - Complete history tracking for transparency
    - Statistical analysis tools for insights
    """
    
    def __init__(self, k_factor: int = 32):
        """
        Initialize Elo tracker with configurable parameters.
        
        Args:
            k_factor: Rating change sensitivity
                     - 16: Conservative (small rating changes, suitable for established ratings)
                     - 32: Standard (balanced, good for most scenarios)
                     - 64: Volatile (large rating changes, good for rapid sorting)
        """
        self.ratings: Dict[str, float] = {}  # scenario_id -> current_elo_rating
        self.k_factor = k_factor
        self.rating_history: Dict[str, List[Dict[str, Any]]] = {}  # scenario_id -> history_list
        self.default_rating = 1500  # Standard starting Elo rating (chess standard)
        
        print(f"📊 Elo tracker initialized with K-factor {k_factor}")
    
    def initialize_from_quality(self, scenarios: List[Dict[str, Any]], quality_weight: float = 0.6) -> None:
        """
        Initialize Elo ratings based on reflection quality scores.
        
        This gives scenarios fair starting ratings based on their initial quality assessment,
        rather than starting everyone at the same rating. This leads to more accurate
        tournaments since high-quality scenarios start with appropriately higher ratings.
        
        Args:
            scenarios: List of scenario dictionaries with quality_score field (0-100)
            quality_weight: How much quality influences initial rating (0.0-1.0)
                          - 0.0: All scenarios start at default rating (1500)
                          - 1.0: Maximum quality-based adjustment (±300 points)
                          - 0.6: Recommended balanced approach
        """
        if not scenarios:
            print("⚠️  No scenarios provided for Elo initialization")
            return
            
        quality_scores = []
        
        for scenario in scenarios:
            scenario_id = scenario.get("scenario_id")
            quality_score = scenario.get("quality_score", 50)  # Default neutral quality
            
            if not scenario_id:
                print(f"⚠️  Scenario missing ID, skipping: {scenario}")
                continue
            
            # Convert quality score (0-100) to Elo rating adjustment
            # Quality 50 → no adjustment (1500 baseline)
            # Quality 100 → +300 points (1800 maximum) 
            # Quality 0 → -300 points (1200 minimum)
            quality_adjustment = (quality_score - 50) * 6 * quality_weight  # Max ±180 at default weight
            initial_rating = self.default_rating + quality_adjustment
            
            # Keep within reasonable competitive bounds
            initial_rating = max(1200, min(1800, initial_rating))
            
            self.ratings[scenario_id] = initial_rating
            quality_scores.append(quality_score)
            
            # Record this initialization in history
            self._record_rating_change(
                scenario_id, 
                initial_rating, 
                f"Initial rating from quality score {quality_score} (weight: {quality_weight})"
            )
        
        # Log initialization summary
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        avg_rating = sum(self.ratings.values()) / len(self.ratings) if self.ratings else 0
        print(f"📊 Initialized {len(self.ratings)} scenarios:")
        print(f"   Average quality: {avg_quality:.1f}/100")
        print(f"   Average starting Elo: {avg_rating:.0f}")
        print(f"   Rating range: {min(self.ratings.values()):.0f} - {max(self.ratings.values()):.0f}")
    
    def get_rating(self, scenario_id: str) -> float:
        """
        Get current Elo rating for a scenario.
        
        Args:
            scenario_id: Unique identifier for the scenario
            
        Returns:
            float: Current Elo rating (defaults to 1500 if not found)
        """
        return self.ratings.get(scenario_id, self.default_rating)
    
    def update_ratings(self, winner_id: str, loser_id: str, margin: float = 1.0) -> Dict[str, Any]:
        """
        Update Elo ratings after a pairwise comparison result.
        
        This is the core of the Elo system. It calculates expected win probabilities
        based on current ratings, then adjusts ratings based on the actual result.
        Upsets (underdog victories) cause larger rating changes than expected wins.
        
        Args:
            winner_id: Scenario ID of the comparison winner
            loser_id: Scenario ID of the comparison loser
            margin: Victory margin multiplier (currently unused, reserved for future)
            
        Returns:
            Dict containing detailed results of the rating update:
            - Before/after ratings for both scenarios
            - Rating changes applied
            - Expected win probability
            - Whether this was an upset victory
        """
        # Get current ratings (with defaults if scenarios are new)
        winner_rating = self.get_rating(winner_id)
        loser_rating = self.get_rating(loser_id)
        
        # Calculate expected scores using standard Elo formula
        # This gives the probability that each scenario should win based on ratings
        winner_expected = 1 / (1 + 10**((loser_rating - winner_rating) / 400))
        loser_expected = 1 - winner_expected
        
        # Actual scores (1 for win, 0 for loss)
        winner_actual = 1.0 * margin  # Currently margin=1.0, but could be used for decisive victories
        loser_actual = 0.0
        
        # Calculate rating changes using Elo formula
        # K-factor determines how much ratings can change per game
        winner_change = self.k_factor * (winner_actual - winner_expected)
        loser_change = self.k_factor * (loser_actual - loser_expected)
        
        # Apply rating changes
        new_winner_rating = winner_rating + winner_change
        new_loser_rating = loser_rating + loser_change
        
        self.ratings[winner_id] = new_winner_rating
        self.ratings[loser_id] = new_loser_rating
        
        # Record changes in history for transparency
        self._record_rating_change(winner_id, new_winner_rating, f"Beat {loser_id} (+{winner_change:.1f})")
        self._record_rating_change(loser_id, new_loser_rating, f"Lost to {winner_id} ({loser_change:.1f})")
        
        # Determine if this was an upset (underdog victory)
        was_upset = winner_expected < 0.5
        
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
            "upset": was_upset,
            "margin": margin
        }
    
    def get_leaderboard(self, scenarios: Optional[List[Dict[str, Any]]] = None) -> List[Tuple[str, float]]:
        """
        Get scenarios sorted by Elo rating in descending order.
        
        Args:
            scenarios: Optional list to filter ratings by specific scenarios
                      If None, returns all scenarios in the system
                      
        Returns:
            List of (scenario_id, rating) tuples sorted by rating (highest first)
        """
        if scenarios:
            # Filter to only provided scenarios
            relevant_ratings = {}
            for scenario in scenarios:
                scenario_id = scenario.get("scenario_id")
                if scenario_id:
                    relevant_ratings[scenario_id] = self.get_rating(scenario_id)
        else:
            # Use all ratings
            relevant_ratings = self.ratings.copy()
        
        # Sort by rating in descending order (highest first)
        leaderboard = sorted(relevant_ratings.items(), key=lambda x: x[1], reverse=True)
        
        return leaderboard
    
    def get_rating_history(self, scenario_id: str) -> List[Dict[str, Any]]:
        """
        Get complete rating history for a specific scenario.
        
        This provides transparency into how a scenario's rating evolved over time,
        including the reasons for each change (initial quality, tournament results, etc.)
        
        Args:
            scenario_id: Unique identifier for the scenario
            
        Returns:
            List of history entries, each containing:
            - timestamp: When the rating change occurred
            - rating: The new rating after the change
            - reason: Description of why the rating changed
        """
        return self.rating_history.get(scenario_id, [])
    
    def get_statistics(self) -> Dict[str, float]:
        """
        Get comprehensive Elo rating statistics for analysis.
        
        Returns:
            Dictionary containing:
            - count: Total number of rated scenarios
            - average: Mean rating across all scenarios
            - min/max: Rating range boundaries
            - std_dev: Standard deviation (measure of rating spread)
            - range: Difference between highest and lowest ratings
        """
        if not self.ratings:
            return {
                "count": 0,
                "average": 0,
                "min": 0,
                "max": 0,
                "std_dev": 0,
                "range": 0
            }
        
        ratings = list(self.ratings.values())
        count = len(ratings)
        average = sum(ratings) / count
        min_rating = min(ratings)
        max_rating = max(ratings)
        
        # Calculate standard deviation for rating distribution analysis
        variance = sum((rating - average) ** 2 for rating in ratings) / count
        std_dev = variance ** 0.5
        
        return {
            "count": count,
            "average": average,
            "min": min_rating,
            "max": max_rating,
            "std_dev": std_dev,
            "range": max_rating - min_rating
        }
    
    def get_scenario_performance_summary(self, scenario_id: str) -> Dict[str, Any]:
        """
        Get comprehensive performance summary for a specific scenario.
        
        Args:
            scenario_id: Unique identifier for the scenario
            
        Returns:
            Dictionary containing:
            - current_rating: Current Elo rating
            - initial_rating: Starting rating
            - total_change: Net rating change since start
            - games_played: Number of comparisons participated in
            - history: Complete rating history
            - percentile: Where this rating ranks among all scenarios (0-100)
        """
        if scenario_id not in self.ratings:
            return {"error": f"Scenario {scenario_id} not found in rating system"}
        
        current_rating = self.ratings[scenario_id]
        history = self.get_rating_history(scenario_id)
        
        # Calculate initial rating and total change
        initial_rating = history[0]["rating"] if history else self.default_rating
        total_change = current_rating - initial_rating
        games_played = len([h for h in history if "Beat" in h["reason"] or "Lost" in h["reason"]])
        
        # Calculate percentile ranking
        all_ratings = list(self.ratings.values())
        ratings_below = sum(1 for r in all_ratings if r < current_rating)
        percentile = (ratings_below / len(all_ratings)) * 100 if all_ratings else 0
        
        return {
            "scenario_id": scenario_id,
            "current_rating": current_rating,
            "initial_rating": initial_rating,
            "total_change": total_change,
            "games_played": games_played,
            "percentile": percentile,
            "history_entries": len(history),
            "history": history
        }
    
    def export_ratings_data(self) -> Dict[str, Any]:
        """
        Export all rating data for analysis or backup.
        
        Returns:
            Dictionary containing complete rating system state:
            - ratings: Current ratings for all scenarios
            - history: Complete rating history for all scenarios
            - statistics: System-wide statistics
            - metadata: System configuration (K-factor, default rating, etc.)
        """
        return {
            "ratings": self.ratings.copy(),
            "rating_history": {k: v.copy() for k, v in self.rating_history.items()},
            "statistics": self.get_statistics(),
            "metadata": {
                "k_factor": self.k_factor,
                "default_rating": self.default_rating,
                "total_scenarios": len(self.ratings),
                "export_timestamp": datetime.now().isoformat()
            }
        }
    
    # === Internal Helper Methods ===
    
    def _record_rating_change(self, scenario_id: str, new_rating: float, reason: str) -> None:
        """
        Internal method to record rating changes in history.
        
        This maintains a complete audit trail of all rating changes for transparency
        and debugging. Each entry includes when the change happened and why.
        """
        if scenario_id not in self.rating_history:
            self.rating_history[scenario_id] = []
        
        self.rating_history[scenario_id].append({
            "timestamp": datetime.now().isoformat(),
            "rating": new_rating,
            "reason": reason
        })


def create_elo_tracker(k_factor: int = 32) -> EloTracker:
    """
    Convenience function to create an Elo tracker with standard settings.
    
    Args:
        k_factor: Rating change sensitivity (16=conservative, 32=standard, 64=volatile)
        
    Returns:
        Configured EloTracker instance
        
    Example:
        elo = create_elo_tracker(k_factor=32)
        elo.initialize_from_quality(scenarios)
    """
    return EloTracker(k_factor=k_factor) 