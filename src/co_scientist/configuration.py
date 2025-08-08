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

class UseCase(Enum):
    """Pre-configured use case templates for Deep Sci-Fi workflow."""
    # Deep Sci-Fi future-native workflow use cases
    COMPETITIVE_LOGLINES = "competitive_loglines"  # Competitive logline generation
    COMPETITIVE_OUTLINE = "competitive_outline"  # Competitive outline creation
    STORY_RESEARCH_INTEGRATION = "story_research_integration"  # Research-integrated story refinement
    FIRST_CHAPTER_WRITING = "first_chapter_writing"  # First chapter competitive writing

# Model Templates - Define phase-specific model configurations
MODEL_TEMPLATES = {
    "creative": {
        "description": "Optimized for creative and narrative tasks",
        "meta_analysis_model": "anthropic:claude-sonnet-4-20250514",              # Deep strategic thinking
        "generation_model": "anthropic:claude-opus-4-20250514",              # Maximum creativity
        "debate_a_model": "anthropic:claude-opus-4-20250514",                # Creative perspective A
        "debate_b_model": "anthropic:claude-sonnet-4-20250514",              # Structured perspective B  
        "reflection_model": "anthropic:claude-sonnet-4-20250514",            # Balanced critique
        "evolution_model": "anthropic:claude-opus-4-20250514",               # Creative enhancement
        "tournament_model": "anthropic:claude-sonnet-4-20250514",            # Balanced comparison
        "meta_review_model": "openai:o3-2025-04-16",               # Final strategic selection
        
        # Creative-optimized temperatures
        "generation_temperature": 0.9,      # High creativity
        "evolution_temperature": 0.9,       # High creativity enhancement
        "meta_analysis_temperature": 0.7,   # Strategic but creative
        "reflection_temperature": 0.6,      # Precise critique
        "debate_temperature": 0.8,          # Balanced argumentation
        "tournament_temperature": 0.7,      # Structured comparison
        "meta_review_temperature": 0.7,     # Strategic selection
    },
    
    "reasoning": {
        "description": "Optimized for analytical and research tasks",
        "meta_analysis_model": "openai:o3-2025-04-16",      # Maximum reasoning
        "generation_model": "openai:o3-2025-04-16",         # Reasoned generation
        "debate_a_model": "openai:o3-2025-04-16",           # Deep analytical perspective
        "debate_b_model": "openai:o3-2025-04-16",           # Fast counter-perspective
        "reflection_model": "anthropic:claude-sonnet-4-20250514",    # Structured critique
        "evolution_model": "openai:o3-2025-04-16",          # Reasoned improvement
        "tournament_model": "openai:o3-2025-04-16",         # Efficient comparison
        "meta_review_model": "openai:o3-2025-04-16",        # Deep final analysis
        
        # Reasoning-optimized temperatures  
        "generation_temperature": 0.7,      # Controlled creativity
        "evolution_temperature": 0.7,       # Controlled enhancement
        "meta_analysis_temperature": 0.6,   # Precise analysis
        "reflection_temperature": 0.6,      # Precise critique
        "debate_temperature": 0.7,          # Structured argumentation
        "tournament_temperature": 0.6,      # Objective comparison
        "meta_review_temperature": 0.6,     # Analytical selection
    }
}

