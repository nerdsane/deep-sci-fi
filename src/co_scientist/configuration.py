from pydantic import BaseModel, Field
from typing import Optional, List
from langchain_core.runnables import RunnableConfig

class CoScientistConfiguration(BaseModel):
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
    
    # Tournament Configuration
    scenarios_per_direction: int = Field(
        default=6,
        metadata={
            "x_oap_ui_config": {
                "type": "number",
                "default": 6,
                "min": 3,
                "max": 10,
                "description": "Number of scenarios to generate for each research direction"
            }
        }
    )
    
    parallel_directions: int = Field(
        default=3,
        metadata={
            "x_oap_ui_config": {
                "type": "number",
                "default": 3,
                "min": 2,
                "max": 5,
                "description": "Number of parallel research directions to explore"
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
    
    # Reflection Configuration
    reflection_domains: List[str] = Field(
        default=["physics", "biology", "engineering", "social_science", "economics"],
        metadata={
            "x_oap_ui_config": {
                "type": "array",
                "items": {"type": "string"},
                "default": ["physics", "biology", "engineering", "social_science", "economics"],
                "description": "Domains of expertise for reflection agents"
            }
        }
    )
    
    # Evolution Configuration
    evolution_strategies: List[str] = Field(
        default=["feasibility", "creativity", "synthesis", "detail_enhancement"],
        metadata={
            "x_oap_ui_config": {
                "type": "array", 
                "items": {"type": "string"},
                "default": ["feasibility", "creativity", "synthesis", "detail_enhancement"],
                "description": "Types of evolution to apply to winning scenarios"
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

    @classmethod
    def from_runnable_config(cls, config: RunnableConfig) -> "CoScientistConfiguration":
        """Create configuration from a RunnableConfig."""
        configurable = config.get("configurable", {})
        return cls(**configurable) 