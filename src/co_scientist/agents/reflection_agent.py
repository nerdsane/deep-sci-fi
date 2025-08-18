"""
Reflection Agent for CS Chapter Writing System

This agent evaluates chapter quality and identifies gaps:
- Assesses scientific accuracy
- Evaluates narrative quality
- Identifies research gaps or inconsistencies
"""

from typing import Dict, Any, List
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.prebuilt import create_react_agent
from langchain.chat_models import init_chat_model

from deep_sci_fi.prompts import REFLECTION_CHAPTER_PROMPT


class ReflectionAgent:
    """Agent that evaluates chapter quality and identifies improvement needs"""
    
    def __init__(self, model_string: str = "anthropic:claude-sonnet-4-20250514"):
        self.model = init_chat_model(model_string, temperature=0.6)
        self.tools = [
            self._evaluate_scientific_accuracy,
            self._evaluate_narrative_quality,
            self._identify_research_gaps,
            self._assess_character_authenticity,
        ]
        self.agent = create_react_agent(
            self.model,
            self.tools,
            prompt="""You are a reflection agent for scientifically grounded chapter writing.

Your role is to critically evaluate chapters and identify:
1. Scientific accuracy issues
2. Narrative quality problems  
3. Research gaps that need filling
4. Character authenticity concerns

Be thorough but constructive. Focus on specific, actionable feedback."""
        )
    
    @tool
    def _evaluate_scientific_accuracy(self, chapter_content: str, research_context: str) -> str:
        """Evaluate the scientific accuracy of the chapter"""
        raise NotImplementedError(f"Scientific accuracy evaluation tool not yet implemented")
    
    @tool
    def _evaluate_narrative_quality(self, chapter_content: str, story_goals: str) -> str:
        """Evaluate the narrative quality and story progression"""
        raise NotImplementedError(f"Narrative quality evaluation tool not yet implemented")
    
    @tool
    def _identify_research_gaps(self, chapter_content: str, available_research: str) -> str:
        """Identify areas that need additional research"""
        raise NotImplementedError(f"Research gap identification tool not yet implemented")
    
    @tool
    def _assess_character_authenticity(self, chapter_content: str, future_context: str) -> str:
        """Assess whether characters think and act authentically for their time period"""
        raise NotImplementedError(f"Character authenticity assessment tool not yet implemented")
    
    async def evaluate_chapter(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Main entry point for chapter evaluation"""
        current_chapter = state.get("current_chapter", "")
        chapter_analysis = state.get("chapter_analysis", "")
        research_cache = state.get("research_cache", {})
        light_future_context = state.get("light_future_context", "")
        
        # Invoke the agent to evaluate the chapter
        result = await self.agent.ainvoke({
            "messages": [
                HumanMessage(content=f"""Evaluate this chapter for quality and accuracy:

CHAPTER CONTENT: {current_chapter}

ORIGINAL REQUIREMENTS: {chapter_analysis}

AVAILABLE RESEARCH: {str(research_cache)}

FUTURE CONTEXT: {light_future_context}

Provide specific feedback on:
1. Scientific accuracy
2. Narrative quality
3. Research gaps
4. Character authenticity

Give actionable suggestions for improvement.""")
            ]
        })
        
        # Extract the evaluation from the result
        evaluation = result["messages"][-1].content if result["messages"] else "Evaluation failed"
        
        # Determine if the chapter needs improvement
        needs_improvement = "research gap" in evaluation.lower() or "inaccurate" in evaluation.lower() or "improvement needed" in evaluation.lower()
        
        return {
            "chapter_evaluation": evaluation,
            "needs_improvement": needs_improvement,
            "reflection_complete": True
        } 