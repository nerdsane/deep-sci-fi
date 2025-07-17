from typing import Annotated, Optional, List, Dict, Any
from pydantic import BaseModel, Field
import operator
from typing_extensions import TypedDict

###################
# Structured Outputs
###################

class MetaAnalysisOutput(BaseModel):
    """Output from meta-analysis to identify research directions."""
    research_directions: List[Dict[str, str]] = Field(
        description="List of 3 distinct research directions with assumptions"
    )
    reasoning: str = Field(
        description="Reasoning for why these directions provide meaningful variety"
    )

class ScenarioGeneration(BaseModel):
    """A single generated scenario from a research team."""
    scenario_content: str = Field(
        description="The complete scenario addressing all world-building questions"
    )
    research_direction: str = Field(
        description="Which research direction this scenario follows"
    )
    team_id: str = Field(
        description="Unique identifier for the research team"
    )

class ReflectionCritique(BaseModel):
    """Critique from a reflection agent."""
    target_scenario_id: str = Field(
        description="ID of the scenario being critiqued"
    )
    critique_domain: str = Field(
        description="Domain of expertise (physics, biology, engineering, etc.)"
    )
    critique_content: str = Field(
        description="Detailed scientific critique and suggestions"
    )
    severity_score: int = Field(
        description="Severity of issues found (1-10, 10 = major problems)"
    )

class TournamentComparison(BaseModel):
    """Result of pairwise scenario comparison."""
    scenario1_id: str
    scenario2_id: str
    winner_id: str = Field(
        description="ID of the winning scenario"
    )
    reasoning: str = Field(
        description="Detailed reasoning for the comparison decision"
    )
    criteria_scores: Dict[str, int] = Field(
        description="Scores for different evaluation criteria"
    )

class EvolutionImprovement(BaseModel):
    """Evolved version of a scenario."""
    original_scenario_id: str
    evolved_content: str = Field(
        description="Improved scenario content"
    )
    evolution_type: str = Field(
        description="Type of evolution applied (feasibility, creativity, synthesis, etc.)"
    )
    improvements_made: List[str] = Field(
        description="List of specific improvements made"
    )

###################
# State Definitions
###################

def override_reducer(current_value, new_value):
    """Custom reducer that allows overriding values."""
    if isinstance(new_value, dict) and new_value.get("type") == "override":
        return new_value.get("value", new_value)
    else:
        return operator.add(current_value, new_value)

class CoScientistInputState(TypedDict):
    """Input state for the co-scientist subgraph."""
    research_context: str  # The research questions and context
    storyline: Optional[str]  # Story context for scenario generation
    target_year: Optional[int]  # Target year for projections
    baseline_world_state: Optional[str]  # Current world state if available
    years_in_future: Optional[int]  # Years to project forward

class CoScientistState(CoScientistInputState):
    """Complete state for the co-scientist competition process."""
    
    # Meta-analysis outputs
    research_directions: List[Dict[str, str]]
    meta_analysis_reasoning: str
    
    # Population generation
    scenario_population: Annotated[List[Dict[str, Any]], override_reducer]
    generation_complete: bool
    
    # Reflection phase
    reflection_critiques: Annotated[List[Dict[str, Any]], override_reducer]
    reflection_complete: bool
    
    # Tournament phase
    tournament_rounds: Annotated[List[Dict[str, Any]], override_reducer]
    tournament_winners: List[Dict[str, Any]]
    tournament_complete: bool
    
    # Evolution phase
    evolved_scenarios: Annotated[List[Dict[str, Any]], override_reducer]
    evolution_complete: bool
    
    # Evolution tournament phase
    evolution_tournament_results: Annotated[List[Dict[str, Any]], override_reducer]
    final_representatives: List[Dict[str, Any]]  # Best scenario from each direction after evolution
    evolution_tournament_complete: bool
    
    # Final outputs
    top_scenarios: List[Dict[str, str]]  # Final 3 scenarios for user selection
    competition_summary: str  # Summary of the competition process

class TournamentDirectionState(TypedDict):
    """State for a single tournament direction."""
    direction_info: Dict[str, str]  # Direction details and assumptions
    research_teams: List[Dict[str, str]]  # Team assignments
    raw_scenarios: List[Dict[str, Any]]  # Generated scenarios
    critiques: List[Dict[str, Any]]  # Reflection critiques
    tournament_bracket: List[Dict[str, Any]]  # Tournament comparisons
    winner_scenario: Dict[str, Any]  # Final winner from this direction
    evolution_results: List[Dict[str, Any]] 