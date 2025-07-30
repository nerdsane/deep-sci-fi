"""
Unified Output Manager - Centralized File Output System

This module replaces 15+ repetitive save functions with a single, flexible system.
It provides consistent file organization, automatic formatting, and easy-to-use templates.

Key Features:
- Template-driven content formatting eliminates repetitive formatting code
- Automatic directory organization with timestamped runs  
- Unified interface for all file types (markdown, JSON, structured data)
- Easy for new developers to add new content types
- Consistent file naming and organization across the entire system

Usage Example:
    output_manager = UnifiedOutputManager("output", "meta_analysis")
    output_manager.save_scenarios(scenarios_list)  # Automatic formatting + saving
    output_manager.save_leaderboard(leaderboard_data)  # Handles complex data structures
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class UnifiedOutputManager:
    """
    Centralized output manager that handles all file saving with consistent formatting.
    
    This class eliminates the repetitive patterns found in 15+ save functions by:
    - Using templates for consistent content formatting
    - Providing a unified interface for different data types
    - Automatically handling directory structure and file naming
    - Making it easy to add new content types
    """
    
    def __init__(self, base_output_dir: str = "output", phase: Optional[str] = None):
        """
        Initialize the output manager with automatic directory setup.
        
        Args:
            base_output_dir: Root directory for all outputs
            phase: Optional phase name for organized subdirectories
        """
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        phase_suffix = f"_{phase}" if phase else ""
        self.run_dir = Path(base_output_dir) / f"{self.timestamp}_coscientist{phase_suffix}"
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.file_counter = 0
        
        # Content templates for consistent formatting
        self._init_content_templates()
        
    def save_scenarios(self, scenarios: List[Dict[str, Any]], subdirectory: str = "scenarios") -> None:
        """
        Save scenario data with automatic formatting.
        
        Replaces: save_individual_scenarios()
        
        Args:
            scenarios: List of scenario dictionaries
            subdirectory: Subdirectory to save files in
        """
        if not scenarios:
            return
            
        for scenario in scenarios:
            content = self._format_scenario_content(scenario)
            scenario_id = scenario.get("scenario_id", "unknown")
            team_id = scenario.get("team_id", "unknown")
            filename = f"scenario_{scenario_id}_{team_id}.md"
            self._save_file(filename, content, subdirectory)
    
    def save_critiques(self, critiques: List[Dict[str, Any]], subdirectory: str = "critiques") -> None:
        """
        Save critique data with automatic formatting and domain organization.
        
        Replaces: save_individual_critiques()
        
        Args:
            critiques: List of critique dictionaries
            subdirectory: Subdirectory to save files in
        """
        if not critiques:
            return
            
        # Group by domain for better organization
        by_domain = self._group_critiques_by_domain(critiques)
        
        critique_counter = 1
        for domain, domain_critiques in by_domain.items():
            for critique in domain_critiques:
                content = self._format_critique_content(critique, critique_counter, domain)
                scenario_id = critique.get('target_scenario_id', 'unknown')
                filename = f"critique_{critique_counter:03d}_{domain}_{scenario_id}.md"
                self._save_file(filename, content, subdirectory)
                critique_counter += 1
    
    def save_tournament_comparisons(self, tournament_data: List[Dict[str, Any]], subdirectory: str = "tournaments") -> None:
        """
        Save tournament comparison data with structured formatting.
        
        Replaces: save_individual_tournament_comparisons()
        
        Args:
            tournament_data: List of tournament comparison dictionaries
            subdirectory: Subdirectory to save files in
        """
        if not tournament_data:
            return
            
        comparison_counter = 1
        for comparison in tournament_data:
            content = self._format_tournament_comparison_content(comparison, comparison_counter)
            direction = comparison.get('direction', 'unknown').replace(' ', '_')
            round_num = comparison.get('round', 'unknown')
            filename = f"tournament_{comparison_counter:03d}_{direction}_round_{round_num}.md"
            self._save_file(filename, content, subdirectory)
            comparison_counter += 1
    
    def save_evolution_attempts(self, evolutions: List[Dict[str, Any]], subdirectory: str = "evolutions") -> None:
        """
        Save evolution attempt data with strategy-based organization.
        
        Replaces: save_individual_evolution_attempts()
        
        Args:
            evolutions: List of evolution attempt dictionaries  
            subdirectory: Subdirectory to save files in
        """
        if not evolutions:
            return
            
        evolution_counter = 1
        for evolution in evolutions:
            content = self._format_evolution_content(evolution, evolution_counter)
            strategy = evolution.get('strategy', 'unknown')
            direction = evolution.get('original_direction', 'unknown').replace(' ', '_')
            filename = f"evolution_{evolution_counter:03d}_{strategy}_{direction}.md"
            self._save_file(filename, content, subdirectory)
            evolution_counter += 1
    
    def save_leaderboard(self, leaderboard_data: Dict[str, Any], subdirectory: str = "rankings") -> None:
        """
        Save leaderboard data with comprehensive formatting.
        
        Replaces: save_elo_leaderboard()
        
        Args:
            leaderboard_data: Dictionary containing leaderboard information
            subdirectory: Subdirectory to save files in
        """
        if not leaderboard_data:
            return
            
        # Generate markdown content using template
        content = self._format_leaderboard_content(leaderboard_data)
        filename = "elo_leaderboard.md"
        self._save_file(filename, content, subdirectory)
        
        # Also save raw JSON data for analysis
        json_filename = "leaderboard_data.json"
        self._save_json(json_filename, leaderboard_data, subdirectory)
    
    def save_final_winners(self, top_scenarios: List[Dict[str, Any]], state: Dict[str, Any], subdirectory: str = "final") -> None:
        """
        Save final winner data with detailed competition context.
        
        Replaces: save_final_winners()
        
        Args:
            top_scenarios: List of winning scenario dictionaries
            state: Full state containing competition context
            subdirectory: Subdirectory to save files in
        """
        if not top_scenarios:
            return
            
        for rank, scenario in enumerate(top_scenarios, 1):
            content = self._format_final_winner_content(scenario, rank, state)
            direction = scenario.get('research_direction', 'unknown').replace(' ', '_')
            filename = f"final_winner_{rank:02d}_{direction}.md"
            self._save_file(filename, content, subdirectory)
    
    def save_simple_content(self, filename: str, content: str, subdirectory: Optional[str] = None) -> None:
        """
        Save simple text content (replaces the basic save functions).
        
        Replaces: save_co_scientist_output() and similar basic functions
        
        Args:
            filename: Name of the file to save
            content: Text content to save
            subdirectory: Optional subdirectory
        """
        numbered_filename = self._get_next_filename(filename)
        self._save_file(numbered_filename, content, subdirectory)
    
    def save_structured_data(self, data_type: str, data: Any, **kwargs) -> None:
        """
        Generic interface for saving any type of structured data.
        
        This provides extensibility for new content types without adding new methods.
        
        Args:
            data_type: Type identifier (e.g., "scenarios", "critiques", "tournaments")
            data: The data to save
            **kwargs: Additional options (subdirectory, filename_prefix, etc.)
        """
        method_map = {
            "scenarios": self.save_scenarios,
            "critiques": self.save_critiques,
            "tournament_comparisons": self.save_tournament_comparisons,
            "evolution_attempts": self.save_evolution_attempts,
            "leaderboard": self.save_leaderboard,
            "final_winners": self.save_final_winners,
        }
        
        if data_type in method_map:
            if data_type == "final_winners":
                # Special case that requires state parameter
                state = kwargs.get("state", {})
                method_map[data_type](data, state, kwargs.get("subdirectory", data_type))
            else:
                method_map[data_type](data, kwargs.get("subdirectory", data_type))
        else:
            # Fallback for unknown types - save as JSON
            filename = kwargs.get("filename", f"{data_type}_data.json")
            subdirectory = kwargs.get("subdirectory", "misc")
            self._save_json(filename, data, subdirectory)
    
    # === Internal Helper Methods ===
    
    def _save_file(self, filename: str, content: str, subdirectory: Optional[str] = None) -> None:
        """Internal method to save a file with proper directory structure."""
        if subdirectory:
            save_dir = self.run_dir / subdirectory
            save_dir.mkdir(exist_ok=True)
        else:
            save_dir = self.run_dir
            
        filepath = save_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Co-scientist saved: {filepath}")
    
    def _save_json(self, filename: str, data: Dict[str, Any], subdirectory: Optional[str] = None) -> None:
        """Internal method to save JSON data."""
        if subdirectory:
            save_dir = self.run_dir / subdirectory
            save_dir.mkdir(exist_ok=True)
        else:
            save_dir = self.run_dir
            
        filepath = save_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        print(f"Co-scientist saved JSON: {filepath}")
    
    def _get_next_filename(self, name: str) -> str:
        """Generate next numbered filename."""
        self.file_counter += 1
        return f"{self.file_counter:02d}_{name}"
    
    def _group_critiques_by_domain(self, critiques: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group critiques by domain for better organization."""
        by_domain = {}
        for critique in critiques:
            domain = critique.get('critique_domain', 'general')
            if domain not in by_domain:
                by_domain[domain] = []
            by_domain[domain].append(critique)
        return by_domain
    
    # === Content Formatting Templates ===
    
    def _init_content_templates(self) -> None:
        """Initialize content formatting templates."""
        # This could be moved to a separate file if templates grow large
        pass
    
    def _format_scenario_content(self, scenario: Dict[str, Any]) -> str:
        """Format scenario data using consistent template."""
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
        if "quality_score" in scenario:
            content += f"\n\n## Quality Information\n\n"
            content += f"**Quality Score:** {scenario.get('quality_score', 0)}/100\n"
            content += f"**Advancement Recommendation:** {scenario.get('advancement_recommendation', 'N/A')}\n"
        
        return content
    
    def _format_critique_content(self, critique: Dict[str, Any], counter: int, domain: str) -> str:
        """Format critique data using consistent template."""
        scenario_id = critique.get('target_scenario_id', 'unknown')
        severity = critique.get('severity_score', 0)
        
        content = f"# Critique {counter:03d}\n\n"
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
        
        return content
    
    def _format_tournament_comparison_content(self, comparison: Dict[str, Any], counter: int) -> str:
        """Format tournament comparison data using consistent template."""
        direction = comparison.get('direction', 'unknown')
        round_num = comparison.get('round', 'unknown')
        scenario1_id = comparison.get('scenario1_id', 'unknown')
        scenario2_id = comparison.get('scenario2_id', 'unknown')
        
        # Handle winner_id which might be nested under 'winner'
        winner_id = comparison.get('winner_id', 'unknown')
        if winner_id == 'unknown':
            winner_data = comparison.get('winner', {})
            if isinstance(winner_data, dict):
                winner_id = winner_data.get('scenario_id', 'unknown')
            elif isinstance(winner_data, str):
                winner_id = winner_data
        
        content = f"# Tournament Comparison {counter:03d}\n\n"
        content += f"**Direction:** {direction}\n"
        content += f"**Round:** {round_num}\n"
        content += f"**Scenario 1 ID:** {scenario1_id}\n"
        content += f"**Scenario 2 ID:** {scenario2_id}\n"
        content += f"**Winner ID:** {winner_id}\n"
        content += f"**Generated:** {datetime.now().isoformat()}\n\n"
        
        content += "## Comparison Analysis\n\n"
        # Check multiple possible field names for comparison content
        comparison_content = comparison.get('comparison_content', 
                                          comparison.get('reasoning',
                                          comparison.get('analysis',
                                          comparison.get('content', 'No comparison content available'))))
        content += comparison_content
        
        return content
    
    def _format_evolution_content(self, evolution: Dict[str, Any], counter: int) -> str:
        """Format evolution attempt data using consistent template."""
        evolution_id = evolution.get('evolution_id', 'unknown')
        strategy = evolution.get('strategy', 'unknown')
        original_direction = evolution.get('original_direction', 'unknown')
        original_scenario_id = evolution.get('original_scenario_id', 'unknown')
        
        content = f"# Evolution Attempt {counter:03d}\n\n"
        content += f"**Evolution ID:** {evolution_id}\n"
        content += f"**Strategy:** {strategy}\n"
        content += f"**Original Direction:** {original_direction}\n"
        content += f"**Original Scenario ID:** {original_scenario_id}\n"
        content += f"**Timestamp:** {evolution.get('timestamp', 'unknown')}\n\n"
        
        content += "## Original Content\n\n"
        content += evolution.get('original_content', 'No original content available')
        content += "\n\n## Evolved Content\n\n"
        content += evolution.get('evolved_content', 'No evolved content available')
        
        return content
    
    def _format_leaderboard_content(self, leaderboard_data: Dict[str, Any]) -> str:
        """Format leaderboard data using comprehensive template."""
        content = "# Co-Scientist Elo Leaderboard\n\n"
        content += f"**Total Participants:** {leaderboard_data.get('total_participants', 0)}\n"
        content += f"**Generated:** {leaderboard_data.get('timestamp', 'Unknown')}\n\n"
        
        # Add Elo statistics if available
        elo_stats = leaderboard_data.get('elo_statistics', {})
        if elo_stats:
            content += "## Elo Rating Statistics\n\n"
            content += f"**Average Elo Rating:** {elo_stats.get('average', 0):.0f}\n"
            content += f"**Rating Range:** {elo_stats.get('min', 0):.0f} - {elo_stats.get('max', 0):.0f}\n"
            content += f"**Standard Deviation:** {elo_stats.get('std_dev', 0):.0f}\n"
            content += f"**Total Rating Spread:** {elo_stats.get('range', 0):.0f} points\n\n"
        
        # Add rankings table
        rankings = leaderboard_data.get('rankings', [])
        if rankings:
            content += "## Full Rankings\n\n"
            content += "| Rank | Team ID | Research Direction | Elo Rating | Change | W-L | Win Rate | Status |\n"
            content += "|------|---------|-------------------|------------|--------|-----|----------|--------|\n"
            
            for entry in rankings:
                status_emoji = self._get_performance_emoji(entry.get('performance_tier', ''))
                content += f"| {entry['rank']} | {entry['team_id']} | {entry['research_direction'][:20]}... | "
                content += f"{entry['final_elo_rating']:.0f} | {entry['elo_change']:+.0f} | "
                content += f"{entry['wins']}-{entry['losses']} | {entry['win_rate']:.1f}% | "
                content += f"{entry['tournament_placement']} {status_emoji} |\n"
        
        return content
    
    def _format_final_winner_content(self, scenario: Dict[str, Any], rank: int, state: Dict[str, Any]) -> str:
        """Format final winner data with comprehensive competition context."""
        research_direction = scenario.get('research_direction', 'Unknown')
        scenario_id = scenario.get('scenario_id', 'unknown')
        evolution_type = scenario.get('type', 'original')
        
        content = f"# Final Winner {rank}: {research_direction}\n\n"
        content += f"**Competition Rank:** #{rank} of 3 Final Winners\n"
        content += f"**Research Direction:** {research_direction}\n"
        content += f"**Scenario ID:** {scenario_id}\n"
        content += f"**Evolution Type:** {evolution_type}\n"
        content += f"**Selection Process:** {scenario.get('selection_reasoning', 'Won evolution tournament')}\n"
        content += f"**Generated:** {datetime.now().isoformat()}\n\n"
        
        # Add competition process summary
        total_scenarios = len(state.get('scenario_population', []))
        total_critiques = len(state.get('reflection_critiques', []))
        total_evolutions = len(state.get('evolved_scenarios', []))
        
        content += "## Competition Process\n\n"
        content += f"1. **Initial Generation**: One of 6 scenarios in the '{research_direction}' research direction\n"
        content += f"2. **Expert Reflection**: Critiqued by 5 domain experts across physics, biology, engineering, social science, and economics\n"
        content += f"3. **Tournament Competition**: Competed in quality-based brackets using Elo rating system\n"
        content += f"4. **Evolution Phase**: Enhanced through targeted improvements\n"
        content += f"5. **Final Selection**: Won evolution tournament to become final representative\n\n"
        
        content += "## Competition Statistics\n\n"
        content += f"- **Total Scenarios Generated:** {total_scenarios}\n"
        content += f"- **Expert Critiques Produced:** {total_critiques}\n"
        content += f"- **Evolution Attempts:** {total_evolutions}\n"
        content += f"- **Final Selection Rate:** {rank}/3 from {total_scenarios} initial scenarios ({(1/total_scenarios)*100:.2f}% selection rate)\n\n"
        
        content += "## Scenario Content\n\n"
        content += scenario.get('scenario_content', 'No content available')
        
        return content
    
    def _get_performance_emoji(self, tier: str) -> str:
        """Get emoji for performance tier."""
        emoji_map = {
            'elite': '🏆',
            'high_performer': '🥇', 
            'above_average': '📈',
            'average': '📊',
            'below_average': '📉'
        }
        return emoji_map.get(tier, '📊')


# Global output manager instance for backward compatibility
_global_output_manager = None

def get_output_manager(output_dir: str = "output", phase: Optional[str] = None) -> UnifiedOutputManager:
    """
    Get or create the global output manager instance.
    
    This maintains backward compatibility with existing code while providing
    the new unified interface.
    
    Args:
        output_dir: Base output directory
        phase: Optional phase name
        
    Returns:
        UnifiedOutputManager instance
    """
    global _global_output_manager
    if _global_output_manager is None:
        _global_output_manager = UnifiedOutputManager(output_dir, phase)
    return _global_output_manager

def reset_output_manager() -> None:
    """Reset the global output manager for a fresh run."""
    global _global_output_manager
    _global_output_manager = None 