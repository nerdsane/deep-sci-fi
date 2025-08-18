"""
Meta-Analysis Agent for CS Chapter Writing System

This agent identifies what needs to be accomplished for chapter writing:
- Chapter goals and structure
- Scientific research requirements  
- World-building needs
"""

from typing import Dict, Any, List
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.prebuilt import create_react_agent
from langchain.chat_models import init_chat_model

from deep_sci_fi.prompts import META_ANALYSIS_CHAPTER_PROMPT


class MetaAnalysisAgent:
    """Agent that analyzes chapter requirements and identifies research needs"""
    
    def __init__(self, model_string: str = "anthropic:claude-sonnet-4-20250514"):
        self.model = init_chat_model(model_string, temperature=0.7)
        self.tools = [
            self._identify_chapter_goals,
            self._identify_research_needs,
            self._identify_world_building_needs,
        ]
        self.agent = create_react_agent(
            self.model,
            self.tools,
            prompt="""You are a meta-analysis agent for scientifically grounded chapter writing.

Your role is to analyze story requirements and identify:
1. What the chapter needs to accomplish narratively
2. What scientific research is required
3. What world-building elements need development

Be thorough but focused. Identify only what's essential for this specific chapter."""
        )
    
    @tool
    def _identify_chapter_goals(self, story_concept: str, chapter_position: str) -> str:
        """Identify what this chapter needs to accomplish narratively"""
        raise NotImplementedError(f"Chapter goals identification tool not yet implemented for position: {chapter_position}")
    
    @tool  
    def _identify_research_needs(self, story_concept: str, scientific_elements: str) -> str:
        """Identify what scientific research is needed for this chapter"""
        raise NotImplementedError(f"Research needs identification tool not yet implemented for elements: {scientific_elements}")
    
    @tool
    def _identify_world_building_needs(self, story_concept: str, setting_elements: str) -> str:
        """Identify what world-building development is needed"""
        raise NotImplementedError(f"World-building needs identification tool not yet implemented for: {setting_elements}")
    
    async def analyze_chapter_requirements(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Main entry point for meta-analysis"""
        story_concept = state.get("selected_story_concept", "")
        light_future_context = state.get("light_future_context", "")
        
        # Invoke the agent to analyze requirements
        result = await self.agent.ainvoke({
            "messages": [
                HumanMessage(content=f"""Analyze the chapter writing requirements for this story:

STORY CONCEPT: {story_concept}

FUTURE CONTEXT: {light_future_context}

Identify:
1. Chapter narrative goals
2. Required scientific research
3. World-building needs

Provide specific, actionable requirements.""")
            ]
        })
        
        # Extract the analysis from the result
        analysis = result["messages"][-1].content if result["messages"] else "Analysis failed"
        
        return {
            "chapter_analysis": analysis,
            "meta_analysis_complete": True
        } 