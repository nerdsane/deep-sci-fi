"""
Generation Agent for CS Chapter Writing System

This agent writes chapter content and conducts research as needed:
- Writes chapter scenes and content
- Conducts just-in-time research when gaps are encountered
- Integrates research findings into the writing
"""

import asyncio
import random
import traceback
from typing import Dict, Any, List
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.prebuilt import create_react_agent
from langchain.chat_models import init_chat_model
from open_deep_research.deep_researcher import deep_researcher, reset_deep_researcher_global_state

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
        """Write chapter content based on goals and research context"""
        # Use the proper prompt from prompts.py - let failures bubble up visibly
        prompt_content = GENERATION_CHAPTER_PROMPT.format(
            chapter_analysis=chapter_goals,
            story_concept="Story concept from state",
            research_cache=research_context
        )
        
        response = self.model.invoke([{"role": "user", "content": prompt_content}])
        
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
                return "\n".join(text_parts)
            elif isinstance(content, dict) and 'text' in content:
                return content['text']
            else:
                return str(content)
        else:
            return str(response)
    
    @tool
    async def _conduct_research(self, research_query: str) -> str:
        """Conduct deep research on a specific scientific question using Deep Researcher"""
        # Check cache first
        if research_query in self.research_cache:
            return self.research_cache[research_query]
        
        # Reset deep_researcher for fresh research context
        reset_deep_researcher_global_state()
        
        # Configure deep researcher
        research_config = {
            "configurable": {
                "research_model": "anthropic:claude-sonnet-4-20250514",
                "research_model_max_tokens": 8000,
                "summarization_model": "anthropic:claude-sonnet-4-20250514", 
                "compression_model": "anthropic:claude-sonnet-4-20250514",
                "compression_model_max_tokens": 8000,
                "final_report_model": "anthropic:claude-sonnet-4-20250514",
                "final_report_model_max_tokens": 8000,
                "allow_clarification": False,
                "search_api": "tavily"
            }
        }
        
        # Call deep_researcher directly - let API failures bubble up visibly
        research_result = await deep_researcher.ainvoke(
            {"messages": [HumanMessage(content=research_query)]},
            research_config
        )
        
        # Extract research findings
        research_content = research_result.get("final_report", "")
        if not research_content.strip():
            raise RuntimeError(f"Deep researcher returned empty report for: {research_query}")
            
        print(f"✅ Deep research completed for: {research_query[:50]}...")
        
        # Cache the result
        self.research_cache[research_query] = research_content
        return research_content
    
    @tool
    def _integrate_research(self, chapter_content: str, research_findings: str) -> str:
        """Integrate research findings into chapter content"""
        integration_prompt = f"""Integrate these research findings into the chapter content naturally and seamlessly:

CHAPTER CONTENT:
{chapter_content}

RESEARCH FINDINGS:
{research_findings}

Instructions:
1. Weave research findings naturally into the narrative
2. Maintain story flow and character voice
3. Ensure scientific accuracy
4. Don't make the research feel like exposition dumps
5. Use research to enhance world-building and authenticity

Return the improved chapter content."""

        response = self.model.invoke([{"role": "user", "content": integration_prompt}])
        
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
                return "\n".join(text_parts)
            elif isinstance(content, dict) and 'text' in content:
                return content['text']
            else:
                return str(content)
        else:
            return str(response)
    
    async def write_chapter(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Main entry point for chapter writing with research"""
        selected_story_concept = state.get("selected_story_concept", "")
        chapter_analysis = state.get("chapter_analysis", "")
        research_cache = state.get("research_cache", {})
        
        # Merge any existing research cache
        self.research_cache.update(research_cache)
        
        # Use the proper prompt from prompts.py
        prompt_content = GENERATION_CHAPTER_PROMPT.format(
            story_concept=selected_story_concept,
            chapter_analysis=chapter_analysis,
            research_cache=str(self.research_cache) if self.research_cache else "No previous research available"
        )
        
        # Invoke the agent with visible retry logic for API overloads
        import anthropic
        import asyncio
        import random
        
        messages = [HumanMessage(content=prompt_content)]
        
        for attempt in range(3):  # 3 retry attempts
            try:
                result = await self.agent.ainvoke({"messages": messages})
                break  # Success, exit retry loop
            except anthropic.APIStatusError as e:
                error_type = e.body.get("error", {}).get("type", "") if hasattr(e, 'body') else ""
                if error_type in ["overloaded_error", "rate_limit_error"] and attempt < 2:
                    delay = 2.0 * (2 ** attempt) + random.uniform(0, 1)
                    print(f"⏳ Generation API {error_type}, retrying in {delay:.1f}s (attempt {attempt + 1}/3)")
                    await asyncio.sleep(delay)
                    continue
                else:
                    print(f"❌ Generation failed after {attempt + 1} attempts: {e}")
                    raise  # Re-raise the error after all retries exhausted
        
        # Extract content from agent response
        if result and "messages" in result:
            last_message = result["messages"][-1]
            if hasattr(last_message, 'content'):
                content = last_message.content
                # Handle structured content
                if isinstance(content, list):
                    text_parts = []
                    for item in content:
                        if isinstance(item, dict) and 'text' in item:
                            text_parts.append(item['text'])
                        else:
                            text_parts.append(str(item))
                    chapter_content = "\n".join(text_parts)
                elif isinstance(content, dict) and 'text' in content:
                    chapter_content = content['text']
                else:
                    chapter_content = str(content)
            else:
                chapter_content = str(last_message)
        else:
            raise RuntimeError("Chapter generation failed - no response from agent")
        
        return {
            "current_chapter": chapter_content,
            "research_cache": self.research_cache,
            "generation_complete": True
        } 