"""
Generation Agent for CS Chapter Writing System

This agent writes chapter content and conducts research as needed:
- Writes chapter scenes and content
- Conducts just-in-time research when gaps are encountered
- Integrates research findings into the writing
"""

from typing import Dict, Any, List
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.prebuilt import create_react_agent
from langchain.chat_models import init_chat_model
from open_deep_research.deep_researcher import deep_researcher

from deep_sci_fi.prompts import GENERATION_CHAPTER_PROMPT


class GenerationAgent:
    """Agent that writes chapters and conducts just-in-time research"""
    
    def __init__(self, model_string: str = "anthropic:claude-opus-4-1-20250805"):
        self.model = init_chat_model(model_string, temperature=0.9)
        self.research_cache = {}
        self.tools = [
            self._write_chapter_content,
            self._conduct_research,
            self._integrate_research,
        ]
        self.agent = create_react_agent(
            self.model,
            self.tools,
            system_message="""You are a generation agent for scientifically grounded chapter writing.

Your role is to:
1. Write engaging chapter content
2. Identify when scientific research is needed
3. Conduct research using available tools
4. Integrate research findings naturally into the writing

Write compelling prose while maintaining scientific accuracy. When you encounter something that needs research, use your research tool immediately."""
        )
    
    @tool
    def _write_chapter_content(self, chapter_goals: str, research_context: str) -> str:
        """Write chapter content based on goals and available research"""
        # This would generate the actual chapter prose
        return f"Chapter content written incorporating: {research_context}"
    
    @tool
    def _conduct_research(self, research_query: str) -> str:
        """Conduct deep research on a specific scientific question"""
        # Check cache first
        if research_query in self.research_cache:
            return self.research_cache[research_query]
        
        # This would use the deep researcher tool
        # For now, return a placeholder
        research_result = f"Research conducted on: {research_query}"
        self.research_cache[research_query] = research_result
        return research_result
    
    @tool
    def _integrate_research(self, research_findings: str, chapter_content: str) -> str:
        """Integrate research findings into chapter content"""
        # This would blend research naturally into the prose
        return f"Integrated research into chapter: {research_findings[:100]}..."
    
    async def write_chapter(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Main entry point for chapter generation"""
        chapter_analysis = state.get("chapter_analysis", "")
        story_concept = state.get("selected_story_concept", "")
        research_cache = state.get("research_cache", {})
        
        # Update our cache with any existing research
        self.research_cache.update(research_cache)
        
        # Invoke the agent to write the chapter
        result = await self.agent.ainvoke({
            "messages": [
                HumanMessage(content=f"""Write a chapter based on these requirements:

CHAPTER ANALYSIS: {chapter_analysis}

STORY CONCEPT: {story_concept}

Write engaging, scientifically grounded prose. When you encounter scientific concepts that need research, use your research tool to get accurate information, then integrate it naturally into the writing.""")
            ]
        })
        
        # Extract the chapter content from the result
        chapter_content = result["messages"][-1].content if result["messages"] else "Chapter generation failed"
        
        return {
            "current_chapter": chapter_content,
            "research_cache": self.research_cache,
            "generation_complete": True
        } 