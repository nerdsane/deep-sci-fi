# Prompts Package
# Organized by phase for better maintainability

# Import all the main prompt functions
from .generation_prompts import (
    get_generation_prompt,
    get_uniqueness_seed,
    INITIAL_SCENARIO_GENERATION_PROMPT,
    INCREMENTAL_SCENARIO_GENERATION_PROMPT,
    STORYLINE_GENERATION_PROMPT,
    CHAPTER_WRITING_GENERATION_PROMPT,
    CHAPTER_GENERATION_PROMPT,
    NARRATIVE_GENERATION_PROMPT,
    CHAPTER_ARCS_ADJUSTMENT_PROMPT,
    LINGUISTIC_EVOLUTION_GENERATION_PROMPT,
    STORYLINE_ADJUSTMENT_GENERATION_PROMPT,
    # Future-native workflow prompts
    FUTURE_STORY_SEEDS_GENERATION_PROMPT,
    COMPETITIVE_LOGLINES_GENERATION_PROMPT,
    COMPETITIVE_OUTLINE_GENERATION_PROMPT,
    STORY_RESEARCH_INTEGRATION_PROMPT,
    FIRST_CHAPTER_WRITING_GENERATION_PROMPT,
)

from .meta_analysis_prompts import (
    get_meta_analysis_prompt,
    INITIAL_META_ANALYSIS_PROMPT,
    INCREMENTAL_META_ANALYSIS_PROMPT,
    STORYLINE_META_ANALYSIS_PROMPT,
    LOGLINE_META_ANALYSIS_PROMPT,
    COMPETITIVE_OUTLINE_META_ANALYSIS_PROMPT,
    CHAPTER_WRITING_META_ANALYSIS_PROMPT,
    CHAPTER_META_ANALYSIS_PROMPT,
    NARRATIVE_META_ANALYSIS_PROMPT,
    LINGUISTIC_EVOLUTION_META_ANALYSIS_PROMPT,
    STORYLINE_ADJUSTMENT_META_ANALYSIS_PROMPT
)

from .evolution_prompts import (
    get_evolution_prompt,
    SCENARIO_EVOLUTION_PROMPT,
    STORYLINE_EVOLUTION_PROMPT,
    CHAPTER_WRITING_EVOLUTION_PROMPT,
    CHAPTER_ARCS_EVOLUTION_PROMPT,
    LINGUISTIC_EVOLUTION_EVOLUTION_PROMPT
)

from .reflection_prompts import (
    get_unified_reflection_prompt,
    UNIFIED_SCIENTIFIC_REFLECTION_PROMPT,
    UNIFIED_NARRATIVE_REFLECTION_PROMPT,
    CHAPTER_ARCS_REFLECTION_PROMPT,
    UNIFIED_PROSE_REFLECTION_PROMPT,
    UNIFIED_RESEARCH_REFLECTION_PROMPT
)

from .tournament_prompts import (
    get_pairwise_prompt,
    PAIRWISE_RANKING_PROMPT,
    STORYLINE_PAIRWISE_PROMPT,
    CHAPTER_PAIRWISE_PROMPT,
    RESEARCH_PAIRWISE_PROMPT
)

from .debate_prompts import (
    get_llm_debate_meta_analysis_prompt_a,
    get_llm_debate_meta_analysis_prompt_b,
    get_llm_debate_meta_analysis_continue_a,
    get_llm_debate_meta_analysis_continue_b,
    get_llm_debate_tournament_prompt_a,
    get_llm_debate_tournament_prompt_b,
    get_llm_debate_tournament_final_a,
    get_llm_debate_tournament_final_b
)

from .meta_review_prompts import (
    META_REVIEW_PROMPT,
)

# Export all the functions and constants that were previously available
__all__ = [
    # Main prompt functions
    'get_generation_prompt',
    'get_meta_analysis_prompt', 
    'get_evolution_prompt',
    'get_unified_reflection_prompt',
    'get_pairwise_prompt',
    'get_uniqueness_seed',
    
    # LLM Debate functions
    'get_llm_debate_meta_analysis_prompt_a',
    'get_llm_debate_meta_analysis_prompt_b',
    'get_llm_debate_meta_analysis_continue_a',
    'get_llm_debate_meta_analysis_continue_b',
    'get_llm_debate_tournament_prompt_a',
    'get_llm_debate_tournament_prompt_b',
    'get_llm_debate_tournament_final_a',
    'get_llm_debate_tournament_final_b',
    
    # Generation prompts
    'INITIAL_SCENARIO_GENERATION_PROMPT',
    'INCREMENTAL_SCENARIO_GENERATION_PROMPT',
    'STORYLINE_GENERATION_PROMPT',
    'CHAPTER_WRITING_GENERATION_PROMPT',
    'CHAPTER_GENERATION_PROMPT',
    'NARRATIVE_GENERATION_PROMPT',
    'CHAPTER_ARCS_ADJUSTMENT_PROMPT',
    'LINGUISTIC_EVOLUTION_GENERATION_PROMPT',
    'STORYLINE_ADJUSTMENT_GENERATION_PROMPT',
    # Future-native workflow prompts
    'FUTURE_STORY_SEEDS_GENERATION_PROMPT',
    'COMPETITIVE_LOGLINES_GENERATION_PROMPT',
    'COMPETITIVE_OUTLINE_GENERATION_PROMPT',
    'STORY_RESEARCH_INTEGRATION_PROMPT', 
    'FIRST_CHAPTER_WRITING_GENERATION_PROMPT',
    
    # Meta-analysis prompts
    'INITIAL_META_ANALYSIS_PROMPT',
    'INCREMENTAL_META_ANALYSIS_PROMPT',
    'STORYLINE_META_ANALYSIS_PROMPT',
    'LOGLINE_META_ANALYSIS_PROMPT',
    'COMPETITIVE_OUTLINE_META_ANALYSIS_PROMPT',
    'CHAPTER_WRITING_META_ANALYSIS_PROMPT',
    'CHAPTER_META_ANALYSIS_PROMPT',
    'NARRATIVE_META_ANALYSIS_PROMPT',
    'LINGUISTIC_EVOLUTION_META_ANALYSIS_PROMPT',
    'STORYLINE_ADJUSTMENT_META_ANALYSIS_PROMPT',
    
    # Evolution prompts
    'SCENARIO_EVOLUTION_PROMPT',
    'STORYLINE_EVOLUTION_PROMPT',
    'CHAPTER_WRITING_EVOLUTION_PROMPT',
    'CHAPTER_ARCS_EVOLUTION_PROMPT',
    'LINGUISTIC_EVOLUTION_EVOLUTION_PROMPT',
    
    # Reflection prompts
    'UNIFIED_SCIENTIFIC_REFLECTION_PROMPT',
    'UNIFIED_NARRATIVE_REFLECTION_PROMPT',
    'CHAPTER_ARCS_REFLECTION_PROMPT',
    'UNIFIED_PROSE_REFLECTION_PROMPT',
    'UNIFIED_RESEARCH_REFLECTION_PROMPT',
    
    # Tournament prompts
    'PAIRWISE_RANKING_PROMPT',
    'STORYLINE_PAIRWISE_PROMPT',
    'CHAPTER_PAIRWISE_PROMPT',
    'RESEARCH_PAIRWISE_PROMPT',
    
    # Meta-review prompts
    'META_REVIEW_PROMPT',
] 