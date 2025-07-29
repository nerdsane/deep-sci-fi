"""
Co-Scientist Workflow Phases Package

This package contains all the major workflow phase modules that implement
the core business logic of the Co-Scientist system.

Each phase is responsible for a specific part of the workflow:
- Generation: Scenario and content generation
- Reflection: Quality assessment and critique
- Tournament: Competitive evaluation and ranking
- Evolution: Scenario improvement and enhancement
- Debate: LLM vs LLM collaborative evaluation
"""

# Import the main phase functions for convenient access
from .generation import parallel_scenario_generation, generate_single_scenario
from .reflection import reflection_phase, generate_unified_reflection, integrate_quality_scores
from .tournament import tournament_phase, run_direction_tournament, pairwise_comparison
from .ranking import ranking_phase
from .evolution import evolution_phase, evolution_tournament_phase, evolve_scenario
from .debate import debate_phase, conduct_llm_vs_llm_debate, parse_debate_result_directions
from .meta_analysis import meta_analysis_phase, meta_analysis_traditional_phase, meta_analysis_debate_phase, parse_research_directions
from .meta_review import final_meta_review_phase

__all__ = [
    # Generation Phase
    'parallel_scenario_generation',
    'generate_single_scenario',
    
    # Reflection Phase
    'reflection_phase',
    'generate_unified_reflection', 
    'integrate_quality_scores',
    
        # Tournament Phase
    'tournament_phase',
    'run_direction_tournament',
    'pairwise_comparison',

    # Ranking Phase
    'ranking_phase',

    # Evolution Phase
    'evolution_phase',
    'evolution_tournament_phase',
    'evolve_scenario',

    # Debate Phase
    'debate_phase',
    'conduct_llm_vs_llm_debate',
    'parse_debate_result_directions',

    # Meta-Analysis Phase
    'meta_analysis_phase',
    'meta_analysis_traditional_phase',
    'meta_analysis_debate_phase',
    'parse_research_directions',

    # Meta-Review Phase
    'final_meta_review_phase',
] 