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
        # Reflection uses LLM reasoning directly for evaluation
        self.agent = create_react_agent(
            self.model,
            [],  # No tools needed for evaluation
            prompt="""You are a reflection agent for scientifically grounded chapter writing.

Your role is to critically evaluate chapters and identify:
1. Scientific accuracy issues
2. Narrative quality problems  
3. Research gaps that need filling
4. Character authenticity concerns

Be thorough but constructive. Focus on specific, actionable feedback."""
        )
    

    
    async def evaluate_chapter(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Main entry point for chapter evaluation"""
        current_chapter = state.get("current_chapter", "")
        chapter_analysis = state.get("chapter_analysis", "")
        research_cache = state.get("research_cache", {})
        light_future_context = state.get("light_future_context", "")
        
        # Use the proper prompt from prompts.py
        from deep_sci_fi.prompts import REFLECTION_CHAPTER_PROMPT
        
        reflection_prompt = REFLECTION_CHAPTER_PROMPT.format(
            chapter_content=current_chapter,
            chapter_analysis=chapter_analysis,
            light_future_context=light_future_context
        )
        
        # Invoke the agent with visible retry logic for API overloads
        import anthropic
        import asyncio
        import random
        
        for attempt in range(3):  # 3 retry attempts
            try:
                result = await self.agent.ainvoke({
                    "messages": [HumanMessage(content=reflection_prompt)]
                })
                break  # Success, exit retry loop
            except anthropic.APIStatusError as e:
                error_type = e.body.get("error", {}).get("type", "") if hasattr(e, 'body') else ""
                if error_type in ["overloaded_error", "rate_limit_error"] and attempt < 2:
                    delay = 2.0 * (2 ** attempt) + random.uniform(0, 1)
                    print(f"⏳ Reflection API {error_type}, retrying in {delay:.1f}s (attempt {attempt + 1}/3)")
                    await asyncio.sleep(delay)
                    continue
                else:
                    print(f"❌ Reflection failed after {attempt + 1} attempts: {e}")
                    raise  # Re-raise the error after all retries exhausted
        
        # Extract the evaluation from the result
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
                    evaluation = "\n".join(text_parts)
                elif isinstance(content, dict) and 'text' in content:
                    # Single structured content object
                    evaluation = content['text']
                else:
                    evaluation = str(content)
            else:
                evaluation = str(last_message)
        else:
            evaluation = "Evaluation failed - no messages returned"
        
        # Intelligently determine if the chapter needs improvement
        needs_improvement = self._assess_improvement_needs(evaluation, current_chapter)
        
        return {
            "chapter_evaluation": evaluation,
            "needs_improvement": needs_improvement,
            "reflection_complete": True
        }
    
    def _assess_improvement_needs(self, evaluation: str, chapter_content: str) -> bool:
        """Intelligently assess if chapter needs improvement based on evaluation"""
        
        # Check for obvious quality issues
        quality_indicators = [
            "needs improvement", "poor quality", "significant issues",
            "major problems", "inadequate", "insufficient", "unclear",
            "confusing", "inconsistent", "unrealistic", "implausible"
        ]
        
        improvement_needed = any(indicator in evaluation.lower() for indicator in quality_indicators)
        
        # Also check chapter length - if too short, needs improvement
        if len(chapter_content.strip()) < 500:  # Very short chapter
            improvement_needed = True
        
        # Check for placeholder content that indicates incomplete generation
        if "[placeholder" in chapter_content.lower() or "todo:" in chapter_content.lower():
            improvement_needed = True
        
        return improvement_needed 