# Use case configurations for Deep Sci-Fi workflow
USE_CASE_CONFIGS = {
    "competitive_loglines": {
        "direction_type": "logline approaches",
        "task_type": "competitive logline generation",
        "reflection_domains": ["premise_strength", "future_specificity", "protagonist_clarity", "stakes_uniqueness", "thematic_resonance"],
        "evolution_strategies": ["logline_refinement"],  # Single evolution strategy
        "output_name": "loglines",
        "meta_prompt_key": "logline_meta",
        "generation_prompt_key": "competitive_loglines",
        "model_template": "creative"  # Use creative template for logline development
    },
    "competitive_outline": {
        "direction_type": "structural approaches",
        "task_type": "competitive outline creation",
        "reflection_domains": ["plot_structure", "character_development", "thematic_integration", "world_building", "pacing"],
        "evolution_strategies": ["structural_refinement"],  # Single evolution strategy
        "output_name": "outlines",
        "meta_prompt_key": "outline_meta",
        "generation_prompt_key": "competitive_outline",
        "model_template": "creative"  # Use creative template for outline development
    },
    "story_research_integration": {
        "direction_type": "integration approaches",
        "task_type": "research integration with story authenticity",
        "reflection_domains": ["scientific_accuracy", "narrative_flow", "world_consistency", "research_integration", "story_authenticity"],
        "evolution_strategies": ["integration_enhancement"],  # Single evolution strategy
        "output_name": "research_integrated_stories",
        "meta_prompt_key": "narrative_meta",
        "generation_prompt_key": "narrative_generation",
        "model_template": "creative"  # Use creative template for story refinement
    },
    "first_chapter_writing": {
        "direction_type": "narrative approaches",
        "task_type": "first chapter competitive writing",
        "reflection_domains": ["opening_hook", "world_establishment", "character_introduction", "tone_setting", "future_authenticity"],
        "evolution_strategies": ["opening_enhancement"],  # Single evolution strategy
        "output_name": "first_chapters",
        "meta_prompt_key": "chapter_meta",
        "generation_prompt_key": "chapter_generation",
        "model_template": "creative"  # Use creative template for chapter writing
    }
}

