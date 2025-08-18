"""
Evolution Agent for CS Chapter Writing System

This agent improves chapters based on feedback:
- Addresses scientific accuracy issues
- Improves narrative quality
- Conducts additional research as needed
- Refines character authenticity
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

from deep_sci_fi.prompts import EVOLUTION_CHAPTER_PROMPT


class EvolutionAgent:
    """Agent that improves chapters based on reflection feedback"""
    
    def __init__(self, model_string: str = "anthropic:claude-opus-4-1-20250805"):
        self.model = init_chat_model(model_string, temperature=0.8)
        self.tools = [
            self._conduct_additional_research,
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
    async def _conduct_additional_research(self, research_query: str) -> str:
        """Conduct additional research to fill gaps using Deep Researcher"""
        try:
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
            
            # Use retry logic for deep_researcher call
            import anthropic
            
            for attempt in range(3):
                try:
                    research_result = await deep_researcher.ainvoke(
                        {"messages": [HumanMessage(content=research_query)]},
                        research_config
                    )
                    break  # Success, exit retry loop
                except anthropic.APIStatusError as e:
                    error_type = e.body.get("error", {}).get("type", "") if hasattr(e, 'body') else ""
                    if error_type in ["overloaded_error", "rate_limit_error"] and attempt < 2:
                        delay = 1.0 * (2 ** attempt) + random.uniform(0, 1)
                        print(f"  ⏳ Deep researcher API {error_type}, retrying in {delay:.1f}s (attempt {attempt + 1}/3)")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        raise
                except Exception as e:
                    error_msg = str(e).lower()
                    if any(keyword in error_msg for keyword in ["timeout", "connection", "network"]) and attempt < 2:
                        delay = 1.0 * (2 ** attempt) + random.uniform(0, 1)
                        print(f"  ⏳ Deep researcher network error, retrying in {delay:.1f}s (attempt {attempt + 1}/3)")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        raise
            
            # Extract research findings
            research_content = research_result.get("final_report", "")
            print(f"✅ Deep research completed for evolution: {research_query[:50]}...")
            return research_content
            
        except Exception as e:
            print(f"❌ Deep researcher failed for evolution '{research_query}': {e}")
            print(f"Deep researcher failure traceback:")
            print(traceback.format_exc())
            
            return f"""Evolution Research Error for: {research_query}

Error: {str(e)}

[Deep researcher integration failed. Manual research needed.]

Basic research outline:
- Scientific principles involved
- Current technological state  
- Future development possibilities
- Implications for chapter improvement"""
    
    async def improve_chapter(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Main entry point for chapter improvement"""
        current_chapter = state.get("current_chapter", "")
        chapter_evaluation = state.get("chapter_evaluation", "")
        research_cache = state.get("research_cache", {})
        
        # Use the proper prompt from prompts.py
        prompt_content = EVOLUTION_CHAPTER_PROMPT.format(
            current_chapter=current_chapter,
            chapter_evaluation=chapter_evaluation,
            research_cache=str(research_cache) if research_cache else "No research context available"
        )
        
        try:
            # Invoke the agent with the improvement prompt
            messages = [HumanMessage(content=prompt_content)]
            result = await self.agent.ainvoke({"messages": messages})
            
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
                        improved_chapter = "\n".join(text_parts)
                    elif isinstance(content, dict) and 'text' in content:
                        improved_chapter = content['text']
                    else:
                        improved_chapter = str(content)
                else:
                    improved_chapter = str(last_message)
            else:
                improved_chapter = "Chapter improvement failed - no response from agent"
            
        except Exception as e:
            improved_chapter = f"""Chapter Improvement Failed: {str(e)}

Original Chapter: {current_chapter}
Evaluation: {chapter_evaluation}

[Agent execution failed. Manual chapter improvement needed.]"""
        
        return {
            "current_chapter": improved_chapter,
            "research_cache": research_cache,  # Keep existing research
            "evolution_complete": True,
            "improvement_applied": True
        } 