"""
Meta-Review Phase - Competition Process Analysis and Synthesis

This module handles the final meta-review process that synthesizes insights from the
entire competition workflow for optimization and analysis.

Key Features:
- Competition process analysis
- Direction winner evaluation
- Quality score aggregation
- Performance insights synthesis
- Process optimization recommendations
"""

import asyncio
from typing import Dict, List, Any

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from co_scientist.state import CoScientistState
from co_scientist.configuration import CoScientistConfiguration
from co_scientist.utils.output_manager import get_output_manager
from co_scientist.utils.content_formatters import format_content
from co_scientist.prompts.meta_review_prompts import META_REVIEW_PROMPT


async def final_meta_review_phase(state: CoScientistState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Synthesize insights from competition process for optimization.
    
    Analyzes tournament winners, quality scores, and competition performance
    to generate process insights and optimization recommendations.
    
    Args:
        state: Current workflow state with competition results
        config: Configuration with meta-review settings
        
    Returns:
        dict: Final analysis with direction winners and process insights
    """
    configuration = CoScientistConfiguration.from_runnable_config(config)
    
    # Extract direction winners from tournament results
    direction_winners = _extract_direction_winners(state.get("tournament_winners", []))
    
    if not direction_winners:
        print("📋 No direction winners available - generating process analysis with available data")
        return {
            "direction_winners": [],
            "process_analysis": "Competition completed but no direction winners were identified.",
            "competition_summary": "Process analysis: No winners to analyze."
        }
    
    # Import here to avoid circular imports
    from co_scientist.co_scientist import create_isolated_model_instance, llm_call_with_retry
    
    # Determine temperature based on model type
    review_temperature = 1 if "o3" in configuration.general_model else 0.7
    
    llm = create_isolated_model_instance(
        model_name=configuration.general_model,
        max_tokens=4096,
        temperature=review_temperature  # Use appropriate temperature for model
    )
    
    # Prepare analysis data
    analysis_data = _prepare_analysis_data(state, direction_winners)
    
    # Generate meta-review prompt
    # Combine all analysis data into a single formatted string
    combined_analysis_data = f"""
Tournament Analysis:
{analysis_data["tournament_data"]}

Reflection Analysis:
{analysis_data["reflection_data"]}

Evolution Analysis:
{analysis_data["evolution_data"]}
"""
    
    meta_review_prompt = META_REVIEW_PROMPT.format(
        competition_summary=format_content("competition_summary", state),
        tournament_winners=analysis_data["winners_summary"],
        analysis_data=combined_analysis_data
    )
    
    # Generate process analysis
    response = await llm_call_with_retry(llm, [HumanMessage(content=meta_review_prompt)])
    process_analysis = response.content
    
    # Create competition summary
    competition_summary = format_content("competition_summary", state)
    
    # Save results if configured
    if configuration.save_intermediate_results:
        manager = get_output_manager(configuration.output_dir, configuration.phase)
        manager.save_simple_content("meta_review_process_analysis.md", process_analysis)
        manager.save_simple_content("competition_summary.md", competition_summary)
    
    print(f"📊 Meta-review complete with {len(direction_winners)} direction winners analyzed")
    
    return {
        "direction_winners": direction_winners,
        "process_analysis": process_analysis,
        "competition_summary": competition_summary
    }


def _extract_direction_winners(tournament_winners: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extract direction winners from tournament results.
    
    Args:
        tournament_winners: List of tournament results
        
    Returns:
        list: Structured direction winner data
    """
    direction_winners = []
    
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
    
    return direction_winners


def _prepare_analysis_data(state: CoScientistState, direction_winners: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Prepare comprehensive analysis data for meta-review.
    
    Args:
        state: Current workflow state
        direction_winners: List of direction winner data
        
    Returns:
        dict: Formatted analysis data for meta-review prompt
    """
    # Format direction winners summary
    winners_summary = _format_winners_summary(direction_winners)
    
    # Format competition process data
    tournament_data = format_content("tournament_analysis", state.get("tournament_comparisons", []))
    reflection_data = format_content("reflection_analysis", state.get("reflection_critiques", []))
    evolution_data = format_content("evolution_analysis", state.get("evolved_scenarios", []))
    
    return {
        "winners_summary": winners_summary,
        "tournament_data": tournament_data,
        "reflection_data": reflection_data,
        "evolution_data": evolution_data
    }


def _format_winners_summary(direction_winners: List[Dict[str, Any]]) -> str:
    """
    Format direction winners summary with quality statistics.
    
    Args:
        direction_winners: List of direction winner data
        
    Returns:
        str: Formatted winners summary with statistics
    """
    if not direction_winners:
        return "No direction winners available.\n"
    
    summary = ""
    quality_scores = []
    
    for i, winner in enumerate(direction_winners, 1):
        summary += f"Direction {i} Winner: {winner.get('research_direction', 'Unknown')}\n"
        summary += f"  - Core Assumption: {winner.get('core_assumption', 'N/A')}\n"
        summary += f"  - Team: {winner.get('team_id', 'Unknown')}\n"
        
        # Add quality metrics if available
        quality_score = winner.get('quality_score', 0)
        advancement_rec = winner.get('advancement_recommendation', 'N/A')
        if quality_score > 0:
            summary += f"  - Quality Score: {quality_score}/100\n"
            summary += f"  - Pre-Tournament Assessment: {advancement_rec}\n"
            quality_scores.append(quality_score)
        
        summary += "\n"
    
    # Add overall quality statistics if available
    if quality_scores:
        avg_quality = sum(quality_scores) / len(quality_scores)
        summary += f"Overall Quality Statistics:\n"
        summary += f"  - Average Winner Quality: {avg_quality:.1f}/100\n"
        summary += f"  - Quality Range: {min(quality_scores)}-{max(quality_scores)}/100\n"
        summary += f"  - Total Winners with Quality Data: {len(quality_scores)}\n\n"
    
    return summary 