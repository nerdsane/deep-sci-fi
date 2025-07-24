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
    """Input state for the co-scientist subgraph - flexible for different use cases."""
    # Core fields (universal) - optional for backward compatibility
    task_description: Optional[str]  # What the competitive process should accomplish
    context: Optional[str]  # Background information, requirements, constraints
    
    # Optional fields for different use cases
    reference_material: Optional[str]  # Existing content to work with (e.g., current chapter, character)
    domain_context: Optional[str]  # Genre/domain-specific context
    use_case: Optional[str]  # Which template to use (defaults to "scenario_generation")
    
    # Legacy fields for backward compatibility (scenario generation)
    research_context: Optional[str]  # Alias for 'context' in scenario generation
    storyline: Optional[str]  # Story context for scenario generation  
    target_year: Optional[int]  # Target year for projections
    baseline_world_state: Optional[str]  # Current world state if available
    years_in_future: Optional[int]  # Years to project forward

class CoScientistState(CoScientistInputState):
    """Complete state for the co-scientist competition process."""
    
    # Meta-analysis phase
    research_directions: Annotated[List[Dict[str, Any]], override_reducer]
    meta_analysis_reasoning: str
    
    # Meta-analysis debate phase (when using LLM vs LLM debate)
    llm_debate_conversation: Optional[str]  # Full LLM vs LLM conversation transcript
    debate_conclusion: Optional[str]  # Final conclusion from LLM debate
    
    # Legacy fields (kept for backward compatibility)
    expert_proposals: Optional[List[Dict[str, Any]]]  # Individual expert domain proposals  
    debate_transcript: Optional[str]  # Debate transcript (now stores LLM conversation)
    
    # Generation phase
    scenario_population: Annotated[List[Dict[str, Any]], override_reducer]
    generation_complete: bool
    
    # Reflection phase
    reflection_critiques: Annotated[List[Dict[str, Any]], override_reducer]
    reflection_complete: bool
    
    # Tournament phase
    tournament_rounds: Annotated[List[Dict[str, Any]], override_reducer]
    tournament_winners: List[Dict[str, Any]]
    tournament_complete: bool
    
    # Ranking phase
    leaderboard_data: Dict[str, Any]  # Comprehensive Elo-based leaderboard and analytics
    ranking_complete: bool
    
    # Debate phase  
    debate_winner: Optional[Dict[str, Any]]  # Winner of final debate between top 2
    debate_transcript: Optional[str]  # Full debate transcript
    debate_participants: Optional[List[Dict[str, Any]]]  # Top 2 scenarios that debated
    debate_summary_for_evolution: Optional[str]  # Debate outcome summary for evolution phase
    debate_complete: bool
    
    # Evolution phase
    evolved_scenarios: Annotated[List[Dict[str, Any]], override_reducer]
    evolution_complete: bool
    
    # Evolution tournament phase
    evolution_tournament_results: Annotated[List[Dict[str, Any]], override_reducer]
    final_representatives: List[Dict[str, Any]]  # Best scenario from each direction after evolution
    evolution_tournament_complete: bool
    
    # Final outputs
    direction_winners: List[Dict[str, Any]]  # Final 2 direction winners for user selection
    top_scenarios: List[Dict[str, str]]  # Final 3 scenarios for user selection  
    process_analysis: str  # Meta-review process analysis
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