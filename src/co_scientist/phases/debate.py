"""
Debate Phase - LLM vs LLM Collaborative Evaluation

This module handles collaborative evaluation debates between LLM experts to determine
final winners and generate research directions. It supports both meta-analysis debates
for direction generation and tournament debates for competitive scenario evaluation.

Key Features:
- LLM vs LLM collaborative consultation with natural conversation flow
- Multiple debate types (meta-analysis, tournament)
- Configurable debate rounds and consensus detection
- Use case-specific debate goals and criteria
- Comprehensive result parsing and winner determination
"""

import asyncio
from typing import Dict, List, Any, Literal

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from co_scientist.state import CoScientistState
from co_scientist.configuration import CoScientistConfiguration
from co_scientist.utils.output_manager import get_output_manager
from co_scientist.utils.content_formatters import format_content
from co_scientist.prompts import (
    get_llm_debate_meta_analysis_prompt_a, get_llm_debate_meta_analysis_prompt_b,
    get_llm_debate_meta_analysis_continue_a, get_llm_debate_meta_analysis_continue_b,
    get_llm_debate_tournament_prompt_a, get_llm_debate_tournament_prompt_b,
    get_llm_debate_tournament_final_a, get_llm_debate_tournament_final_b
)


async def debate_phase(state: CoScientistState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Conduct collaborative evaluation between top 2 scenarios to determine final winner.
    
    This is the main entry point for the final debate phase where the top-ranked
    scenarios compete in a structured LLM vs LLM debate to determine the ultimate
    winner based on use case-specific criteria.
    
    Args:
        state: Current workflow state containing leaderboard and scenario data
        config: LangGraph configuration with debate settings
        
    Returns:
        dict: Updated state with debate winner, transcript, and outcome data
    """
    configuration = CoScientistConfiguration.from_runnable_config(config)
    
    print(f"🗣️ DEBATE PHASE: Starting final tournament LLM vs LLM debate")
    
    # Debug: Check what data we're receiving
    print(f"🔍 DEBUG: State keys available: {list(state.keys())}")
    print(f"🔍 DEBUG: Leaderboard data type: {type(state.get('leaderboard_data', 'missing'))}")
    
    # Get leaderboard data to find top 2 scenarios
    leaderboard_data = state.get("leaderboard_data", {})
    rankings = leaderboard_data.get("rankings", [])
    
    print(f"📊 Found {len(rankings)} ranked scenarios for debate")
    print(f"🔍 DEBUG: Leaderboard data keys: {list(leaderboard_data.keys()) if leaderboard_data else 'No leaderboard data'}")
    
    if len(rankings) > 0:
        print(f"🔍 DEBUG: First ranking entry keys: {list(rankings[0].keys()) if rankings[0] else 'Empty ranking'}")
        print(f"🔍 DEBUG: Top 2 scenarios:")
        for i, scenario in enumerate(rankings[:2]):
            print(f"    #{i+1}: {scenario.get('team_id', 'unknown')} (Elo: {scenario.get('final_elo_rating', 'unknown')})")
    else:
        print(f"🔍 DEBUG: No rankings found!")
    
    if len(rankings) < 2:
        print("Insufficient scenarios for debate - need at least 2 ranked scenarios")
        return {
            "debate_winner": rankings[0] if rankings else None,
            "debate_complete": True,
            "debate_transcript": "No debate conducted - insufficient participants"
        }
    
    # Get top 2 scenarios
    scenario_1 = rankings[0]  # #1 ranked
    scenario_2 = rankings[1]  # #2 ranked
    
    print(f"🗣️ Starting debate between:")
    print(f"  #1: {scenario_1['team_id']} ({scenario_1['final_elo_rating']:.0f} Elo)")
    print(f"  #2: {scenario_2['team_id']} ({scenario_2['final_elo_rating']:.0f} Elo)")
    
    # Find full scenario content from population
    scenario_population = state.get("scenario_population", [])
    
    scenario_1_content = None
    scenario_2_content = None
    
    for scenario in scenario_population:
        if scenario.get("scenario_id") == scenario_1["scenario_id"]:
            scenario_1_content = scenario.get("scenario_content", "Content not found")
        elif scenario.get("scenario_id") == scenario_2["scenario_id"]:
            scenario_2_content = scenario.get("scenario_content", "Content not found")
    
    # Get reflection critiques as initial reviews
    reflection_critiques = state.get("reflection_critiques", [])
    
    scenario_1_review = "No initial review available"
    scenario_2_review = "No initial review available"
    
    for critique in reflection_critiques:
        if critique.get("scenario_id") == scenario_1["scenario_id"]:
            scenario_1_review = critique.get("critique_content", "Review not found")
        elif critique.get("scenario_id") == scenario_2["scenario_id"]:
            scenario_2_review = critique.get("critique_content", "Review not found")
    
    # Create use case-specific debate prompt
    use_case_config = configuration.get_use_case_config()
    
    # Define debate parameters based on use case
    debate_goals = {
        "scenario_generation": "Determine which sci-fi scenario provides the most compelling and scientifically grounded foundation for world-building",
        "storyline_creation": "Determine which storyline offers the most engaging and narratively compelling foundation for the novel",
        "storyline_adjustment": "Determine which revised storyline best integrates world-building while maintaining narrative excellence",
        "chapter_writing": "Determine which chapter demonstrates superior prose quality and immersive storytelling",
        "chapter_rewriting": "Determine which rewritten chapter best integrates world-building with literary excellence",
        "chapter_arcs_creation": "Determine which chapter arc structure provides the most effective narrative architecture",
        "chapter_arcs_adjustment": "Determine which adjusted chapter arc best serves the integrated storyline",
        "linguistic_evolution": "Determine which linguistic evolution analysis demonstrates superior academic rigor and cultural authenticity"
    }
    
    debate_criteria = {
        "scenario_generation": "Scientific feasibility, technological plausibility, internal consistency, narrative potential, innovation within constraints",
        "storyline_creation": "Narrative strength, character development, plot coherence, reader engagement, originality and uniqueness",
        "storyline_adjustment": "World integration, narrative coherence, character consistency, thematic enhancement, story flow",
        "chapter_writing": "Prose quality, world integration, character authenticity, immersion effectiveness, literary craftsmanship",
        "chapter_rewriting": "World integration, prose enhancement, character authenticity, narrative flow, immersion quality",
        "chapter_arcs_creation": "Narrative architecture, pacing strategy, character development progression, reader engagement, structural innovation",
        "chapter_arcs_adjustment": "Structure optimization, world integration, character progression, plot consistency, thematic alignment",
        "linguistic_evolution": "Linguistic accuracy, evolutionary plausibility, methodological soundness, cultural authenticity, academic rigor"
    }
    
    use_case = configuration.use_case.value
    goal = debate_goals.get(use_case, debate_goals["scenario_generation"])
    preferences = debate_criteria.get(use_case, debate_criteria["scenario_generation"])
    
    # Conduct LLM vs LLM debate
    debate_result = await conduct_llm_vs_llm_debate(
        use_case,
        "tournament",
        configuration,
        max_rounds=3,  # Tournament debates typically shorter
        goal=goal,
        criteria=preferences,
        scenario_1_content=scenario_1_content,
        scenario_2_content=scenario_2_content,
        scenario_1_review=scenario_1_review,
        scenario_2_review=scenario_2_review
    )
    
    try:
        print("🤖 Conducting LLM vs LLM debate...")
        debate_transcript = debate_result["full_conversation"]
        
        # Parse collaborative consultation result
        debate_winner_id = None
        final_conclusion = debate_result["final_conclusion"]
        
        # Support multiple winner declaration formats for robustness
        if ("BETTER OPTION: 1" in final_conclusion or 
            "CONSENSUS WINNER: SCENARIO 1" in final_conclusion or 
            "WINNER: SCENARIO 1" in final_conclusion):
            debate_winner = scenario_1
            debate_winner_id = scenario_1["scenario_id"]
            print(f"🏆 Collaborative winner: #{1} {scenario_1['team_id']}")
        elif ("BETTER OPTION: 2" in final_conclusion or
              "CONSENSUS WINNER: SCENARIO 2" in final_conclusion or 
              "WINNER: SCENARIO 2" in final_conclusion):
            debate_winner = scenario_2  
            debate_winner_id = scenario_2["scenario_id"]
            print(f"🏆 Collaborative winner: #{2} {scenario_2['team_id']}")
        else:
            # Fallback to #1 ranked if parsing fails
            debate_winner = scenario_1
            debate_winner_id = scenario_1["scenario_id"]
            print(f"⚠️ Collaborative result unclear - defaulting to #1 ranked: {scenario_1['team_id']}")
        
        print(f"📝 LLM debate conversation length: {len(debate_transcript)} characters")
        print(f"🔄 Debate rounds completed: {debate_result['conversation_rounds']}")
        
    except Exception as e:
        print(f"❌ Debate failed: {e}")
        # Fallback to #1 ranked
        debate_winner = scenario_1
        debate_winner_id = scenario_1["scenario_id"]
        debate_transcript = f"Debate failed due to error: {str(e)}. Defaulting to #1 ranked scenario."
    
    # Save debate results
    debate_outcome = None
    if configuration.save_intermediate_results:
        manager = get_output_manager(configuration.output_dir, configuration.phase)
        
        # Save full debate transcript (both formats)
        print(f"💾 Saving final debate transcript...")
        manager.save_simple_content("final_debate_transcript.md", debate_transcript, "debate")
        
        # Save chat format if available
        if "chat_conversation" in debate_result:
            manager.save_simple_content("final_debate_chat.md", debate_result["chat_conversation"], "debate")
        
        # Save debate summary
        debate_summary = f"""# Final Debate Results
        
**Participants:**
- Scenario 1: {scenario_1['team_id']} (#{scenario_1['rank']}, {scenario_1['final_elo_rating']:.0f} Elo)
- Scenario 2: {scenario_2['team_id']} (#{scenario_2['rank']}, {scenario_2['final_elo_rating']:.0f} Elo)

**Winner:** {debate_winner['team_id']}

**Goal:** {goal}

**Criteria:** {preferences}

**Decision:** The collaborative analysis concluded that {"Scenario 1" if debate_winner_id == scenario_1["scenario_id"] else "Scenario 2"} provides the superior solution based on the established criteria.
"""
        manager.save_simple_content("debate_summary.md", debate_summary, "debate")
        
        # Save debate outcome data for evolution use
        debate_outcome = {
            "winner_id": debate_winner_id,
            "winner_rank": debate_winner["rank"],
            "losing_scenario_id": scenario_2["scenario_id"] if debate_winner_id == scenario_1["scenario_id"] else scenario_1["scenario_id"],
            "losing_scenario_rank": scenario_2["rank"] if debate_winner_id == scenario_1["scenario_id"] else scenario_1["rank"],
            "goal": goal,
            "criteria": preferences,
            "key_strengths": f"Collaborative analysis identified superior performance in: {preferences}",
            "comparative_analysis": f"Debate winner demonstrated stronger performance compared to the #{'2' if debate_winner_id == scenario_1['scenario_id'] else '1'} ranked scenario through structured expert analysis.",
            "evolution_guidance": f"Future evolution should focus on maintaining the winning elements while addressing any weaknesses identified in the collaborative evaluation.",
            "transcript_excerpt": debate_transcript[:500] + "..." if len(debate_transcript) > 500 else debate_transcript
        }
        manager.save_structured_data("debate_data", debate_outcome, filename="debate_outcome.json", subdirectory="debate")
    
    # Create comprehensive debate summary for evolution phase
    debate_summary_for_evolution = f"""DEBATE OUTCOME ANALYSIS:

Winner: {debate_winner['team_id']} (Originally ranked #{debate_winner['rank']})
Defeated: {"#2" if debate_winner_id == scenario_1["scenario_id"] else "#1"} ranked scenario

Collaborative Analysis Decision Criteria:
{preferences}

Key Decision Factors:
- The winning scenario demonstrated superior performance across the established criteria
- Collaborative analysis conducted structured evaluation comparing both approaches
- Decision based on: {goal}

Evolution Guidance:
- Maintain the core strengths that led to debate victory
- Address any weaknesses identified during collaborative evaluation
- Build upon the winning approach's foundation

Debate Context:
This scenario emerged as the final champion after defeating the other top-ranked scenario in structured expert analysis, indicating strong foundational elements worth preserving and enhancing."""
    
    return {
        "debate_winner": debate_winner,
        "debate_transcript": debate_transcript,
        "debate_participants": [scenario_1, scenario_2],
        "debate_summary_for_evolution": debate_summary_for_evolution,
        "debate_outcome": debate_outcome,
        "debate_complete": True
    }


async def conduct_llm_vs_llm_debate(use_case: str, debate_type: str, configuration, num_directions: int = 3, max_rounds: int = 4, **kwargs) -> Dict[str, Any]:
    """
    Conduct collaborative consultation conversation between two LLM instances.
    
    This function orchestrates a natural conversation between two LLM experts, supporting
    both meta-analysis debates for research direction generation and tournament debates
    for competitive scenario evaluation.
    
    Args:
        use_case: Type of content being debated
        debate_type: Either "meta_analysis" or "tournament"
        configuration: Configuration object with model settings
        num_directions: Number of research directions to generate (meta-analysis only)
        max_rounds: Maximum conversation rounds
        **kwargs: Additional parameters specific to debate type
        
    Returns:
        dict: Debate results with conversation, conclusion, and metadata
    """
    print(f"🗣️ Starting LLM vs LLM debate for {debate_type}")
    
    # Import legacy functions (will be replaced with direct LLMManager calls in future)
    from co_scientist.co_scientist import create_isolated_model_instance, llm_call_with_retry
    
    # Create two isolated LLM instances
    llm_a = create_isolated_model_instance(
        model_name=configuration.general_model,
        max_tokens=4096,
        temperature=0.8  # Slightly creative for debate
    )
    
    llm_b = create_isolated_model_instance(
        model_name=configuration.general_model,
        max_tokens=4096,
        temperature=0.8  # Slightly creative for debate
    )
    
    # Initialize conversation
    conversation_history = []
    final_conclusion = ""
    
    if debate_type == "meta_analysis":
        # Meta-analysis debate: Generate research directions
        
        # Map state parameters to template parameters for each use case
        template_kwargs = kwargs.copy()
        context_value = kwargs.get("context", "")
        
        if use_case == "scenario_generation":
            template_kwargs["storyline"] = kwargs.get("reference_material", "")
            template_kwargs["world_building_questions"] = context_value
            template_kwargs["target_year"] = kwargs.get("target_year", "future")
        elif use_case == "storyline_creation":
            template_kwargs["story_concept"] = context_value
            template_kwargs["source_content"] = kwargs.get("reference_material", "")
        elif use_case == "chapter_writing":
            template_kwargs["storyline"] = kwargs.get("storyline", "")
            template_kwargs["chapter_arcs"] = kwargs.get("chapter_arcs", "")
        elif use_case == "linguistic_evolution":
            template_kwargs["source_content"] = kwargs.get("reference_material", "")
            template_kwargs["target_year"] = kwargs.get("target_year", "future")
            template_kwargs["years_in_future"] = kwargs.get("years_in_future", "many")
        elif use_case == "storyline_adjustment":
            template_kwargs["source_content"] = kwargs.get("reference_material", "")
        elif use_case == "chapter_rewriting":
            template_kwargs["source_content"] = kwargs.get("reference_material", "")
        elif use_case in ["chapter_arcs_creation", "chapter_arcs_adjustment"]:
            template_kwargs["story_concept"] = context_value
            template_kwargs["source_content"] = kwargs.get("reference_material", "")
        
        # Expert A starts the conversation naturally
        source_content = template_kwargs.get('source_content', template_kwargs.get('reference_material', 'None provided'))
        prompt_a = get_llm_debate_meta_analysis_prompt_a(use_case, num_directions, context_value, source_content)
        
        print("💬 Expert A: Starting the conversation...")
        
        response_a = await llm_call_with_retry(llm_a, [HumanMessage(content=prompt_a)])
        proposals_a = response_a.content
        
        conversation_history.append({"speaker": "expert_a", "content": proposals_a})
        print(f"  ✅ Expert A shared {num_directions} directions")
        
        # Expert B responds naturally to Expert A
        conversation_context = format_content("conversation_context", conversation_history)
        prompt_b = get_llm_debate_meta_analysis_prompt_b(use_case, num_directions, conversation_context)

        print("💬 Expert B: Responding to Expert A...")
        
        response_b = await llm_call_with_retry(llm_b, [HumanMessage(content=prompt_b)])
        proposals_b = response_b.content
        
        conversation_history.append({"speaker": "expert_b", "content": proposals_b})
        print(f"  ✅ Expert B provided response and alternatives")
        
        # Continue debate until consensus or max rounds reached
        for round_num in range(2, max_rounds + 1):  # Configurable max rounds
            print(f"🔄 Debate Round {round_num}...")
            
            # Expert A continues the conversation
            conversation_context = format_content("conversation_context", conversation_history)
            prompt_a_continue = get_llm_debate_meta_analysis_continue_a(use_case, num_directions, conversation_context)

            response_a_continue = await llm_call_with_retry(llm_a, [HumanMessage(content=prompt_a_continue)])
            response_a_text = response_a_continue.content
            
            conversation_history.append({"speaker": "expert_a", "content": response_a_text})
            
            # Check if consensus reached
            if "FINAL CONSENSUS:" in response_a_text:
                print(f"  ✅ Consensus reached in round {round_num}!")
                final_conclusion = response_a_text
                break
            
            # Expert B responds
            conversation_context = format_content("conversation_context", conversation_history)
            prompt_b_continue = get_llm_debate_meta_analysis_continue_b(use_case, num_directions, conversation_context)

            response_b_continue = await llm_call_with_retry(llm_b, [HumanMessage(content=prompt_b_continue)])
            response_b_text = response_b_continue.content
            
            conversation_history.append({"speaker": "expert_b", "content": response_b_text})
            
            # Check if consensus reached
            if "FINAL CONSENSUS:" in response_b_text:
                print(f"  ✅ Consensus reached in round {round_num}!")
                final_conclusion = response_b_text
                break
                
            final_conclusion = response_b_text  # Use last response if no consensus marker
    
    elif debate_type == "tournament":
        # Tournament debate: Pick winner between 2 scenarios
        scenario_1_content = kwargs.get("scenario_1_content", "Option 1")
        scenario_2_content = kwargs.get("scenario_2_content", "Option 2")
        
        # Expert A reviews and advocates for scenario 1
        prompt_a = get_llm_debate_tournament_prompt_a(use_case, scenario_1_content, scenario_2_content)
        
        print("💬 Expert A: Evaluating Option 1...")
        
        response_a = await llm_call_with_retry(llm_a, [HumanMessage(content=prompt_a)])
        argument_a = response_a.content
        
        conversation_history.append({"speaker": "expert_a", "content": argument_a})
        
        # Expert B reviews and advocates for scenario 2, seeing Expert A's argument
        conversation_context = format_content("conversation_context", conversation_history)
        prompt_b = get_llm_debate_tournament_prompt_b(use_case, scenario_2_content, conversation_context)

        print("💬 Expert B: Evaluating Option 2...")
        
        response_b = await llm_call_with_retry(llm_b, [HumanMessage(content=prompt_b)])
        argument_b = response_b.content
        
        conversation_history.append({"speaker": "expert_b", "content": argument_b})
        
        # Final round: both make concluding assessments
        conversation_context = format_content("conversation_context", conversation_history)
        
        # Expert A final assessment
        prompt_a_final = get_llm_debate_tournament_final_a(conversation_context)

        response_a_final = await llm_call_with_retry(llm_a, [HumanMessage(content=prompt_a_final)])
        final_a = response_a_final.content
        
        conversation_history.append({"speaker": "expert_a", "content": final_a})
        
        # Expert B final assessment  
        conversation_context = format_content("conversation_context", conversation_history)
        prompt_b_final = get_llm_debate_tournament_final_b(conversation_context)

        response_b_final = await llm_call_with_retry(llm_b, [HumanMessage(content=prompt_b_final)])
        final_b = response_b_final.content
        
        conversation_history.append({"speaker": "expert_b", "content": final_b})
        
        # Determine winner based on collaborative consensus
        if (("BETTER OPTION: 1" in final_a or "WINNER: SCENARIO 1" in final_a) and 
            ("BETTER OPTION: 1" in final_b or "WINNER: SCENARIO 1" in final_b)):
            final_conclusion = "BETTER OPTION: 1 (Consensus)"
        elif (("BETTER OPTION: 2" in final_a or "WINNER: SCENARIO 2" in final_a) and 
              ("BETTER OPTION: 2" in final_b or "WINNER: SCENARIO 2" in final_b)):
            final_conclusion = "BETTER OPTION: 2 (Consensus)"
        elif "BETTER OPTION: 1" in final_b or "WINNER: SCENARIO 1" in final_b:
            final_conclusion = "BETTER OPTION: 1 (Expert B conclusion)"
        elif "BETTER OPTION: 2" in final_a or "WINNER: SCENARIO 2" in final_a:
            final_conclusion = "BETTER OPTION: 2 (Expert A conclusion)"
        else:
            # Default to LLM B's choice (they had last word)
            final_conclusion = final_b
    
    # Format conversation for raw transcript
    conversation_lines = []
    for exchange in conversation_history:
        if isinstance(exchange, dict):
            speaker = exchange.get("speaker", "unknown")
            content = exchange.get("content", "")
            if speaker == "expert_a":
                conversation_lines.append(f"Expert A:\n{content}")
            elif speaker == "expert_b":
                conversation_lines.append(f"Expert B:\n{content}")
            else:
                conversation_lines.append(f"{speaker}:\n{content}")
        else:
            # Legacy format fallback
            conversation_lines.append(str(exchange))
    
    full_conversation = "\n\n" + "="*50 + "\n\n".join(conversation_lines)
    
    # Create chat-style conversation format
    chat_conversation = format_content("chat_conversation", {"conversation_history": conversation_history, "debate_type": debate_type})
    
    print(f"🏁 LLM debate completed. Total conversation length: {len(full_conversation)} characters")
    print(f"📝 Formatted as {len(conversation_history)} conversation exchanges")
    print(f"🔄 Completed {len(conversation_history)} rounds (max allowed: {max_rounds})")
    
    return {
        "full_conversation": full_conversation,
        "chat_conversation": chat_conversation,
        "final_conclusion": final_conclusion,
        "conversation_rounds": len(conversation_history),
        "debate_type": debate_type,
        "max_rounds_allowed": max_rounds
    }


def parse_debate_result_directions(conclusion_text: str) -> List[Dict[str, str]]:
    """
    Parse research directions from LLM collaborative consultation conclusion.
    
    This function extracts structured research direction data from the final
    debate conclusion, supporting both legacy and modern formats for backward
    compatibility.
    
    Args:
        conclusion_text: Raw text conclusion from the debate
        
    Returns:
        list: Parsed research directions with name, assumption, and focus fields
    """
    directions = []
    
    # Look for FINAL CONSENSUS section
    if "FINAL CONSENSUS:" in conclusion_text:
        lines = conclusion_text.split("FINAL CONSENSUS:")[1].split('\n')
    else:
        lines = conclusion_text.split('\n')
    
    current_direction = None
    
    for line in lines:
        line = line.strip()
        
        # Look for direction headers
        if line.startswith('Direction ') and ':' in line:
            if current_direction:
                directions.append(current_direction)
            
            direction_name = line.split(':', 1)[1].strip()
            current_direction = {
                "name": direction_name,
                "assumption": "",  # Maps to core_focus for backward compatibility
                "focus": ""        # Maps to research_approach for backward compatibility
            }
        
        elif current_direction:
            # Support both old format (for backward compatibility) and new collaborative format
            if line.startswith('Core Assumption:'):
                current_direction["assumption"] = line.split(':', 1)[1].strip()
            elif line.startswith('Core Focus:'):
                current_direction["assumption"] = line.split(':', 1)[1].strip()  # Map to assumption field
            elif line.startswith('Focus:'):
                current_direction["focus"] = line.split(':', 1)[1].strip()
            elif line.startswith('Research Approach:'):
                current_direction["focus"] = line.split(':', 1)[1].strip()  # Map to focus field
    
    # Add the last direction
    if current_direction:
        directions.append(current_direction)
    
    return directions 