class ModelSettings(BaseModel):
    """
    Centralized model settings for different use cases.
    
    Example usage with templates (recommended):
        model_settings = ModelSettings.from_template("creative")  # Apply creative template
        model_settings = ModelSettings.from_template("reasoning") # Apply reasoning template
        
    Example usage for manual phase-specific models:
        model_settings = ModelSettings(
            meta_analysis_model="openai:o3-2025-04-16",     # O3 for deep reasoning
            generation_model="anthropic:claude-3-5-opus-20241022",  # Opus for creative writing
            debate_a_model="openai:o3-2025-04-16",          # O3 for debater A (analytical)
            debate_b_model="anthropic:claude-3-5-opus-20241022",    # Opus for debater B (creative)
            reflection_model="anthropic:claude-3-5-sonnet-20241022"  # Sonnet for critique
        )
        
    Available templates:
        - "creative": Optimized for narrative and creative tasks (Claude 4 Opus + Sonnet + O3)
        - "reasoning": Optimized for analytical and research tasks (O3 + Claude 4 Sonnet)
    """
    
    # Model selection by phase (None = use general_model fallback)
    meta_analysis_model: Optional[str] = Field(default=None, description="Model for meta-analysis phase")
    generation_model: Optional[str] = Field(default=None, description="Model for scenario generation phase")
    debate_model: Optional[str] = Field(default=None, description="Model for debate phase (fallback if A/B not specified)")
    debate_a_model: Optional[str] = Field(default=None, description="Model for debate participant A")
    debate_b_model: Optional[str] = Field(default=None, description="Model for debate participant B")
    reflection_model: Optional[str] = Field(default=None, description="Model for reflection phase")
    evolution_model: Optional[str] = Field(default=None, description="Model for evolution phase")
    tournament_model: Optional[str] = Field(default=None, description="Model for tournament phase")
    meta_review_model: Optional[str] = Field(default=None, description="Model for meta-review phase")
    
    # Temperature settings by phase
    meta_analysis_temperature: float = Field(default=0.8, ge=0.0, le=2.0)
    generation_temperature: float = Field(default=0.9, ge=0.0, le=2.0)
    debate_temperature: float = Field(default=0.8, ge=0.0, le=2.0)
    reflection_temperature: float = Field(default=0.8, ge=0.0, le=2.0)
    evolution_temperature: float = Field(default=0.8, ge=0.0, le=2.0)
    tournament_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    meta_review_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    
    # Token limits by phase
    meta_analysis_max_tokens: int = Field(default=4096, ge=512, le=16384)
    generation_max_tokens: int = Field(default=4096, ge=512, le=16384)
    debate_max_tokens: int = Field(default=4096, ge=512, le=16384)
    reflection_max_tokens: int = Field(default=4096, ge=512, le=16384)
    evolution_max_tokens: int = Field(default=8000, ge=512, le=16384)
    tournament_max_tokens: int = Field(default=4096, ge=512, le=16384)
    meta_review_max_tokens: int = Field(default=4096, ge=512, le=16384)
    
    # Global model settings
    request_timeout: int = Field(default=300, ge=30, le=600)
    max_retries: int = Field(default=3, ge=1, le=10)
    base_delay: float = Field(default=1.0, ge=0.1, le=5.0)
    
    # O3-specific handling
    o3_models: List[str] = Field(default=["o3", "o3-mini"], description="Models that require temperature=1")
    
    def get_model_for_phase(self, phase: str, fallback_model: str) -> str:
        """Get appropriate model for phase with fallback to general_model"""
        phase_models = {
            "meta_analysis": self.meta_analysis_model,
            "generation": self.generation_model,
            "debate": self.debate_model,
            "reflection": self.reflection_model,
            "evolution": self.evolution_model,
            "tournament": self.tournament_model,
            "meta_review": self.meta_review_model
        }
        return phase_models.get(phase) or fallback_model
    
    def get_debate_models(self, fallback_model: str) -> tuple[str, str]:
        """Get models for debate participants A and B with intelligent fallback logic"""
        # First priority: specific A/B models
        model_a = self.debate_a_model
        model_b = self.debate_b_model
        
        # Second priority: general debate model
        debate_fallback = self.debate_model or fallback_model
        
        # Final fallback logic
        model_a = model_a or debate_fallback
        model_b = model_b or debate_fallback
        
        return model_a, model_b
    
    def get_temperature_for_phase(self, phase: str, model_name: str) -> float:
        """Get appropriate temperature for phase and model"""
        # O3 models only support temperature=1
        if any(o3_model in model_name for o3_model in self.o3_models):
            return 1.0
            
        phase_temps = {
            "meta_analysis": self.meta_analysis_temperature,
            "generation": self.generation_temperature,
            "debate": self.debate_temperature,
            "reflection": self.reflection_temperature,
            "evolution": self.evolution_temperature,
            "tournament": self.tournament_temperature,
            "meta_review": self.meta_review_temperature
        }
        return phase_temps.get(phase, 0.8)
    
    def get_max_tokens_for_phase(self, phase: str) -> int:
        """Get appropriate max tokens for phase"""
        phase_tokens = {
            "meta_analysis": self.meta_analysis_max_tokens,
            "generation": self.generation_max_tokens,
            "debate": self.debate_max_tokens,
            "reflection": self.reflection_max_tokens,
            "evolution": self.evolution_max_tokens,
            "tournament": self.tournament_max_tokens,
            "meta_review": self.meta_review_max_tokens
        }
        return phase_tokens.get(phase, 4096)
    
    @classmethod
    def from_template(cls, template_name: str) -> "ModelSettings":
        """Create ModelSettings from a predefined template"""
        if template_name not in MODEL_TEMPLATES:
            available = ", ".join(MODEL_TEMPLATES.keys())
            raise ValueError(f"Unknown template '{template_name}'. Available templates: {available}")
        
        template = MODEL_TEMPLATES[template_name]
        
        # Extract model assignments from template
        model_fields = {
            field: template.get(field) 
            for field in [
                "meta_analysis_model", "generation_model", "debate_model",
                "debate_a_model", "debate_b_model", "reflection_model",
                "evolution_model", "tournament_model", "meta_review_model"
            ]
            if template.get(field) is not None
        }
        
        # Extract temperature settings from template
        temperature_fields = {
            field: template.get(field)
            for field in [
                "meta_analysis_temperature", "generation_temperature", "debate_temperature",
                "reflection_temperature", "evolution_temperature", "tournament_temperature",
                "meta_review_temperature"
            ]
            if template.get(field) is not None
        }
        
        # Combine all fields
        all_fields = {**model_fields, **temperature_fields}
        
        return cls(**all_fields)
    
    def apply_template(self, template_name: str) -> "ModelSettings":
        """Apply a template to current settings (overwrites existing values)"""
        if template_name not in MODEL_TEMPLATES:
            available = ", ".join(MODEL_TEMPLATES.keys())
            raise ValueError(f"Unknown template '{template_name}'. Available templates: {available}")
        
        template = MODEL_TEMPLATES[template_name]
        
        # Create a new instance with template values overriding current values
        current_dict = self.model_dump()
        
        # Update with template values (only non-None values)
        for key, value in template.items():
            if value is not None and hasattr(self, key):
                current_dict[key] = value
        
        return ModelSettings(**current_dict)


