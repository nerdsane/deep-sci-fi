from langchain.chat_models import init_chat_model
from langchain_core.runnables import RunnableConfig
from langgraph.graph import START, END, StateGraph
from typing import Literal, Any

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
# Import new modular components
from co_scientist.utils.llm_manager import LLMManager
from co_scientist.utils.session_manager import comprehensive_session_reset
from co_scientist.utils.helper_functions import extract_integration_score, get_competing_scenarios
from co_scientist.elo_rating import EloTracker, create_elo_tracker
from co_scientist.phases.generation import parallel_scenario_generation
from co_scientist.phases.reflection import reflection_phase
from co_scientist.phases.tournament import tournament_phase
from co_scientist.phases.ranking import ranking_phase
from co_scientist.phases.evolution import evolution_phase, evolution_tournament_phase
from co_scientist.phases.debate import debate_phase
from co_scientist.phases.meta_analysis import meta_analysis_phase
from co_scientist.phases.meta_review import final_meta_review_phase

# Prompt imports removed - now handled by individual phase modules

# Import deep_researcher for research tasks
from open_deep_research.deep_researcher import deep_researcher

# Initialize configurable models
configurable_model = init_chat_model(
    configurable_fields=("model", "max_tokens", "api_key"),
)

async def llm_call_with_retry(llm, messages, max_retries: int = 3, base_delay: float = 1.0) -> Any:
    """
    Retry logic for LLM calls with exponential backoff.
    
    This function is still used by refactored phases for consistent retry behavior.
    """
    temp_manager = LLMManager("temp", max_retries, base_delay)
    return await temp_manager._call_with_retry(llm, messages)


# DEPRECATED FUNCTIONS - Use ModelFactory instead
import warnings

def _create_phase_llm_manager(configuration) -> LLMManager:
    """
    DEPRECATED: Use ModelFactory.create_llm_manager() instead.
    
    This function is deprecated and will be removed in a future version.
    Use the centralized ModelFactory for consistent model creation.
    """
    warnings.warn(
        "_create_phase_llm_manager is deprecated. Use ModelFactory.create_llm_manager() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return LLMManager(
        default_model=configuration.research_model,
        max_retries=3,
        base_delay=1.0,
        default_max_tokens=8000,
        default_temperature=0.9
    )

def create_isolated_model_instance(model_name: str, max_tokens: int = 8000, temperature: float = 0.9) -> object:
    """
    DEPRECATED: Use ModelFactory.create_phase_model() instead.
    
    This function is deprecated and will be removed in a future version.
    Use the centralized ModelFactory for consistent model creation with proper configuration.
    """
    warnings.warn(
        "create_isolated_model_instance is deprecated. Use ModelFactory.create_phase_model() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    temp_manager = LLMManager(model_name, default_max_tokens=max_tokens, default_temperature=temperature)
    return temp_manager.create_isolated_instance()

# comprehensive_session_reset delegated to utils/session_manager.py

# meta_analysis_phase moved to co_scientist.phases.meta_analysis

# meta_analysis_traditional_phase moved to co_scientist.phases.meta_analysis

# meta_analysis_debate_phase moved to co_scientist.phases.meta_analysis

# Phase functions moved to dedicated modules in co_scientist.phases

# final_meta_review_phase moved to co_scientist.phases.meta_review

# Workflow routing functions for dynamic phase control
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


