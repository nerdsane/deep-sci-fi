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
    def _conduct_additional_research(self, research_query: str) -> str:
        """Conduct additional research to fill gaps"""
        try:
            # Use the model for research
            research_prompt = f"""Conduct focused research on: {research_query}

Provide specific, actionable research findings that can be used to improve chapter content."""

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
                    return "\n".join(text_parts)
                elif isinstance(content, dict) and 'text' in content:
                    return content['text']
                else:
                    return str(content)
            else:
                return str(response)
                
        except Exception as e:
            return f"Research failed for '{research_query}': {str(e)}"
    
    async def improve_chapter(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Main entry point for chapter improvement"""
        current_chapter = state.get("current_chapter", "")
        chapter_evaluation = state.get("chapter_evaluation", "")
        research_cache = state.get("research_cache", {})
        
        # Use the proper prompt from prompts.py
        from deep_sci_fi.prompts import EVOLUTION_CHAPTER_PROMPT
        
        evolution_prompt = EVOLUTION_CHAPTER_PROMPT.format(
            current_chapter=current_chapter,
            chapter_evaluation=chapter_evaluation,
            research_cache=str(research_cache)
        )
        
        # Invoke the agent to improve the chapter
        result = await self.agent.ainvoke({
            "messages": [HumanMessage(content=evolution_prompt)]
        })
        
        # Extract the improved chapter from the result
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
                    improved_chapter = "\n".join(text_parts)
                elif isinstance(content, dict) and 'text' in content:
                    # Single structured content object
                    improved_chapter = content['text']
                else:
                    improved_chapter = str(content)
            else:
                improved_chapter = str(last_message)
        else:
            improved_chapter = "Chapter improvement failed - no messages returned"
        
        return {
            "current_chapter": improved_chapter,
            "evolution_complete": True,
            "improvement_applied": True
        } 