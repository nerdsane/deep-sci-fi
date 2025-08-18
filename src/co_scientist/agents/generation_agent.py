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
            prompt="""You are a generation agent for scientifically grounded chapter writing.

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
        # Use the model to generate actual chapter content
        try:
            from deep_sci_fi.prompts import GENERATION_CHAPTER_PROMPT
            
            prompt_content = GENERATION_CHAPTER_PROMPT.format(
                chapter_analysis=chapter_goals,
                story_concept="Story concept from state",
                research_cache=research_context
            )
            
            # Generate chapter content using the model
            response = self.model.invoke([{"role": "user", "content": prompt_content}])
            
            if hasattr(response, 'content'):
                return str(response.content)
            else:
                return str(response)
                
        except Exception as e:
            # Fallback to basic content if model call fails
            return f"""# Chapter 1: Opening

[Chapter generation failed: {str(e)}]

Basic chapter structure based on:
Goals: {chapter_goals}
Research: {research_context}

This is a fallback chapter. Full model integration needed."""
    
    @tool
    def _conduct_research(self, research_query: str) -> str:
        """Conduct deep research on a specific scientific question"""
        # Check cache first
        if research_query in self.research_cache:
            return self.research_cache[research_query]
        
        # For now, use a synchronous research approach
        # TODO: Implement proper async deep researcher integration
        try:
            # Use the model directly for research instead of deep researcher
            research_prompt = f"""Conduct scientific research on this question: {research_query}

Provide:
1. Current scientific understanding
2. Relevant research findings
3. Future development possibilities
4. Implications for science fiction storytelling

Be specific and scientifically accurate."""

            response = self.model.invoke([{"role": "user", "content": research_prompt}])
            
            if hasattr(response, 'content'):
                content = response.content
                # Handle structured content
                if isinstance(content, list):
                    text_parts = []
                    for item in content:
                        if isinstance(item, dict) and 'text' in item:
                            text_parts.append(item['text'])
                        else:
                            text_parts.append(str(item))
                    research_result = "\n".join(text_parts)
                elif isinstance(content, dict) and 'text' in content:
                    research_result = content['text']
                else:
                    research_result = str(content)
            else:
                research_result = str(response)
                
        except Exception as e:
            # Fallback if deep researcher fails
            research_result = f"""Research Error for: {research_query}

Error: {str(e)}

[Deep researcher integration failed. Manual research needed.]

Basic research outline:
- Scientific principles involved
- Current technological state
- Future development possibilities
- Implications for story world"""
        
        # Cache the result
        self.research_cache[research_query] = research_result
        return research_result
    
    @tool
    def _integrate_research(self, research_findings: str, chapter_content: str) -> str:
        """Integrate research findings into chapter content"""
        # Basic implementation to prevent infinite loops
        return f"""{chapter_content}

--- RESEARCH INTEGRATION ---
{research_findings}

[Research integrated into chapter content. Full integration logic needed.]"""
    
    async def write_chapter(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Main entry point for chapter generation"""
        chapter_analysis = state.get("chapter_analysis", "")
        story_concept = state.get("selected_story_concept", "")
        research_cache = state.get("research_cache", {})
        target_year = state.get("target_year", 2084)
        human_condition = state.get("human_condition", "")
        
        # Update our cache with any existing research
        self.research_cache.update(research_cache)
        
        # Use the proper prompt from prompts.py
        from deep_sci_fi.prompts import GENERATION_CHAPTER_PROMPT
        
        generation_prompt = GENERATION_CHAPTER_PROMPT.format(
            chapter_analysis=chapter_analysis,
            story_concept=story_concept,
            research_cache=str(self.research_cache)
        )
        
        # Invoke the agent to write the chapter
        result = await self.agent.ainvoke({
            "messages": [HumanMessage(content=generation_prompt)]
        })
        
        # Extract the chapter content from the result
        if result["messages"]:
            last_message = result["messages"][-1]
            # Handle different content formats
            if hasattr(last_message, 'content'):
                content = last_message.content
                # Handle structured content (list of dicts with 'text' field)
                if isinstance(content, list):
                    # Extract text from structured content
                    text_parts = []
                    for item in content:
                        if isinstance(item, dict) and 'text' in item:
                            text_parts.append(item['text'])
                        else:
                            text_parts.append(str(item))
                    chapter_content = "\n".join(text_parts)
                elif isinstance(content, dict) and 'text' in content:
                    # Single structured content object
                    chapter_content = content['text']
                else:
                    chapter_content = str(content)
            else:
                chapter_content = str(last_message)
        else:
            chapter_content = "Chapter generation failed - no messages returned"
        
        return {
            "current_chapter": chapter_content,
            "research_cache": self.research_cache,
            "generation_complete": True
        } 