"""
Feedback Utilities - Critique and Feedback Processing

This module contains utility functions for processing feedback and critiques
to avoid circular import issues between the main orchestrator and phase modules.
"""

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