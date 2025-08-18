"""
Meta-Review Agent for CS Chapter Writing System

This agent makes final strategic decisions:
- Determines if chapter is ready for publication
- Decides if another iteration is needed
- Makes strategic choices about story direction
"""

from typing import Dict, Any, List
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.prebuilt import create_react_agent
from langchain.chat_models import init_chat_model

from deep_sci_fi.prompts import META_REVIEW_CHAPTER_PROMPT


class MetaReviewAgent:
    """Agent that makes final strategic decisions about chapter quality"""
    
    def __init__(self, model_string: str = "openai:o3-2025-04-16"):
        # O3 models only support temperature=1
        temperature = 1.0 if "o3" in model_string.lower() else 0.7
        self.model = init_chat_model(model_string, temperature=temperature)
        # Meta-review uses LLM reasoning directly for strategic decisions
        self.agent = create_react_agent(
            self.model,
            [],  # No tools needed for decision making
            prompt="""You are a meta-review agent for scientifically grounded chapter writing.

Your role is to make final strategic decisions:
1. Assess overall chapter quality
2. Determine if the chapter is ready for publication
3. Recommend next steps (publish, iterate, or major revision)

Be decisive but fair. Consider both scientific accuracy and narrative quality."""
        )
    

    
    async def review_chapter(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Main entry point for meta-review"""
        current_chapter = state.get("current_chapter", "")
        chapter_evaluation = state.get("chapter_evaluation", "")
        improvement_applied = state.get("improvement_applied", False)
        iteration_count = state.get("iteration_count", 0)
        max_iterations = state.get("max_iterations", 3)
        
        # Use the proper prompt from prompts.py
        from deep_sci_fi.prompts import META_REVIEW_CHAPTER_PROMPT
        
        review_prompt = META_REVIEW_CHAPTER_PROMPT.format(
            current_chapter=current_chapter,
            chapter_evaluation=chapter_evaluation,
            improvement_applied=improvement_applied
        )
        
        # Invoke the agent to make final decision
        result = await self.agent.ainvoke({
            "messages": [HumanMessage(content=review_prompt)]
        })
        
        # Extract the decision from the result
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
                    decision = "\n".join(text_parts)
                elif isinstance(content, dict) and 'text' in content:
                    # Single structured content object
                    decision = content['text']
                else:
                    decision = str(content)
            else:
                decision = str(last_message)
        else:
            decision = "Decision failed - no messages returned"
        
        # Intelligently determine next steps based on decision and iteration count
        chapter_ready, needs_iteration = self._make_strategic_decision(
            decision, current_chapter, iteration_count, max_iterations
        )
        
        return {
            "final_decision": decision,
            "chapter_ready": chapter_ready,
            "needs_iteration": needs_iteration,
            "meta_review_complete": True
        }
    
    def _make_strategic_decision(self, decision: str, chapter_content: str, iteration_count: int, max_iterations: int) -> tuple[bool, bool]:
        """Make intelligent strategic decision about chapter readiness"""
        
        # Force completion if we've reached max iterations
        if iteration_count >= max_iterations:
            return True, False  # chapter_ready=True, needs_iteration=False
        
        # Check for explicit readiness indicators in the decision
        ready_indicators = ["ready", "publish", "complete", "acceptable", "good quality"]
        iteration_indicators = ["improve", "revise", "needs work", "another iteration", "not ready"]
        
        decision_lower = decision.lower()
        
        # If decision explicitly says ready, mark as ready
        if any(indicator in decision_lower for indicator in ready_indicators):
            return True, False
        
        # If decision explicitly says needs iteration, and we haven't hit max
        if any(indicator in decision_lower for indicator in iteration_indicators):
            if iteration_count < max_iterations:
                return False, True
            else:
                return True, False  # Force completion at max iterations
        
        # Default: if chapter has substantial content, consider it ready
        if len(chapter_content.strip()) > 1000:  # Substantial content
            return True, False
        else:
            # Short content, needs improvement if under max iterations
            if iteration_count < max_iterations:
                return False, True
            else:
                return True, False 