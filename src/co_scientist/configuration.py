from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from langchain_core.runnables import RunnableConfig
from enum import Enum

class ProcessDepth(str, Enum):
    """Control how deep the co_scientist process goes."""
    QUICK = "quick"           # 3 phases: meta → generation → tournament
    STANDARD = "standard"     # 5 phases: + reflection + evolution  
    COMPREHENSIVE = "comprehensive"  # 7 phases: full pipeline

class PopulationScale(str, Enum):
    """Control the population size for competition."""
    LIGHT = "light"          # 2 directions × 3 contestants = 6 total
    MEDIUM = "medium"        # 3 directions × 6 contestants = 18 total
    HEAVY = "heavy"          # 3 directions × 12 contestants = 36 total

class UseCase(str, Enum):
    """Pre-configured use case templates."""
    SCENARIO_GENERATION = "scenario_generation"
    STORYLINE_CREATION = "storyline_creation"
    CHAPTER_WRITING = "chapter_writing"
    CHAPTER_REWRITING = "chapter_rewriting" 
    CHARACTER_DEVELOPMENT = "character_development"
    PLOT_ANALYSIS = "plot_analysis"
    CUSTOM = "custom"

# Use case configurations
USE_CASE_CONFIGS = {
    "scenario_generation": {
        "direction_type": "research directions",
        "task_type": "scenario development",
        "reflection_domains": ["physics", "biology", "engineering", "social_science", "economics"],
        "evolution_strategies": ["feasibility", "creativity", "synthesis", "detail_enhancement"],
        "output_name": "scenarios",
        "meta_prompt_key": "scenario_meta",
        "generation_prompt_key": "scenario_generation"
    },
    "storyline_creation": {
        "direction_type": "narrative approaches",
        "task_type": "storyline development",
        "reflection_domains": ["plot_structure", "character_development", "thematic_coherence", "pacing", "narrative_arc"],
        "evolution_strategies": ["plot_enhancement", "character_depth", "thematic_strengthening", "structural_improvement"],
        "output_name": "storylines",
        "meta_prompt_key": "storyline_meta",
        "generation_prompt_key": "storyline_generation"
    },
    "chapter_writing": {
        "direction_type": "narrative approaches",
        "task_type": "chapter writing",
        "reflection_domains": ["prose_quality", "scene_development", "character_voice", "pacing", "atmosphere"],
        "evolution_strategies": ["prose_enhancement", "scene_depth", "voice_consistency", "atmospheric_improvement"],
        "output_name": "chapters",
        "meta_prompt_key": "chapter_meta",
        "generation_prompt_key": "chapter_generation"
    },
    "chapter_rewriting": {
        "direction_type": "narrative approaches", 
        "task_type": "chapter rewriting",
        "reflection_domains": ["narrative_structure", "character_development", "prose_style", "pacing", "dialogue"],
        "evolution_strategies": ["character_depth", "narrative_flow", "prose_enhancement", "structural_improvement"],
        "output_name": "chapter_versions",
        "meta_prompt_key": "chapter_meta",
        "generation_prompt_key": "chapter_generation"
    },
    "custom": {
        "direction_type": "approaches",
        "task_type": "content development",
        "reflection_domains": ["quality", "consistency", "effectiveness", "creativity", "feasibility"],
        "evolution_strategies": ["quality_improvement", "creative_enhancement", "structural_refinement", "detail_expansion"],
        "output_name": "outputs",
        "meta_prompt_key": "custom_meta", 
        "generation_prompt_key": "custom_generation"
    }
}