class CoScientistConfiguration(BaseModel):
    # Use Case and Process Control
    use_case: UseCase = Field(
        default=UseCase.COMPETITIVE_LOGLINES,
        metadata={
            "x_oap_ui_config": {
                "type": "string",
                "enum": ["competitive_loglines", "competitive_outline", "story_research_integration", "first_chapter_writing"],
                "default": "competitive_loglines",
                "description": "Pre-configured use case template for Deep Sci-Fi workflow"
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
        default=["meta_analysis", "scenario_generation", "reflection", "tournament", "ranking", "debate", "evolution", "evolution_tournament", "meta_review"],
        metadata={
            "x_oap_ui_config": {
                "type": "array",
                "items": {"type": "string"},
                "default": ["meta_analysis", "scenario_generation", "reflection", "tournament", "ranking", "debate", "evolution", "evolution_tournament", "meta_review"],
                "description": "Which phases to enable (for custom control)"
            }
        }
    )
    
    use_meta_analysis_debate: bool = Field(
        default=True,
        metadata={
            "x_oap_ui_config": {
                "type": "boolean",
                "default": True,
                "description": "Use expert panel debate for meta-analysis instead of single LLM"
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
    
    # Centralized Model Settings
    model_settings: ModelSettings = Field(
        default_factory=ModelSettings,
        metadata={
            "x_oap_ui_config": {
                "type": "object",
                "description": "Centralized model configuration for all phases (supports per-phase model selection)"
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
    
    phase: Optional[str] = Field(
        default=None,
        metadata={
            "x_oap_ui_config": {
                "type": "string",
                "default": None,
                "description": "Current phase/node name from deep-sci-fi graph (for output folder naming)"
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
            
        use_case_config = USE_CASE_CONFIGS.get(self.use_case.value, USE_CASE_CONFIGS["scenario_generation"])
        return use_case_config["reflection_domains"]
    
    def get_evolution_strategies(self) -> List[str]:
        """Get evolution strategies based on use case."""
        if self.evolution_strategies is not None:
            return self.evolution_strategies
            
        use_case_config = USE_CASE_CONFIGS.get(self.use_case.value, USE_CASE_CONFIGS["scenario_generation"])
        return use_case_config["evolution_strategies"]
    
    def get_enabled_phases_for_depth(self) -> List[str]:
        """Get enabled phases based on process depth."""
        all_phases = ["meta_analysis", "scenario_generation", "reflection", "tournament", "ranking", "debate", "evolution", "evolution_tournament", "meta_review"]
        
        if self.process_depth == ProcessDepth.QUICK:
            return ["meta_analysis", "scenario_generation", "tournament", "ranking", "debate", "meta_review"]
        elif self.process_depth == ProcessDepth.STANDARD:
            return ["meta_analysis", "scenario_generation", "reflection", "tournament", "ranking", "debate", "evolution", "meta_review"]
        elif self.process_depth == ProcessDepth.COMPREHENSIVE:
            return all_phases
        else:
            # Use custom enabled_phases
            return self.enabled_phases
    
    def get_use_case_config(self) -> Dict:
        """Get the configuration for the current use case."""
        return USE_CASE_CONFIGS.get(self.use_case.value, USE_CASE_CONFIGS["competitive_loglines"])
    
    def get_phase_list(self) -> List[str]:
        """Get the list of phases to run based on process depth."""
        return self.get_enabled_phases_for_depth()
    
    def get_template_name(self) -> str:
        """Get the model template for the current use case."""
        use_case_config = self.get_use_case_config()
        return use_case_config.get("model_template", "creative")  # Default to creative
    
    def get_model_settings_with_template(self) -> ModelSettings:
        """Get model settings with the use case template applied."""
        template_name = self.get_template_name()
        
        # If model_settings is already customized, apply template as base then override
        if any([
            self.model_settings.meta_analysis_model,
            self.model_settings.generation_model,
            self.model_settings.debate_a_model,
            self.model_settings.debate_b_model,
            # ... other model fields have been manually set
        ]):
            # User has customized settings, start with template then apply their overrides
            template_settings = ModelSettings.from_template(template_name)
            current_dict = template_settings.model_dump()
            user_dict = self.model_settings.model_dump(exclude_unset=True, exclude_none=True)
            current_dict.update(user_dict)
            return ModelSettings(**current_dict)
        else:
            # No customization, just use the template
            return ModelSettings.from_template(template_name)

    @classmethod
    def create_input_state(cls, 
                          use_case: UseCase = UseCase.COMPETITIVE_LOGLINES,
                          context: str = None,
                          storyline: str = None,
                          chapter_arcs: str = None,
                          **legacy_fields) -> dict:
        """Create a properly formatted input state for co_scientist.
        
        Args:
            use_case: Which template to use
            context: Background information, requirements, constraints (optional)
            storyline: The storyline for chapter writing (optional)
            chapter_arcs: The chapter arcs for chapter writing (optional)
            **legacy_fields: Backward compatibility fields like storyline, target_year, etc.
        
        Returns:
            Dictionary formatted for CoScientistInputState
        """
        input_state = {
            "use_case": use_case.value if hasattr(use_case, 'value') else use_case
        }
        
        if context:
            input_state["context"] = context
        if storyline:
            input_state["storyline"] = storyline
        if chapter_arcs:
            input_state["chapter_arcs"] = chapter_arcs
            
        # For backward compatibility and other use cases
        if "reference_material" in legacy_fields:
            input_state["reference_material"] = legacy_fields["reference_material"]
            
        input_state.update(legacy_fields)
        
        return input_state

    @classmethod
    def from_runnable_config(cls, config: RunnableConfig) -> "CoScientistConfiguration":
        """Create configuration from a RunnableConfig."""
        try:
            configurable = config.get("configurable", {})
            
            # Debug logging for configuration
            print(f"Debug - CoScientistConfiguration.from_runnable_config:")
            print(f"  config keys: {list(config.keys()) if config else 'None'}")
            print(f"  configurable keys: {list(configurable.keys()) if configurable else 'None'}")
            
            # Check for phase parameter specifically
            phase = configurable.get("phase")
            print(f"  phase parameter: {phase}")
            print(f"  use_case: {configurable.get('use_case', 'missing')}")
            print(f"  research_model: {configurable.get('research_model', 'missing')}")
            print(f"  general_model: {configurable.get('general_model', 'missing')}")
            
            return cls(
                research_model=configurable.get("research_model", "gpt-4"),
                general_model=configurable.get("general_model", "gpt-3.5-turbo"), 
                use_case=UseCase(configurable.get("use_case", "competitive_loglines")),
                process_depth=configurable.get("process_depth", "standard"),
                population_scale=configurable.get("population_scale", "medium"),
                use_deep_researcher=configurable.get("use_deep_researcher", False),
                search_api=configurable.get("search_api", "tavily"),
                reflection_domains=configurable.get("reflection_domains", ["physics", "biology", "engineering", "social_science", "economics"]),
                world_state_context=configurable.get("world_state_context", ""),
                save_intermediate_results=configurable.get("save_intermediate_results", True),
                output_dir=configurable.get("output_dir", "output"),
                phase=configurable.get("phase")
            )
            
        except Exception as e:
            print(f"Error in CoScientistConfiguration.from_runnable_config: {e}")
            import traceback
            print(f"Configuration parsing traceback:")
            print(traceback.format_exc())
            # Return a default configuration to prevent total failure
            return cls() 