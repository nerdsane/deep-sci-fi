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
from langchain_core.tools import tool, Tool
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langgraph.prebuilt import create_react_agent
from langchain.chat_models import init_chat_model
from open_deep_research.deep_researcher import deep_researcher, reset_deep_researcher_global_state

from deep_sci_fi.prompts import EVOLUTION_CHAPTER_PROMPT


class EvolutionAgent:
    """Agent that improves chapters based on reflection feedback"""
    
    def __init__(self, model_string: str = "anthropic:claude-opus-4-1-20250805"):
        self.model = init_chat_model(model_string, temperature=0.8)
        self.research_cache: Dict[str, str] = {}
        # Wrap tools to avoid passing `self` into tool args
        async def _conduct_additional_research_tool(research_query: str) -> str:
            return await self._conduct_additional_research_impl(research_query)
        
        def _conduct_additional_research_tool_sync(research_query: str) -> str:
            raise RuntimeError("_conduct_additional_research is async-only; coroutine path should be used")

        self.tools = [
            Tool.from_function(name="_conduct_additional_research", func=_conduct_additional_research_tool_sync, coroutine=_conduct_additional_research_tool, description="Conduct additional deep research for improvements"),
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
    
    async def _conduct_additional_research_impl(self, research_query: str) -> str:
        """Conduct additional research to fill gaps using Deep Researcher"""
        # Check local cache first
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
            raise RuntimeError(f"Deep researcher returned empty report for evolution: {research_query}")
            
        print(f"✅ Deep research completed for evolution: {research_query[:50]}...")
        # Cache and return
        self.research_cache[research_query] = research_content
        return research_content
    
    async def improve_chapter(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Main entry point for chapter improvement"""
        current_chapter = state.get("current_chapter", "")
        chapter_evaluation = state.get("chapter_evaluation", "")
        research_cache = state.get("research_cache", {})
        output_dir = state.get("output_dir")
        
        # Use the proper prompt from prompts.py
        prompt_content = EVOLUTION_CHAPTER_PROMPT.format(
            current_chapter=current_chapter,
            chapter_evaluation=chapter_evaluation,
            research_cache=str(research_cache) if research_cache else "No research context available"
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
                    print(f"⏳ Evolution API {error_type}, retrying in {delay:.1f}s (attempt {attempt + 1}/3)")
                    await asyncio.sleep(delay)
                    continue
                else:
                    print(f"❌ Evolution failed after {attempt + 1} attempts: {e}")
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
                    improved_chapter = "\n".join(text_parts)
                elif isinstance(content, dict) and 'text' in content:
                    improved_chapter = content['text']
                else:
                    improved_chapter = str(content)
            else:
                improved_chapter = str(last_message)
        else:
            raise RuntimeError("Evolution failed - no response from agent")

        # Build and save tool usage logs and merge any new research into shared cache
        try:
            if output_dir and result and "messages" in result:
                tool_logs: List[str] = []
                for message in result["messages"]:
                    tool_calls = getattr(message, "tool_calls", None)
                    if tool_calls:
                        for call in tool_calls:
                            name = getattr(call, "name", getattr(call, "tool", "unknown_tool"))
                            args = getattr(call, "args", {})
                            tool_logs.append(f"TOOL CALL -> {name}: {args}")
                    if isinstance(message, ToolMessage):
                        tool_name = getattr(message, "tool", getattr(message, "name", "unknown_tool"))
                        tool_logs.append(f"TOOL RESULT <- {tool_name}:\n{message.content}")
                if tool_logs:
                    from deep_sci_fi.deep_sci_fi_writer import save_output
                    save_output(output_dir, "04d_cs_tool_calls.md", "\n\n".join(tool_logs))
        except Exception as e:
            print(f"⚠️ Failed to save evolution tool logs: {e}")
        
        # Merge any new research captured by this agent (if any) into shared cache
        merged_cache = {**research_cache, **self.research_cache}
        return {
            "current_chapter": improved_chapter,
            "research_cache": merged_cache,
            "evolution_complete": True,
            "improvement_applied": True
        }