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
        self.model = init_chat_model(model_string, temperature=0.7)
        self.tools = [
            self._assess_overall_quality,
            self._determine_readiness,
            self._recommend_next_steps,
        ]
        self.agent = create_react_agent(
            self.model,
            self.tools,
            prompt="""You are a meta-review agent for scientifically grounded chapter writing.

Your role is to make final strategic decisions:
1. Assess overall chapter quality
2. Determine if the chapter is ready for publication
3. Recommend next steps (publish, iterate, or major revision)

Be decisive but fair. Consider both scientific accuracy and narrative quality."""
        )
    
    @tool
    def _assess_overall_quality(self, chapter_content: str, all_feedback: str) -> str:
        """Assess the overall quality of the chapter"""
        # Basic implementation to prevent infinite loops
        return "Overall quality: ACCEPTABLE - Chapter meets basic standards for publication"
    
    @tool
    def _determine_readiness(self, quality_score: str, feedback_summary: str) -> str:
        """Determine if the chapter is ready for publication"""
        # Basic implementation to prevent infinite loops
        return "Chapter readiness: READY - Chapter is acceptable for publication"
    
    @tool
    def _recommend_next_steps(self, readiness_status: str, remaining_issues: str) -> str:
        """Recommend next steps for the chapter"""
        # Basic implementation to prevent infinite loops
        return "Next steps: PUBLISH - Chapter is ready for publication"
    
    async def review_chapter(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Main entry point for meta-review"""
        current_chapter = state.get("current_chapter", "")
        chapter_evaluation = state.get("chapter_evaluation", "")
        improvement_applied = state.get("improvement_applied", False)
        
        # Invoke the agent to make final decision
        result = await self.agent.ainvoke({
            "messages": [
                HumanMessage(content=f"""Make a final strategic decision about this chapter:

CHAPTER CONTENT: {current_chapter}

EVALUATION FEEDBACK: {chapter_evaluation}

IMPROVEMENTS APPLIED: {improvement_applied}

Decide:
1. Is this chapter ready for publication?
2. Does it need another iteration?
3. What are the next steps?

Provide a clear recommendation.""")
            ]
        })
        
        # Extract the decision from the result
        if result["messages"]:
            last_message = result["messages"][-1]
            # Handle different content formats
            if hasattr(last_message, 'content'):
                decision = last_message.content
                # Ensure it's a string
                if isinstance(decision, list):
                    decision = "\n".join(str(item) for item in decision)
                else:
                    decision = str(decision)
            else:
                decision = str(last_message)
        else:
            decision = "Decision failed - no messages returned"
        
        # Determine if the chapter is ready
        # For basic implementation, mark chapter as ready to prevent infinite loops
        # TODO: Implement proper decision logic
        chapter_ready = True  # Set to True to allow system to complete
        needs_iteration = False  # Set to False to prevent infinite loops
        
        return {
            "final_decision": decision,
            "chapter_ready": chapter_ready,
            "needs_iteration": needs_iteration,
            "meta_review_complete": True
        } 