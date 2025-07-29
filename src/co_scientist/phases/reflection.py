"""
Reflection Phase - Scenario Critique and Quality Assessment

This module handles the comprehensive reflection and critique phase where expert
analysis is applied to generated scenarios. It provides unified reflection that
combines multiple domain perspectives into cohesive quality assessments.

Key Features:
- Unified expert reflection across multiple domains
- Quality scoring with detailed dimensional analysis
- Advancement recommendations (ADVANCE/REVISE/REJECT)
- Parallel reflection processing for efficiency
- Comprehensive output management and debugging
"""

import asyncio
import uuid
import re
from typing import Dict, List, Any

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from co_scientist.state import CoScientistState
from co_scientist.configuration import CoScientistConfiguration
from co_scientist.utils.output_manager import get_output_manager
from co_scientist.utils.content_formatters import format_content
from co_scientist.prompts.reflection_prompts import get_unified_reflection_prompt


async def reflection_phase(state: CoScientistState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Conduct unified reflection/critique of all scenarios.
    
    This is the main entry point for the reflection phase. It creates comprehensive
    critique tasks for each scenario and executes them in parallel for efficiency.
    
    Args:
        state: Current workflow state containing scenario population
        config: LangGraph configuration with reflection settings
        
    Returns:
        dict: Updated state with reflection critiques and completion status
    """
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
        manager = get_output_manager(configuration.output_dir, configuration.phase)
        manager.save_critiques(valid_critiques)
        
        # Save raw JSON data for debugging
        manager.save_structured_data("raw_data", {"critiques": valid_critiques}, filename="unified_critiques_raw_data.json", subdirectory="raw_data")
        
        # Save summary with quality scores
        critique_content = format_content("unified_reflection_critiques", valid_critiques)
        manager.save_simple_content("unified_reflection_summary.md", critique_content)
    
    return {
        "reflection_critiques": valid_critiques,
        "reflection_complete": True
    }


async def generate_unified_reflection(scenario: Dict[str, Any], config: RunnableConfig) -> Dict[str, Any]:
    """
    Generate unified comprehensive reflection with quality scoring.
    
    This function conducts a single, comprehensive reflection that combines insights
    from multiple expert domains into one cohesive critique with quality scoring
    and advancement recommendations.
    
    Args:
        scenario: Scenario dictionary containing content and metadata
        config: Configuration with model settings and reflection parameters
        
    Returns:
        dict: Comprehensive critique with quality scores and recommendations
    """
    configuration = CoScientistConfiguration.from_runnable_config(config)
    
    # Get scenario information with defaults for missing fields
    scenario_id = scenario.get("scenario_id", f"missing_id_{uuid.uuid4().hex[:8]}")
    research_direction = scenario.get("research_direction", "Unknown Direction")
    scenario_content = scenario.get("scenario_content", "No scenario content available")
    
    # Get use case from configuration
    use_case = configuration.use_case.value if hasattr(configuration.use_case, 'value') else str(configuration.use_case)
    
    # Get appropriate unified prompt for this use case
    unified_prompt_template = get_unified_reflection_prompt(use_case)
    
    # Import model factory and retry logic
    from co_scientist.co_scientist import llm_call_with_retry
    from co_scientist.utils.model_factory import create_model_factory
    
    # Create model using centralized factory
    model_factory = create_model_factory(configuration)
    llm = model_factory.create_phase_model("reflection")
    
    # Format the unified reflection prompt
    reflection_prompt = unified_prompt_template.format(
        scenario_id=scenario_id,
        research_direction=research_direction,
        scenario_content=scenario_content
    )
    
    try:
        # Generate unified reflection
        response = await llm_call_with_retry(llm, [HumanMessage(content=reflection_prompt)])
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


def parse_quality_scores(reflection_content: str) -> Dict[str, int]:
    """
    Parse quality scores from unified reflection output.
    
    This function extracts numerical quality scores from the reflection text using
    flexible regex patterns that work across different use cases and output formats.
    
    Args:
        reflection_content: Raw reflection text from the LLM
        
    Returns:
        dict: Dictionary mapping quality dimensions to numerical scores
    """
    quality_scores = {}
    
    # Extract overall quality score
    overall_match = re.search(r'\*\*Overall Quality Score:\s*(\d+)/100\*\*', reflection_content)
    if overall_match:
        quality_scores["overall_quality_score"] = int(overall_match.group(1))
    
    # Extract individual dimension scores (flexible patterns for different use cases)
    score_patterns = [
        r'- ([^:]+):\s*(\d+)/100',  # Format: - Dimension: 85/100
        r'\*\*([^:]+)\*\*\s*\(1-100\):\s*(\d+)',  # Format: **Dimension** (1-100): 85
        r'(\w+(?:\s+\w+)*):\s*(\d+)/100'  # Format: Dimension Name: 85/100
    ]
    
    for pattern in score_patterns:
        matches = re.findall(pattern, reflection_content)
        for match in matches:
            dimension_name = match[0].strip().lower().replace(' ', '_')
            score = int(match[1])
            quality_scores[dimension_name] = score
    
    return quality_scores


def parse_advancement_recommendation(reflection_content: str) -> str:
    """
    Parse advancement recommendation from unified reflection output.
    
    This function extracts the advancement recommendation (ADVANCE/REVISE/REJECT)
    from the reflection text, providing fallback logic for robust parsing.
    
    Args:
        reflection_content: Raw reflection text from the LLM
        
    Returns:
        str: Advancement recommendation (ADVANCE/REVISE/REJECT)
    """
    # Look for advancement recommendation in formatted output
    advancement_match = re.search(r'\*\*Advancement Recommendation:\*\*\s*(\w+)', reflection_content)
    if advancement_match:
        return advancement_match.group(1).upper()
    
    # Fallback: look for ADVANCE/REVISE/REJECT anywhere in text
    content_upper = reflection_content.upper()
    if 'ADVANCE' in content_upper:
        return "ADVANCE"
    elif 'REJECT' in content_upper:
        return "REJECT"
    else:
        return "REVISE"


def integrate_quality_scores(scenarios: List[Dict[str, Any]], reflection_critiques: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Integrate quality scores from reflection critiques into scenario data.
    
    This function merges the quality assessment data from the reflection phase
    back into the scenario objects, creating enhanced scenarios with quality
    scores and advancement recommendations.
    
    Args:
        scenarios: List of scenario dictionaries
        reflection_critiques: List of critique dictionaries with quality data
        
    Returns:
        list: Enhanced scenarios with integrated quality data
    """
    # Create a mapping from scenario_id to quality data
    quality_mapping = {}
    for critique in reflection_critiques:
        scenario_id = critique.get("target_scenario_id")
        if scenario_id:
            quality_mapping[scenario_id] = {
                "quality_score": critique.get("overall_quality_score", 50),
                "quality_scores": critique.get("quality_scores", {}),
                "advancement_recommendation": critique.get("advancement_recommendation", "REVISE"),
                "critique_summary": _truncate_text(critique.get("critique_content", ""), 200)
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


def _truncate_text(text: str, max_length: int) -> str:
    """Helper function to truncate text with ellipsis."""
    if len(text) > max_length:
        return text[:max_length] + "..."
    return text 