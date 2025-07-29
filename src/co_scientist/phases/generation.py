"""
Generation Phase - Scenario and Content Generation

This module handles the parallel generation of scenarios or other content types
based on research directions. It supports both deep research-based generation
and creative LLM-based generation.

Key Features:
- Parallel generation across multiple research directions
- Flexible content types (scenarios, storylines, chapters, etc.)
- Error handling with detailed logging
- Support for both deep_researcher and isolated LLM approaches
- Comprehensive output management and debugging
"""

import asyncio
import traceback
import uuid
from datetime import datetime
from typing import Dict, Any

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from co_scientist.state import CoScientistState
from co_scientist.configuration import CoScientistConfiguration
from co_scientist.utils.output_manager import get_output_manager
from co_scientist.utils.content_formatters import format_content
from co_scientist.prompts import INCREMENTAL_SCENARIO_GENERATION_PROMPT, get_generation_prompt


async def parallel_scenario_generation(state: CoScientistState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Generate content in parallel for each research direction.
    
    This is the main entry point for the generation phase. It creates multiple
    generation tasks and executes them in parallel for efficiency, with robust
    error handling to ensure partial failures don't break the entire process.
    
    Args:
        state: Current workflow state containing research directions
        config: LangGraph configuration with generation settings
        
    Returns:
        dict: Updated state with generated scenarios and completion status
    """
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
            # Create multiple research teams per direction for diversity
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
                # Log the full exception details for debugging
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
        print(f"Full traceback:")
        print(traceback.format_exc())
        # Return minimal valid state to prevent total failure
        valid_scenarios = []
    
    # Save scenario generation results
    if configuration.save_intermediate_results:
        # Save individual scenarios with full content  
        manager = get_output_manager(configuration.output_dir)
        manager.save_scenarios(valid_scenarios)
        
        # Save raw JSON data for debugging
        manager.save_structured_data("raw_data", {"scenarios": valid_scenarios}, filename="scenarios_raw_data.json", subdirectory="raw_data")
        
        # Save summary
        scenario_content = format_content("scenario_population", valid_scenarios)
        manager.save_simple_content("scenario_population_summary.md", scenario_content)
    
    return {
        "scenario_population": valid_scenarios,
        "generation_complete": True
    }


async def generate_single_scenario(direction: Dict[str, Any], team_id: str, state: CoScientistState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Generate a single content item (scenario, storyline, chapter, etc.) using either deep research or creative LLM.
    
    This function handles the actual content generation for a single research direction and team.
    It supports backward compatibility and flexible prompt systems for different use cases.
    
    Args:
        direction: Research direction dictionary containing name and assumptions
        team_id: Unique identifier for the generating team
        state: Current workflow state with context and parameters
        config: Configuration with model settings and generation options
        
    Returns:
        dict: Generated scenario with metadata, content, and generation details
    """
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
        print(f"Full traceback:")
        print(traceback.format_exc())
        raise e
    
    # Use either deep_researcher or regular LLM based on configuration
    co_config = CoScientistConfiguration.from_runnable_config(config)
    
    if co_config.use_deep_researcher:
        # Use deep_researcher for research-based generation
        content, raw_result = await _generate_with_deep_researcher(research_query, team_id, co_config, config)
    else:
        # Use isolated LLM for creative generation
        content, raw_result = await _generate_with_isolated_llm(research_query, team_id, co_config)
    
    return {
        "scenario_id": str(uuid.uuid4()),
        "team_id": team_id,
        "research_direction": direction.get("name", ""),
        "core_assumption": direction.get("assumption", ""),
        "scenario_content": content,
        "research_query": research_query,
        "raw_research_result": raw_result,
        "generation_timestamp": datetime.now().isoformat(),
        "quality_score": None,
        "critiques": []
    }


async def _generate_with_deep_researcher(research_query: str, team_id: str, co_config: CoScientistConfiguration, config: RunnableConfig) -> tuple[str, str]:
    """
    Generate content using the deep_researcher system with comprehensive research capabilities.
    
    This approach provides research-backed content generation with automatic source gathering,
    analysis, and synthesis. Includes retry logic for robust API handling.
    """
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
        from open_deep_research.deep_researcher import reset_deep_researcher_global_state, deep_researcher
        reset_deep_researcher_global_state()
        
        # Use retry logic for deep_researcher call
        import anthropic
        import random
        
        for attempt in range(3):  # max_retries = 3
            try:
                research_result = await deep_researcher.ainvoke(
                    {"messages": [HumanMessage(content=research_query)]},
                    research_config
                )
                break  # Success, exit retry loop
            except anthropic.APIStatusError as e:
                error_type = e.body.get("error", {}).get("type", "") if hasattr(e, 'body') else ""
                if error_type in ["overloaded_error", "rate_limit_error"] and attempt < 2:  # attempt < max_retries - 1
                    delay = 1.0 * (2 ** attempt) + random.uniform(0, 1)  # base_delay = 1.0
                    print(f"  ⏳ Deep researcher API {error_type}, retrying in {delay:.1f}s (attempt {attempt + 1}/3)")
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise  # Re-raise if not retryable or max retries exceeded
            except Exception as e:
                error_msg = str(e).lower()
                if any(keyword in error_msg for keyword in ["timeout", "connection", "network"]) and attempt < 2:
                    delay = 1.0 * (2 ** attempt) + random.uniform(0, 1)
                    print(f"  ⏳ Deep researcher network error, retrying in {delay:.1f}s (attempt {attempt + 1}/3)")
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise
        
        scenario_content = research_result.get("final_report", "")
        raw_result = str(research_result)
        print(f"Successfully generated content for {team_id} using deep_researcher, length: {len(scenario_content)}")
        return scenario_content, raw_result
        
    except Exception as e:
        print(f"Failed to generate content for {team_id} using deep_researcher: {e}")
        print(f"Deep researcher failure traceback:")
        print(traceback.format_exc())
        raise e


async def _generate_with_isolated_llm(research_query: str, team_id: str, co_config: CoScientistConfiguration) -> tuple[str, str]:
    """
    Generate content using an isolated LLM instance for creative generation.
    
    This approach prevents context bleeding between parallel tasks and provides
    high-temperature creative generation for unique, diverse content.
    """
    # Import legacy functions (will be replaced with direct LLMManager calls in future)
    from co_scientist.co_scientist import create_isolated_model_instance, llm_call_with_retry
    
    # Use isolated LLM for creative generation (prevents context bleeding between parallel tasks)
    isolated_model = create_isolated_model_instance(
        model_name=co_config.general_model,
        max_tokens=8000,
        temperature=0.9  # High temperature for creativity and uniqueness
    )
    
    try:
        response = await llm_call_with_retry(isolated_model, [HumanMessage(content=research_query)])
        scenario_content = response.content
        raw_result = f"Isolated LLM response: {response.content}"
        print(f"Successfully generated content for {team_id} using isolated LLM, length: {len(scenario_content)}")
        return scenario_content, raw_result
        
    except Exception as e:
        print(f"Failed to generate content for {team_id} using isolated LLM: {e}")
        print(f"Isolated LLM failure traceback:")
        print(traceback.format_exc())
        raise e 