class CoScientistConfiguration(BaseModel):
    # Use Case and Process Control
    use_case: UseCase = Field(
        default=UseCase.SCENARIO_GENERATION,
        metadata={
            "x_oap_ui_config": {
                "type": "string",
                "enum": ["scenario_generation", "chapter_rewriting", "character_development", "plot_analysis", "custom"],
                "default": "scenario_generation",
                "description": "Pre-configured use case template"
            }
        }
    )
    
    process_depth: ProcessDepth = Field(
        default=ProcessDepth.STANDARD,
        metadata={
            "x_oap_ui_config": {
                "type": "string", 
                "enum": ["quick", "standard", "comprehensive"],
                "default": "standard",
                "description": "How deep the competitive process goes"
            }
        }
    )
    
    population_scale: PopulationScale = Field(
        default=PopulationScale.MEDIUM,
        metadata={
            "x_oap_ui_config": {
                "type": "string",
                "enum": ["light", "medium", "heavy"], 
                "default": "medium",
                "description": "Population size for competition"
            }
        }
    )
    
    enabled_phases: List[str] = Field(
        default=["meta_analysis", "scenario_generation", "reflection", "tournament", "evolution", "evolution_tournament", "meta_review"],
        metadata={
            "x_oap_ui_config": {
                "type": "array",
                "items": {"type": "string"},
                "default": ["meta_analysis", "scenario_generation", "reflection", "tournament", "evolution", "evolution_tournament", "meta_review"],
                "description": "Which phases to enable (for custom control)"
            }
        }
    )

    # Model Configuration
    research_model: str = Field(
        default="openai:o4-mini",
        metadata={
            "x_oap_ui_config": {
                "type": "string",
                "default": "openai:o4-mini",
                "description": "Model to use for research and deep analysis tasks"
            }
        }
    )
    
    general_model: str = Field(
        default="openai:o4-mini",
        metadata={
            "x_oap_ui_config": {
                "type": "string", 
                "default": "openai:o4-mini",
                "description": "Model to use for general tasks like reflection and ranking"
            }
        }
    )
    
    # Tournament Configuration (dynamic based on population_scale)
    scenarios_per_direction: Optional[int] = Field(
        default=None,
        metadata={
            "x_oap_ui_config": {
                "type": "number",
                "default": None,
                "min": 3,
                "max": 12,
                "description": "Number of scenarios per direction (auto-calculated from population_scale if None)"
            }
        }
    )
    
    parallel_directions: Optional[int] = Field(
        default=None,
        metadata={
            "x_oap_ui_config": {
                "type": "number",
                "default": None,
                "min": 2,
                "max": 5,
                "description": "Number of parallel directions (auto-calculated from population_scale if None)"
            }
        }
    )
    
    tournament_rounds: int = Field(
        default=3,
        metadata={
            "x_oap_ui_config": {
                "type": "number",
                "default": 3,
                "min": 2,
                "max": 5,
                "description": "Number of tournament elimination rounds"
            }
        }
    )
    
    # Reflection Configuration (dynamic based on use_case)
    reflection_domains: Optional[List[str]] = Field(
        default=None,
        metadata={
            "x_oap_ui_config": {
                "type": "array",
                "items": {"type": "string"},
                "default": None,
                "description": "Domains of expertise for reflection agents (auto-selected from use_case if None)"
            }
        }
    )
    
    # Evolution Configuration (dynamic based on use_case)
    evolution_strategies: Optional[List[str]] = Field(
        default=None,
        metadata={
            "x_oap_ui_config": {
                "type": "array", 
                "items": {"type": "string"},
                "default": None,
                "description": "Types of evolution to apply to winning scenarios (auto-selected from use_case if None)"
            }
        }
    )
    
    # Quality Control
    min_quality_threshold: int = Field(
        default=35,
        metadata={
            "x_oap_ui_config": {
                "type": "number",
                "default": 35,
                "min": 20,
                "max": 50,
                "description": "Minimum quality score (out of 50) for scenarios to advance"
            }
        }
    )
    
    max_critique_severity: int = Field(
        default=7,
        metadata={
            "x_oap_ui_config": {
                "type": "number",
                "default": 7,
                "min": 5,
                "max": 10,
                "description": "Maximum critique severity score (out of 10) allowed to advance"
            }
        }
    )
    
    # Search API Configuration (inherited from deep_researcher pattern)
    search_api: str = Field(
        default="tavily",
        metadata={
            "x_oap_ui_config": {
                "type": "string",
                "enum": ["anthropic", "openai", "tavily", "none"],
                "default": "tavily",
                "description": "Search API to use for deep research"
            }
        }
    )
    
    # Processing Configuration
    use_deep_researcher: bool = Field(
        default=True,
        metadata={
            "x_oap_ui_config": {
                "type": "boolean",
                "default": True,
                "description": "Use deep_researcher for content generation (False = use regular LLM calls)"
            }
        }
    )
    
    max_retries: int = Field(
        default=3,
        metadata={
            "x_oap_ui_config": {
                "type": "number",
                "default": 3,
                "min": 1,
                "max": 5,
                "description": "Maximum retries for failed operations"
            }
        }
    )
    
    enable_parallel_execution: bool = Field(
        default=True,
        metadata={
            "x_oap_ui_config": {
                "type": "boolean",
                "default": True,
                "description": "Enable parallel execution of tournament directions"
            }
        }
    )
    
    # Debugging and Output
    detailed_logging: bool = Field(
        default=False,
        metadata={
            "x_oap_ui_config": {
                "type": "boolean",
                "default": False,
                "description": "Enable detailed logging of competition process"
            }
        }
    )
    
    save_intermediate_results: bool = Field(
        default=True,
        metadata={
            "x_oap_ui_config": {
                "type": "boolean",
                "default": True,
                "description": "Save intermediate results for debugging and analysis"
            }
        }
    )
    
    output_dir: str = Field(
        default="output",
        metadata={
            "x_oap_ui_config": {
                "type": "string",
                "default": "output",
                "description": "Directory to save intermediate results"
            }
        }
    )
    
    # Helper methods
    def get_scenarios_per_direction(self) -> int:
        """Get scenarios per direction based on population scale."""
        if self.scenarios_per_direction is not None:
            return self.scenarios_per_direction
            
        scale_mapping = {
            PopulationScale.LIGHT: 3,
            PopulationScale.MEDIUM: 6,
            PopulationScale.HEAVY: 12
        }
        return scale_mapping.get(self.population_scale, 6)
    
    def get_parallel_directions(self) -> int:
        """Get parallel directions based on population scale."""
        if self.parallel_directions is not None:
            return self.parallel_directions
            
        scale_mapping = {
            PopulationScale.LIGHT: 2,
            PopulationScale.MEDIUM: 3,
            PopulationScale.HEAVY: 3
        }
        return scale_mapping.get(self.population_scale, 3)
    
    def get_reflection_domains(self) -> List[str]:
        """Get reflection domains based on use case."""
        if self.reflection_domains is not None:
            return self.reflection_domains
            
        use_case_config = USE_CASE_CONFIGS.get(self.use_case.value, USE_CASE_CONFIGS["custom"])
        return use_case_config["reflection_domains"]
    
    def get_evolution_strategies(self) -> List[str]:
        """Get evolution strategies based on use case."""
        if self.evolution_strategies is not None:
            return self.evolution_strategies
            
        use_case_config = USE_CASE_CONFIGS.get(self.use_case.value, USE_CASE_CONFIGS["custom"])
        return use_case_config["evolution_strategies"]
    
    def get_enabled_phases_for_depth(self) -> List[str]:
        """Get enabled phases based on process depth."""
        all_phases = ["meta_analysis", "scenario_generation", "reflection", "tournament", "evolution", "evolution_tournament", "meta_review"]
        
        if self.process_depth == ProcessDepth.QUICK:
            return ["meta_analysis", "scenario_generation", "tournament", "meta_review"]
        elif self.process_depth == ProcessDepth.STANDARD:
            return ["meta_analysis", "scenario_generation", "reflection", "tournament", "evolution", "meta_review"]
        elif self.process_depth == ProcessDepth.COMPREHENSIVE:
            return all_phases
        else:
            # Use custom enabled_phases
            return self.enabled_phases
    
    def get_use_case_config(self) -> Dict:
        """Get the configuration for the current use case."""
        return USE_CASE_CONFIGS.get(self.use_case.value, USE_CASE_CONFIGS["custom"])
    
    def get_phase_list(self) -> List[str]:
        """Get the list of phases to run based on process depth."""
        return self.get_enabled_phases_for_depth()

    @classmethod
    def create_input_state(cls, 
                          task_description: str,
                          context: str,
                          use_case: UseCase = UseCase.CUSTOM,
                          reference_material: str = None,
                          domain_context: str = None,
                          **legacy_fields) -> dict:
        """Create a properly formatted input state for co_scientist.
        
        Args:
            task_description: What the competitive process should accomplish
            context: Background information, requirements, constraints
            use_case: Which template to use
            reference_material: Existing content to work with (for rewriting tasks)
            domain_context: Genre/domain-specific context
            **legacy_fields: Backward compatibility fields like storyline, target_year, etc.
        
        Returns:
            Dictionary formatted for CoScientistInputState
        """
        input_state = {
            "task_description": task_description,
            "context": context,
            "use_case": use_case.value if hasattr(use_case, 'value') else use_case
        }
        
        if reference_material:
            input_state["reference_material"] = reference_material
        if domain_context:
            input_state["domain_context"] = domain_context
            
        # Add any legacy fields for backward compatibility
        input_state.update(legacy_fields)
        
        return input_state

    @classmethod
    def from_runnable_config(cls, config: RunnableConfig) -> "CoScientistConfiguration":
        """Create configuration from a RunnableConfig."""
        configurable = config.get("configurable", {})
        return cls(**configurable) 