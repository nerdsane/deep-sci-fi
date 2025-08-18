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
        # Basic implementation to prevent infinite loops
        return f"""Chapter Goals for {chapter_position}:
- Establish character and setting
- Introduce central conflict
- Advance plot progression
- Explore human condition themes"""
    
    @tool  
    def _identify_research_needs(self, story_concept: str, scientific_elements: str) -> str:
        """Identify what scientific research is needed for this chapter"""
        # Basic implementation to prevent infinite loops
        return f"""Research Needs for {scientific_elements}:
- Scientific accuracy for core technology
- Character psychology research
- World-building consistency"""
    
    @tool
    def _identify_world_building_needs(self, story_concept: str, setting_elements: str) -> str:
        """Identify what world-building development is needed"""
        # Basic implementation to prevent infinite loops
        return f"""World-building Needs for {setting_elements}:
- Environmental details
- Social structure implications
- Technology integration"""
    
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
        if result["messages"]:
            last_message = result["messages"][-1]
            # Handle different content formats
            if hasattr(last_message, 'content'):
                analysis = last_message.content
                # Ensure it's a string
                if isinstance(analysis, list):
                    analysis = "\n".join(str(item) for item in analysis)
                else:
                    analysis = str(analysis)
            else:
                analysis = str(last_message)
        else:
            analysis = "Analysis failed - no messages returned"
        
        return {
            "chapter_analysis": analysis,
            "meta_analysis_complete": True
        } 