"""
Meta-Analysis Phase - Research Direction Identification and Analysis

This module handles the identification of research directions through either traditional
single-LLM analysis or collaborative LLM debate approaches.

Key Features:
- Traditional single-LLM meta-analysis
- LLM vs LLM debate-based meta-analysis  
- Research direction parsing and validation
- Flexible prompt template system
- Backward compatibility with legacy formats
"""

import asyncio
from typing import Dict, List, Any

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from co_scientist.state import CoScientistState
from co_scientist.configuration import CoScientistConfiguration
from co_scientist.utils.output_manager import get_output_manager
from co_scientist.utils.content_formatters import format_content
from co_scientist.prompts.meta_analysis_prompts import (
    INITIAL_META_ANALYSIS_PROMPT,
    INCREMENTAL_META_ANALYSIS_PROMPT,
    get_meta_analysis_prompt
)


async def meta_analysis_phase(state: CoScientistState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Analyze input and identify research directions using configurable approaches.
    
    Routes between traditional single-LLM analysis and collaborative debate based
    on configuration settings.
    
    Args:
        state: Current workflow state
        config: Configuration with meta-analysis settings
        
    Returns:
        dict: Updated state with research directions and analysis results
    """
    configuration = CoScientistConfiguration.from_runnable_config(config)
    
    print(f"🔍 Meta-analysis mode: {'DEBATE' if configuration.use_meta_analysis_debate else 'TRADITIONAL'}")
    
    if configuration.use_meta_analysis_debate:
        return await meta_analysis_debate_phase(state, config)
    else:
        return await meta_analysis_traditional_phase(state, config)


async def meta_analysis_traditional_phase(state: CoScientistState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Traditional single-LLM meta-analysis approach.
    
    Uses isolated model instances to prevent context bleeding and generate
    research directions through structured prompting.
    
    Args:
        state: Current workflow state
        config: Configuration with analysis settings
        
    Returns:
        dict: State with research directions and analysis reasoning
    """
    # Import session reset here to avoid circular imports
    from co_scientist.co_scientist import comprehensive_session_reset, llm_call_with_retry
    from co_scientist.utils.model_factory import create_model_factory
    
    session_id = comprehensive_session_reset()
    configuration = CoScientistConfiguration.from_runnable_config(config)
    
    print(f"🧠 Starting traditional meta-analysis: {configuration.use_case}")
    
    # Create model using centralized factory
    model_factory = create_model_factory(configuration)
    llm = model_factory.create_phase_model("meta_analysis")
    
    # Process state for backward compatibility
    processed_state = _process_legacy_state(state)
    use_case = processed_state.get("use_case", configuration.use_case.value)
    
    # Select appropriate prompt template
    if use_case == "scenario_generation" and processed_state.get("baseline_world_state") and processed_state.get("years_in_future"):
        meta_prompt = INCREMENTAL_META_ANALYSIS_PROMPT.format(
            storyline=processed_state.get("storyline", ""),
            world_building_questions=processed_state.get("context", processed_state.get("research_context", "")),
            baseline_world_state=processed_state["baseline_world_state"],
            years_in_future=processed_state["years_in_future"]
        )
    else:
        meta_prompt = get_meta_analysis_prompt(use_case, processed_state, config)
    
    # Generate research directions
    response = await llm_call_with_retry(llm, [HumanMessage(content=meta_prompt)])
    research_directions = parse_research_directions(response.content)
    
    # If parsing failed due to parameter issues, generate fallback directions
    if not research_directions and _is_llm_refusal_response(response.content):
        print("🔧 Generating fallback research directions due to parameter issues")
        research_directions = _generate_fallback_directions(use_case, processed_state)
    
    print(f"📊 Parsed {len(research_directions)} research directions")
    
    # Save results if configured
    if configuration.save_intermediate_results:
        manager = get_output_manager(configuration.output_dir, configuration.phase)
        manager.save_simple_content("meta_analysis.md", response.content)
    
    return _create_meta_analysis_result(research_directions, response.content)


async def meta_analysis_debate_phase(state: CoScientistState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Generate research directions through LLM vs LLM debate conversation.
    
    Uses collaborative debate between multiple LLM instances to identify
    and validate research directions through interactive discussion.
    
    Args:
        state: Current workflow state
        config: Configuration with debate settings
        
    Returns:
        dict: State with research directions and debate conversation
    """
    # Import functions here to avoid circular imports
    from co_scientist.co_scientist import comprehensive_session_reset
    from co_scientist.phases.debate import conduct_llm_vs_llm_debate, parse_debate_result_directions
    
    session_id = comprehensive_session_reset()
    configuration = CoScientistConfiguration.from_runnable_config(config)
    
    print(f"🗣️ Starting LLM vs LLM meta-analysis debate: {configuration.use_case}")
    
    # Process state for backward compatibility
    processed_state = _process_legacy_state(state)
    use_case = processed_state.get("use_case", configuration.use_case.value)
    num_directions = 3  # TODO: Make configurable
    
    # Run collaborative debate
    state_kwargs = {k: v for k, v in processed_state.items() if k != "use_case"}
    debate_result = await conduct_llm_vs_llm_debate(
        use_case,
        "meta_analysis",
        configuration,
        num_directions=num_directions,
        max_rounds=4,  # TODO: Make configurable
        **state_kwargs
    )
    
    # Parse directions from debate results
    research_directions = parse_debate_result_directions(debate_result["final_conclusion"])
    
    # Fallback to traditional approach if debate parsing fails
    if not research_directions or len(research_directions) < num_directions:
        print("⚠️ Debate parsing failed, falling back to traditional meta-analysis")
        return await meta_analysis_traditional_phase(state, config)
    
    print(f"📊 Debate complete. Selected {len(research_directions)} research directions")
    
    # Save debate results if configured
    if configuration.save_intermediate_results:
        manager = get_output_manager(configuration.output_dir, configuration.phase)
        
        manager.save_simple_content("llm_debate_conversation.md", debate_result["full_conversation"], "meta_analysis")
        manager.save_simple_content("llm_debate_chat.md", debate_result["chat_conversation"], "meta_analysis")
        manager.save_simple_content("debate_conclusion.md", debate_result["final_conclusion"], "meta_analysis")
        
        directions_summary = format_content("debate_directions_summary", {"research_directions": research_directions, "debate_result": debate_result})
        manager.save_simple_content("selected_directions.md", directions_summary, "meta_analysis")
    
    result = _create_meta_analysis_result(research_directions, debate_result["full_conversation"])
    result.update({
        "llm_debate_conversation": debate_result["full_conversation"],
        "debate_conclusion": debate_result["final_conclusion"]
    })
    
    return result


def parse_research_directions(content: str) -> List[Dict[str, Any]]:
    """
    Parse research directions from meta-analysis output.
    
    Handles structured format:
    Direction 1: [Name]
    Core Assumption: [Key narrative assumption] 
    Focus: [What this approach emphasizes]
    
    Also handles markdown formatting and multi-line content.
    
    Args:
        content: Raw LLM output containing research directions
        
    Returns:
        list: Parsed research directions with name, assumption, and focus
    """
    # Check if the LLM refused to proceed due to missing parameters
    if _is_llm_refusal_response(content):
        print(f"⚠️ LLM refused to proceed due to missing parameters. Response: {content[:200]}...")
        return []
    
    directions = []
    lines = content.split('\n')
    
    current_direction = {}
    current_field = None
    current_content = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Remove markdown formatting
        clean_line = line.replace("###", "").replace("**", "").strip()
        
        # Direction header (e.g., "Direction 1: Name")
        if clean_line.lower().startswith("direction") and ":" in clean_line:
            _save_current_field(current_direction, current_field, current_content)
            _save_direction_if_complete(directions, current_direction)
            
            name_part = clean_line.split(":", 1)[1].strip()
            current_direction = {"name": name_part}
            current_field = None
            current_content = []
        
        # Core Assumption field
        elif clean_line.lower().startswith("core assumption") and ":" in clean_line:
            _save_current_field(current_direction, current_field, current_content)
            current_field = "assumption"
            assumption_text = clean_line.split(":", 1)[1].strip()
            current_content = [assumption_text] if assumption_text else []
        
        # Focus field
        elif clean_line.lower().startswith("focus") and ":" in clean_line:
            _save_current_field(current_direction, current_field, current_content)
            current_field = "focus"
            focus_text = clean_line.split(":", 1)[1].strip()
            current_content = [focus_text] if focus_text else []
        
        # Reasoning indicates end of directions
        elif clean_line.lower().startswith("reasoning") and ":" in clean_line:
            _save_current_field(current_direction, current_field, current_content)
            _save_direction_if_complete(directions, current_direction)
            break
        
        # Accumulate content for current field
        elif current_field and clean_line:
            current_content.append(clean_line)
    
    # Handle final direction if no "Reasoning:" section
    _save_current_field(current_direction, current_field, current_content)
    _save_direction_if_complete(directions, current_direction)
    
    print(f"📋 Parsed {len(directions)} research directions")
    return directions


def _process_legacy_state(state: CoScientistState) -> Dict[str, Any]:
    """Process state for backward compatibility with legacy formats."""
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
            "use_case": "scenario_generation",
            "world_building_questions": state["research_context"]
        })
    else:
        # New flexible format
        processed_state.update(state)
    
    return processed_state


def _is_llm_refusal_response(content: str) -> bool:
    """Check if the LLM response indicates refusal due to missing parameters."""
    refusal_indicators = [
        "story context you've provided is incomplete",
        "key details are missing",
        "blank]",
        "missing]",
        "would need:",
        "please fill in these context details",
        "cannot provide the targeted",
        "without knowing what specific"
    ]
    
    content_lower = content.lower()
    return any(indicator in content_lower for indicator in refusal_indicators)


def _generate_fallback_directions(use_case: str, state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate fallback research directions when LLM refuses due to missing parameters."""
    
    if use_case == "competitive_outline":
        return [
            {
                "name": "Character-Driven Structural Architecture",
                "assumption": "Story structure should prioritize character development and emotional arcs as the primary organizing principle",
                "focus": "Building chapter sequences around character growth moments and relationship dynamics"
            },
            {
                "name": "Thematic Resonance Framework", 
                "assumption": "Each structural element should reinforce and explore the central human condition theme",
                "focus": "Organizing content to create thematic echoes and deeper meaning through structural choices"
            },
            {
                "name": "Future-World Integration Structure",
                "assumption": "The story structure should showcase the unique aspects of the future world setting",
                "focus": "Balancing world-building revelation with plot progression through strategic pacing"
            }
        ]
    
    elif use_case == "competitive_loglines":
        return [
            {
                "name": "Technology-Consequence Exploration",
                "assumption": "Future stories should examine unexpected consequences of technological advancement",
                "focus": "Creating loglines that explore how technology changes human behavior and relationships"
            },
            {
                "name": "Social Evolution Narrative",
                "assumption": "Future societies develop new social structures and cultural norms",
                "focus": "Crafting loglines around conflicts between old and new ways of being human"
            },
            {
                "name": "Individual vs System Tension",
                "assumption": "Future worlds create new forms of tension between individual agency and systemic control",
                "focus": "Developing loglines where personal stakes intersect with larger societal forces"
            }
        ]
    
    else:
        # Generic fallback for other use cases
        return [
            {
                "name": "Foundation Approach",
                "assumption": "Build on established principles while introducing innovation",
                "focus": "Balancing proven methods with creative exploration"
            },
            {
                "name": "Experimental Methodology", 
                "assumption": "Push boundaries through systematic experimentation",
                "focus": "Testing new approaches while maintaining coherence"
            },
            {
                "name": "Synthesis Strategy",
                "assumption": "Combine multiple perspectives for comprehensive solutions",
                "focus": "Integrating diverse elements into unified approaches"
            }
        ]


def _create_meta_analysis_result(research_directions: List[Dict[str, Any]], reasoning: str) -> Dict[str, Any]:
    """Create standardized meta-analysis result structure."""
    return {
        "research_directions": research_directions,
        "meta_analysis_reasoning": reasoning,
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


def _save_current_field(direction: Dict[str, Any], field: str, content: List[str]) -> None:
    """Save accumulated content to current direction field."""
    if field and content and direction:
        content_text = " ".join(content).strip()
        if content_text:
            direction[field] = content_text


def _save_direction_if_complete(directions: List[Dict[str, Any]], direction: Dict[str, Any]) -> None:
    """Save direction to list if it has required fields."""
    if direction and direction not in directions:
        directions.append(direction) 