"""
Content Formatters - Template-Driven Content Generation

This module replaces 15+ repetitive format functions with a unified, template-driven system.
It provides consistent formatting across all content types and makes it easy to add new formats.

Key Features:
- Template-driven formatting eliminates repetitive string building
- Consistent markdown structure across all content types
- Easy to extend with new content types
- Clear separation of data processing and presentation logic
- Well-documented for easy maintenance by new developers

Usage Example:
    formatter = ContentFormatter()
    summary = formatter.format_content("tournament_results", tournament_data)
    analysis = formatter.format_content("reflection_analysis", critique_data)
"""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime


class ContentFormatter:
    """
    Unified content formatter that replaces repetitive format functions.
    
    This class uses a template-driven approach to generate consistent markdown
    content for all data types in the Co-Scientist system. Instead of having
    15+ separate format functions with similar patterns, we have one flexible
    system that's easy to extend and maintain.
    """
    
    def __init__(self):
        """Initialize the formatter with content templates."""
        self._init_templates()
    
    def format_content(self, content_type: str, data: Any, **options) -> str:
        """
        Format any type of content using the appropriate template.
        
        This is the main interface that replaces all the individual format functions.
        It automatically selects the right template and applies consistent formatting.
        
        Args:
            content_type: Type of content to format (e.g., "tournament_results", "reflection_analysis")
            data: The data to format (list, dict, or other structure)
            **options: Additional formatting options (title, subtitle, etc.)
            
        Returns:
            str: Formatted markdown content
            
        Example:
            # Instead of format_tournament_results(winners, all_results)
            content = formatter.format_content("tournament_results", {"winners": winners, "all_results": all_results})
        """
        # Map content types to their formatting methods
        format_methods = {
            "tournament_analysis": self._format_tournament_analysis,
            "reflection_analysis": self._format_reflection_analysis,
            "evolution_analysis": self._format_evolution_analysis,
            "competition_summary": self._format_competition_summary,
            "scenario_population": self._format_scenario_population,
            "reflection_critiques": self._format_reflection_critiques,
            "tournament_results": self._format_tournament_results,
            "evolution_results": self._format_evolution_results,
            "complete_summary": self._format_complete_summary,
            "evolution_tournament_results": self._format_evolution_tournament_results,
            "research_directions": self._format_research_directions,
            "unified_reflection_critiques": self._format_unified_reflection_critiques,
            "debate_directions_summary": self._format_debate_directions_summary,
            "chat_conversation": self._format_chat_conversation,
            "conversation_context": self._format_conversation_context,
        }
        
        if content_type in format_methods:
            return format_methods[content_type](data, **options)
        else:
            # Fallback for unknown content types
            return self._format_generic_content(content_type, data, **options)
    
    # === Core Analysis Formatters ===
    
    def _format_tournament_analysis(self, tournament_comparisons: List[Dict[str, Any]], **options) -> str:
        """Format tournament comparison data for meta-analysis."""
        if not tournament_comparisons:
            return "No tournament comparisons available."
        
        analysis = f"Tournament Analysis: {len(tournament_comparisons)} pairwise comparisons conducted.\n"
        analysis += "Key patterns in decision-making and reasoning quality observed in tournament process."
        return analysis
    
    def _format_reflection_analysis(self, reflection_critiques: List[Dict[str, Any]], **options) -> str:
        """Format reflection critique data for meta-analysis."""
        if not reflection_critiques:
            return "No reflection critiques available."
        
        analysis = f"Reflection Analysis: {len(reflection_critiques)} expert critiques conducted.\n"
        analysis += "Domain expert analysis patterns and quality assessments from reflection phase."
        return analysis
    
    def _format_evolution_analysis(self, evolved_scenarios: List[Dict[str, Any]], **options) -> str:
        """Format evolution scenario data for meta-analysis."""
        if not evolved_scenarios:
            return "No evolved scenarios available."
        
        analysis = f"Evolution Analysis: {len(evolved_scenarios)} evolution attempts conducted.\n"
        analysis += "Improvement patterns and enhancement strategies from evolution phase."
        return analysis
    
    def _format_competition_summary(self, state: Dict[str, Any], **options) -> str:
        """Format high-level competition process summary."""
        directions = state.get('research_directions', [])
        scenarios = state.get('scenario_population', [])
        
        summary = "## Competition Process Summary\n\n"
        summary += f"- {len(directions)} research directions explored\n"
        summary += f"- {len(scenarios)} total scenarios generated\n"
        summary += "- Multi-phase competitive evaluation process completed\n"
        summary += "- Quality-based selection through expert review and tournaments\n"
        
        return summary
    
    # === Detailed Data Formatters ===
    
    def _format_scenario_population(self, scenarios: List[Dict[str, Any]], **options) -> str:
        """Format scenario population for detailed analysis."""
        if not scenarios:
            return "No scenarios available."
        
        content = "# Scenario Population Analysis\n\n"
        content += f"**Total Scenarios Generated:** {len(scenarios)}\n\n"
        
        # Group by research direction for better organization
        by_direction = self._group_by_field(scenarios, 'research_direction')
        
        for direction, direction_scenarios in by_direction.items():
            content += f"## Direction: {direction}\n\n"
            content += f"**Scenarios in Direction:** {len(direction_scenarios)}\n\n"
            
            for i, scenario in enumerate(direction_scenarios):
                scenario_id = scenario.get('scenario_id', 'unknown')
                content += f"### Scenario {i} (Team: {scenario.get('team_id', 'Unknown')})\n"
                content += f"**Generated:** {scenario.get('generation_timestamp', 'Unknown')}\n\n"
                
                # Show content preview (first 200 characters)
                scenario_content = scenario.get('scenario_content', '')
                preview = scenario_content[:200] + "..." if len(scenario_content) > 200 else scenario_content
                content += f"{preview}\n\n"
        
        return content
    
    def _format_reflection_critiques(self, critiques: List[Dict[str, Any]], **options) -> str:
        """Format reflection critiques with quality analysis."""
        if not critiques:
            return "No reflection critiques available."
        
        content = "# Reflection Critiques Summary\n\n"
        content += f"**Total Critiques Generated:** {len(critiques)}\n\n"
        
        # Calculate quality statistics
        quality_scores = [c.get('overall_quality_score', 0) for c in critiques if c.get('overall_quality_score')]
        if quality_scores:
            avg_quality = sum(quality_scores) / len(quality_scores)
            content += f"**Average Quality Score:** {avg_quality:.1f}/100\n"
            content += f"**Quality Range:** {min(quality_scores)}-{max(quality_scores)}/100\n\n"
        
        # Group by domain
        by_domain = self._group_by_field(critiques, 'critique_domain')
        
        for domain, domain_critiques in by_domain.items():
            content += f"## {domain.title()} Domain Critiques\n\n"
            content += f"**Critiques in Domain:** {len(domain_critiques)}\n\n"
            
            # Show quality distribution
            domain_scores = [c.get('overall_quality_score', 0) for c in domain_critiques if c.get('overall_quality_score')]
            if domain_scores:
                high_quality = [s for s in domain_scores if s >= 80]
                medium_quality = [s for s in domain_scores if 60 <= s < 80]
                
                content += f"**High Quality (80-100):** {len(high_quality)} scenarios\n"
                content += f"**Medium Quality (60-79):** {len(medium_quality)} scenarios\n"
                content += f"**Below 60:** {len(domain_scores) - len(high_quality) - len(medium_quality)} scenarios\n\n"
            
            # Show individual critiques
            for i, critique in enumerate(domain_critiques[:3]):  # Show first 3 as examples
                scenario_id = critique.get('target_scenario_id', 'unknown')
                quality_score = critique.get('overall_quality_score', 0)
                
                content += f"### {i}. Scenario {scenario_id}\n\n"
                content += f"**Overall Quality Score:** {quality_score}/100\n"
                
                # Show critique preview
                critique_content = critique.get('critique_content', '')
                preview = critique_content[:200] + "..." if len(critique_content) > 200 else critique_content
                content += f"**Critique Preview:** {preview}\n\n"
        
        return content
    
    def _format_tournament_results(self, data: Dict[str, Any], **options) -> str:
        """Format tournament results with comprehensive statistics."""
        winners = data.get('winners', [])
        all_results = data.get('all_results', [])
        
        if not winners:
            return "No tournament winners available."
        
        content = "# Tournament Results Summary\n\n"
        content += f"**Total Tournaments Completed:** {len(all_results)}\n"
        content += f"**Direction Winners Selected:** {len(winners)}\n\n"
        
        # Calculate overall statistics
        all_quality_scores = [w.get('quality_score', 0) for w in winners if w.get('quality_score')]
        all_elo_ratings = [w.get('final_elo_rating', 1500) for w in winners if w.get('final_elo_rating')]
        
        if all_quality_scores:
            avg_quality = sum(all_quality_scores) / len(all_quality_scores)
            content += f"**Average Winner Quality Score:** {avg_quality:.1f}/100\n"
            content += f"**Quality Range:** {min(all_quality_scores)}-{max(all_quality_scores)}/100\n"
        
        if all_elo_ratings:
            avg_elo = sum(all_elo_ratings) / len(all_elo_ratings)
            content += f"**Average Winner Elo Rating:** {avg_elo:.0f}\n"
            content += f"**Elo Range:** {min(all_elo_ratings):.0f}-{max(all_elo_ratings):.0f}\n"
        
        # Add elo statistics if available
        elo_stats = data.get('elo_statistics', {})
        if elo_stats:
            content += f"\n**Overall Elo Statistics:**\n"
            content += f"- Total Scenarios: {elo_stats['count']}\n"
            content += f"- Average Rating: {elo_stats['average']:.0f}\n"
            content += f"- Rating Range: {elo_stats['min']:.0f} - {elo_stats['max']:.0f}\n\n"
        
        # Detail each tournament
        for i, result in enumerate(all_results):
            direction = result.get('direction', 'Unknown')
            rounds = result.get('rounds', 0)
            winner = result.get('winner', {})
            
            content += f"## Tournament {i}: {direction}\n"
            content += f"**Rounds Completed:** {rounds}\n"
            
            if winner:
                team_id = winner.get('team_id', 'unknown')
                quality_score = winner.get('quality_score', 0)
                content += f"**Winner Team:** {team_id}\n"
                content += f"**Quality Score:** {quality_score}/100\n"
                
                # Add round details if available
                tournament_rounds = result.get('tournament_rounds', [])
                for round_num, round_data in enumerate(tournament_rounds, 1):
                    content += f"### Round {round_num}\n\n"
                    content += f"**Participants:** {len(round_data.get('participants', []))}\n"
                    content += f"**Comparisons:** {len(round_data.get('comparisons', []))}\n\n"
            
            content += "\n"
        
        return content
    
    def _format_evolution_results(self, evolved_scenarios: List[Dict[str, Any]], **options) -> str:
        """Format evolution results with improvement analysis."""
        if not evolved_scenarios:
            return "No evolved scenarios available."
        
        content = "# Evolution Results Summary\n\n"
        content += f"**Total Evolution Attempts:** {len(evolved_scenarios)}\n\n"
        
        # Group by strategy
        by_strategy = self._group_by_field(evolved_scenarios, 'strategy')
        
        for strategy, strategy_evolutions in by_strategy.items():
            content += f"## {strategy.title()} Strategy\n\n"
            content += f"**Evolutions Using Strategy:** {len(strategy_evolutions)}\n\n"
            
            for evolution in strategy_evolutions:
                direction = evolution.get('original_direction', 'Unknown')
                evolution_id = evolution.get('evolution_id', 'unknown')
                
                content += f"### Evolution: {evolution_id}\n"
                content += f"**Original Direction:** {direction}\n"
                content += f"**Strategy Applied:** {strategy}\n"
                
                # Show improvement summary if available
                improvement = evolution.get('improvement_summary', '')
                if improvement:
                    content += f"**Improvement:** {improvement}\n"
                
                content += "\n"
        
        return content
    
    def _format_complete_summary(self, data: Dict[str, Any], **options) -> str:
        """Format complete workflow summary with all phases."""
        state = data.get('state', {})
        top_scenarios = data.get('top_scenarios', [])
        competition_summary = data.get('competition_summary', '')
        
        content = "# Complete Co-Scientist Workflow Summary\n\n"
        content += f"**Generated:** {datetime.now().isoformat()}\n\n"
        
        # Add research directions overview
        directions = state.get('research_directions', [])
        if directions:
            content += "## Research Directions Explored\n\n"
            for i, direction in enumerate(directions, 1):
                direction_name = direction.get('name', 'Unknown')
                direction_assumption = direction.get('assumption', 'N/A')
                content += f"### Direction {i}: {direction_name}\n"
                content += f"- **Assumption:** {direction_assumption}\n\n"
        
        # Add phase statistics
        population = state.get('scenario_population', [])
        critiques = state.get('reflection_critiques', [])
        winners = state.get('tournament_winners', [])
        evolved = state.get('evolved_scenarios', [])
        
        content += "## Workflow Statistics\n\n"
        content += f"- **Scenarios Generated:** {len(population)}\n"
        content += f"- **Critiques Produced:** {len(critiques)}\n"
        content += f"- **Tournament Winners:** {len(winners)}\n"
        content += f"- **Evolution Attempts:** {len(evolved)}\n\n"
        
        # Add competition summary if provided
        if competition_summary:
            content += "## Competition Analysis\n\n"
            content += competition_summary + "\n\n"
        
        # Add final results
        if top_scenarios:
            content += "## Final Selected Scenarios\n\n"
            for i, scenario in enumerate(top_scenarios, 1):
                direction = scenario.get('research_direction', 'Unknown')
                team_id = scenario.get('team_id', 'unknown')
                content += f"{i}. **{direction}** (Team: {team_id})\n"
        
        return content
    
    # === Specialized Formatters ===
    
    def _format_evolution_tournament_results(self, final_representatives: List[Dict[str, Any]], **options) -> str:
        """Format evolution tournament results."""
        if not final_representatives:
            return "No evolution tournament results available."
        
        content = "# Evolution Tournament Results\n\n"
        content += f"**Final Representatives Selected:** {len(final_representatives)}\n\n"
        
        for i, result in enumerate(final_representatives):
            direction = result.get('direction', 'Unknown')
            rounds = result.get('rounds', 0)
            final_winner = result.get('final_winner', {})
            
            content += f"## Evolution Tournament {i}: {direction}\n"
            content += f"**Rounds Completed:** {rounds}\n"
            
            if final_winner:
                winner_type = final_winner.get('type', 'unknown')
                team_id = final_winner.get('team_id', 'unknown')
                content += f"**Final Winner Type:** {winner_type}\n"
                content += f"**Winner Team:** {team_id}\n"
            
            content += "\n"
        
        return content
    
    def _format_research_directions(self, directions: List[Dict[str, Any]], **options) -> str:
        """Format research directions for display."""
        if not directions:
            return "No research directions available."
        
        formatted = "# Research Directions\n\n"
        for i, direction in enumerate(directions, 1):
            direction_name = direction.get('name', 'Unknown')
            assumption = direction.get('assumption', 'N/A')
            
            formatted += f"Direction {i}: {direction_name}\n"
            formatted += f"  Assumption: {assumption}\n"
            if i < len(directions):
                formatted += "\n"
        
        return formatted
    
    def _format_unified_reflection_critiques(self, critiques: List[Dict[str, Any]], **options) -> str:
        """Format unified reflection critiques for display including quality scores."""
        if not critiques:
            return "No unified reflection critiques available."
        
        content = "# Unified Reflection Analysis Summary\n\n"
        content += f"**Total Scenarios Evaluated:** {len(critiques)}\n\n"
        
        # Calculate quality statistics
        quality_scores = [c.get('overall_quality_score', 0) for c in critiques if c.get('overall_quality_score')]
        if quality_scores:
            avg_quality = sum(quality_scores) / len(quality_scores)
            content += f"**Average Quality Score:** {avg_quality:.1f}/100\n"
            content += f"**Quality Range:** {min(quality_scores)}-{max(quality_scores)}/100\n\n"
        
        # Show quality distribution
        high_quality = [s for s in quality_scores if s >= 80]
        medium_quality = [s for s in quality_scores if 60 <= s < 80]
        
        content += "## Quality Distribution\n\n"
        content += f"**High Quality (80-100):** {len(high_quality)} scenarios\n"
        content += f"**Medium Quality (60-79):** {len(medium_quality)} scenarios\n"
        content += f"**Below 60:** {len(quality_scores) - len(high_quality) - len(medium_quality)} scenarios\n\n"
        
        # Show individual critiques with quality scores
        content += "## Individual Assessments\n\n"
        for i, critique in enumerate(critiques):
            scenario_id = critique.get('target_scenario_id', 'unknown')
            quality_score = critique.get('overall_quality_score', 0)  # Fixed: use 'overall_quality_score'
            
            content += f"### {i}. Scenario {scenario_id}\n\n"
            content += f"**Overall Quality Score:** {quality_score}/100\n"
            
            # Include critique content preview
            critique_content = critique.get('critique_content', '')
            preview = critique_content[:200] + "..." if len(critique_content) > 200 else critique_content
            content += f"**Assessment:** {preview}\n\n"
        
        return content
    
    def _format_debate_directions_summary(self, data: Dict[str, Any], **options) -> str:
        """Format debate-generated research directions summary."""
        research_directions = data.get('research_directions', [])
        debate_result = data.get('debate_result', {})
        
        if not research_directions:
            return "No research directions from debate available."
        
        content = "# Collaborative Expert Consultation Results\n\n"
        content += f"**Debate Type:** {debate_result.get('debate_type', 'Unknown')}\n"
        content += f"**Conversation Rounds:** {debate_result.get('conversation_rounds', 0)}\n\n"
        
        content += "## Selected Research Directions\n\n"
        for i, direction in enumerate(research_directions, 1):
            direction_name = direction.get('name', 'Unknown')
            assumption = direction.get('assumption', 'N/A')
            
            content += f"## Direction {i}: {direction_name}\n\n"
            content += f"**Core Assumption:** {assumption}\n\n"
        
        # Add debate summary if available
        conversation_rounds = debate_result.get('conversation_rounds', 0)
        if conversation_rounds > 0:
            content += f"## Consultation Process\n\n"
            content += f"The research directions were developed through {conversation_rounds} rounds of "
            content += f"collaborative discussion between domain experts, ensuring comprehensive coverage "
            content += f"and balanced perspectives across different approaches.\n"
        
        return content
    
    # === Helper Methods ===
    
    def _format_generic_content(self, content_type: str, data: Any, **options) -> str:
        """Generic formatter for unknown content types."""
        title = options.get('title', f"{content_type.replace('_', ' ').title()}")
        
        content = f"# {title}\n\n"
        content += f"**Content Type:** {content_type}\n"
        content += f"**Generated:** {datetime.now().isoformat()}\n\n"
        
        if isinstance(data, list):
            content += f"**Total Items:** {len(data)}\n\n"
            for i, item in enumerate(data[:5]):  # Show first 5 items
                content += f"## Item {i+1}\n\n"
                content += f"{str(item)[:200]}...\n\n"
        elif isinstance(data, dict):
            content += "## Data Summary\n\n"
            for key, value in list(data.items())[:10]:  # Show first 10 keys
                content += f"**{key}:** {str(value)[:100]}...\n"
        else:
            content += f"**Data:** {str(data)[:500]}...\n"
        
        return content
    
    def _format_chat_conversation(self, data: Dict[str, Any], **options) -> str:
        """Format conversation as a chat-style conversation."""
        conversation_history = data.get("conversation_history", [])
        debate_type = data.get("debate_type", "Discussion")
        
        chat_lines = []
        chat_lines.append("# 💬 Expert Consultation - Chat Format")
        chat_lines.append(f"**Type:** {debate_type.title()} Discussion")
        chat_lines.append(f"**Participants:** Expert A & Expert B")
        chat_lines.append(f"**Format:** Collaborative Consultation\n")
        
        for i, exchange in enumerate(conversation_history):
            if isinstance(exchange, dict):
                # New structured format
                speaker_key = exchange.get("speaker", f"speaker_{i}")
                content = exchange.get("content", "")
                
                if speaker_key == "expert_a":
                    speaker = "🎯 Expert A"
                elif speaker_key == "expert_b":
                    speaker = "🔄 Expert B"
                else:
                    speaker = f"💬 {speaker_key.title()}"
            else:
                # Legacy format fallback
                speaker = f"💬 Speaker {i+1}"
                content = str(exchange)
            
            # Format as chat message
            chat_lines.append(f"## {speaker}")
            chat_lines.append("")
            chat_lines.append(content.strip())
            chat_lines.append("")
            chat_lines.append("---")
            chat_lines.append("")
        
        return '\n'.join(chat_lines)
    
    def _format_conversation_context(self, conversation_history: List[Dict[str, Any]], **options) -> str:
        """Format conversation history naturally for LLM context."""
        if not conversation_history:
            return "This is the start of the conversation."
        
        formatted = []
        for exchange in conversation_history:
            speaker = exchange["speaker"]
            content = exchange["content"]
            
            if speaker == "expert_a":
                formatted.append(f"Expert A:\n{content}")
            elif speaker == "expert_b":
                formatted.append(f"Expert B:\n{content}")
            else:
                formatted.append(f"{speaker}:\n{content}")
        
        return "\n\n" + "="*50 + "\n\n".join(formatted) + "\n\n" + "="*50 + "\n"
    
    def _group_by_field(self, items: List[Dict[str, Any]], field: str) -> Dict[str, List[Dict[str, Any]]]:
        """Group items by a specific field value."""
        groups = {}
        for item in items:
            field_value = item.get(field, 'Unknown')
            if field_value not in groups:
                groups[field_value] = []
            groups[field_value].append(item)
        return groups
    
    def _init_templates(self) -> None:
        """Initialize content templates (could be expanded to load from external files)."""
        # This method is reserved for future template system expansion
        # Currently, templates are embedded in the formatting methods
        pass


# Convenience function for quick usage
def format_content(content_type: str, data: Any, **options) -> str:
    """
    Quick function to format content without creating a formatter instance.
    
    Args:
        content_type: Type of content to format
        data: Data to format
        **options: Additional formatting options
        
    Returns:
        str: Formatted content
        
    Example:
        summary = format_content("tournament_results", {"winners": winners, "all_results": results})
    """
    formatter = ContentFormatter()
    return formatter.format_content(content_type, data, **options) 