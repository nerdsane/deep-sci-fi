"""
Evolution Agent for CS Chapter Writing System

This agent improves chapters based on feedback:
- Addresses scientific accuracy issues
- Improves narrative quality
- Conducts additional research as needed
- Refines character authenticity
"""

from typing import Dict, Any, List
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.prebuilt import create_react_agent
from langchain.chat_models import init_chat_model

from deep_sci_fi.prompts import EVOLUTION_CHAPTER_PROMPT


class EvolutionAgent:
    """Agent that improves chapters based on reflection feedback"""
    
    def __init__(self, model_string: str = "anthropic:claude-opus-4-1-20250805"):
        self.model = init_chat_model(model_string, temperature=0.8)
        self.tools = [
            self._improve_scientific_accuracy,
            self._enhance_narrative_quality,
            self._conduct_additional_research,
            self._refine_character_authenticity,
        ]
        self.agent = create_react_agent(
            self.model,
            self.tools,
            prompt="""You are an evolution agent for scientifically grounded chapter writing.

Your role is to improve chapters based on feedback:
1. Fix scientific accuracy issues
2. Enhance narrative quality
3. Conduct additional research when needed
4. Improve character authenticity

Make targeted improvements while preserving the chapter's strengths."""
        )
    
    @tool
    def _improve_scientific_accuracy(self, chapter_content: str, accuracy_issues: str) -> str:
        """Fix scientific accuracy issues in the chapter"""
        # Basic implementation to prevent infinite loops
        return f"{chapter_content}\n\n[Scientific accuracy improvements applied - full implementation needed]"
    
    @tool
    def _enhance_narrative_quality(self, chapter_content: str, quality_issues: str) -> str:
        """Improve narrative quality and story flow"""
        # Basic implementation to prevent infinite loops
        return f"{chapter_content}\n\n[Narrative quality enhancements applied - full implementation needed]"
    
    @tool
    def _conduct_additional_research(self, research_query: str) -> str:
        """Conduct additional research to fill gaps"""
        # Basic implementation to prevent infinite loops
        return f"Additional research completed for: {research_query}\n[Placeholder research - full implementation needed]"
    
    @tool
    def _refine_character_authenticity(self, chapter_content: str, authenticity_issues: str) -> str:
        """Improve character authenticity for the time period"""
        # Basic implementation to prevent infinite loops
        return f"{chapter_content}\n\n[Character authenticity refinements applied - full implementation needed]"
    
    async def improve_chapter(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Main entry point for chapter improvement"""
        current_chapter = state.get("current_chapter", "")
        chapter_evaluation = state.get("chapter_evaluation", "")
        research_cache = state.get("research_cache", {})
        
        # Invoke the agent to improve the chapter
        result = await self.agent.ainvoke({
            "messages": [
                HumanMessage(content=f"""Improve this chapter based on the evaluation feedback:

CURRENT CHAPTER: {current_chapter}

EVALUATION FEEDBACK: {chapter_evaluation}

AVAILABLE RESEARCH: {str(research_cache)}

Make specific improvements to address the identified issues while preserving the chapter's strengths. If additional research is needed, conduct it first.""")
            ]
        })
        
        # Extract the improved chapter from the result
        if result["messages"]:
            last_message = result["messages"][-1]
            # Handle different content formats
            if hasattr(last_message, 'content'):
                improved_chapter = last_message.content
                # Ensure it's a string
                if isinstance(improved_chapter, list):
                    improved_chapter = "\n".join(str(item) for item in improved_chapter)
                else:
                    improved_chapter = str(improved_chapter)
            else:
                improved_chapter = str(last_message)
        else:
            improved_chapter = "Chapter improvement failed - no messages returned"
        
        return {
            "current_chapter": improved_chapter,
            "evolution_complete": True,
            "improvement_applied": True
        } 