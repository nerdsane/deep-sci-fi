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
        # Meta-analysis doesn't need tools - it uses LLM reasoning directly
        self.agent = create_react_agent(
            self.model,
            [],  # No tools needed for analysis
            prompt="""You are a meta-analysis agent for scientifically grounded chapter writing.

Your role is to analyze story requirements and identify:
1. What the chapter needs to accomplish narratively
2. What scientific research is required
3. What world-building elements need development

Be thorough but focused. Identify only what's essential for this specific chapter."""
        )
    

    
    async def analyze_chapter_requirements(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Main entry point for meta-analysis"""
        story_concept = state.get("selected_story_concept", "")
        light_future_context = state.get("light_future_context", "")
        target_year = state.get("target_year", 2084)
        human_condition = state.get("human_condition", "")
        
        # Use the prompt from prompts.py for consistency
        from deep_sci_fi.prompts import META_ANALYSIS_CHAPTER_PROMPT
        
        analysis_prompt = META_ANALYSIS_CHAPTER_PROMPT.format(
            story_concept=story_concept,
            light_future_context=light_future_context,
            chapter_position="Chapter 1 (Opening)"
        )
        
        # Invoke the agent with the proper prompt
        result = await self.agent.ainvoke({
            "messages": [HumanMessage(content=analysis_prompt)]
        })
        
        # Extract the analysis from the result
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
                    analysis = "\n".join(text_parts)
                elif isinstance(content, dict) and 'text' in content:
                    # Single structured content object
                    analysis = content['text']
                else:
                    analysis = str(content)
            else:
                analysis = str(last_message)
        else:
            analysis = "Analysis failed - no messages returned"
        
        return {
            "chapter_analysis": analysis,
            "meta_analysis_complete": True
        } 