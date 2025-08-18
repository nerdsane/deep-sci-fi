"""
CS Chapter Writing Orchestrator

This orchestrates the CS agent-based chapter writing system:
- Coordinates all CS agents (meta-analysis, generation, reflection, evolution, meta-review)
- Manages the iterative writing and improvement process
- Handles state management and agent communication
"""

from typing import Dict, Any, Optional
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage

from co_scientist.agents.meta_analysis_agent import MetaAnalysisAgent
from co_scientist.agents.generation_agent import GenerationAgent
from co_scientist.agents.reflection_agent import ReflectionAgent
from co_scientist.agents.evolution_agent import EvolutionAgent
from co_scientist.agents.meta_review_agent import MetaReviewAgent


class CSChapterState(TypedDict):
    """State for CS Chapter Writing System - compatible with main AgentState"""
    # Input from main workflow (required)
    user_input: str
    target_year: int
    human_condition: str
    technology_context: str
    constraint: str
    tone: str
    setting: str
    light_future_context: str
    story_seed_options: list
    selected_story_concept: str
    story_selection_ready: bool
    output_dir: str
    starting_year: int
    
    # CS agent outputs (optional)
    chapter_analysis: Optional[str]
    current_chapter: Optional[str]
    research_cache: Optional[dict]
    chapter_evaluation: Optional[str]
    final_decision: Optional[str]
    
    # Control flags (optional)
    meta_analysis_complete: Optional[bool]
    generation_complete: Optional[bool]
    reflection_complete: Optional[bool]
    evolution_complete: Optional[bool]
    meta_review_complete: Optional[bool]
    needs_improvement: Optional[bool]
    chapter_ready: Optional[bool]
    needs_iteration: Optional[bool]
    improvement_applied: Optional[bool]
    
    # Iteration tracking (optional)
    iteration_count: Optional[int]
    max_iterations: Optional[int]


class CSChapterOrchestrator:
    """Orchestrates the CS agent-based chapter writing system"""
    
    def __init__(self):
        # Initialize all agents
        self.meta_analysis_agent = MetaAnalysisAgent()
        self.generation_agent = GenerationAgent()
        self.reflection_agent = ReflectionAgent()
        self.evolution_agent = EvolutionAgent()
        self.meta_review_agent = MetaReviewAgent()
        
        # Build the CS chapter writing graph
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the CS chapter writing workflow graph"""
        
        # Define agent node functions
        async def meta_analysis_node(state: CSChapterState) -> CSChapterState:
            """Meta-analysis agent node"""
            print("🔍 CS Meta-Analysis: Analyzing chapter requirements...")
            print(f"📊 Input state keys: {list(state.keys())}")
            
            try:
                result = await self.meta_analysis_agent.analyze_chapter_requirements(state)
                print(f"✅ Meta-analysis result: {result}")
                
                # Save meta-analysis output for observability
                if output_dir := state.get("output_dir"):
                    from deep_sci_fi.deep_sci_fi_writer import save_output
                    save_output(output_dir, "04a_cs_meta_analysis.md", result.get("chapter_analysis", ""))
                    print("💾 Meta-analysis saved to 04a_cs_meta_analysis.md")
                
                merged_state = {**state, **result}
                print(f"📊 Output state completion flags: meta_analysis_complete={merged_state.get('meta_analysis_complete')}")
                return merged_state
                
            except Exception as e:
                print(f"❌ Meta-analysis failed: {str(e)}")
                return {**state, "meta_analysis_complete": False, "chapter_analysis": f"Meta-analysis failed: {str(e)}"}
        
        async def generation_node(state: CSChapterState) -> CSChapterState:
            """Generation agent node"""
            print("✍️ CS Generation: Writing chapter with just-in-time research...")
            
            try:
                result = await self.generation_agent.write_chapter(state)
                print(f"✅ Generation result keys: {list(result.keys())}")
                
                # Save generation output for observability
                if output_dir := state.get("output_dir"):
                    from deep_sci_fi.deep_sci_fi_writer import save_output
                    save_output(output_dir, "04b_cs_generation.md", result.get("current_chapter", ""))
                    # Also save research cache updates
                    research_cache = result.get("research_cache", {})
                    if research_cache:
                        cache_content = "\n\n".join([f"## {query}\n{result}" for query, result in research_cache.items()])
                        save_output(output_dir, "04b_cs_research_cache.md", cache_content)
                    print("💾 Generation output saved to 04b_cs_generation.md")
                
                merged_state = {**state, **result}
                print(f"📊 Generation completion: {merged_state.get('generation_complete')}")
                return merged_state
                
            except Exception as e:
                print(f"❌ Generation failed: {str(e)}")
                return {**state, "generation_complete": False, "current_chapter": f"Generation failed: {str(e)}"}
        
        async def reflection_node(state: CSChapterState) -> CSChapterState:
            """Reflection agent node"""
            print("🤔 CS Reflection: Evaluating chapter quality...")
            
            try:
                result = await self.reflection_agent.evaluate_chapter(state)
                print(f"✅ Reflection result: needs_improvement={result.get('needs_improvement')}")
                
                # Save reflection output for observability
                if output_dir := state.get("output_dir"):
                    from deep_sci_fi.deep_sci_fi_writer import save_output
                    iteration = state.get("iteration_count", 0)
                    save_output(output_dir, f"04c_cs_reflection_iter{iteration}.md", result.get("chapter_evaluation", ""))
                    print(f"💾 Reflection saved to 04c_cs_reflection_iter{iteration}.md")
                
                merged_state = {**state, **result}
                print(f"📊 Reflection routing: needs_improvement={merged_state.get('needs_improvement')}")
                return merged_state
                
            except Exception as e:
                print(f"❌ Reflection failed: {str(e)}")
                return {**state, "reflection_complete": False, "needs_improvement": False}
        
        async def evolution_node(state: CSChapterState) -> CSChapterState:
            """Evolution agent node"""
            print("🔧 CS Evolution: Improving chapter based on feedback...")
            result = await self.evolution_agent.improve_chapter(state)
            # Increment iteration count
            iteration_count = state.get("iteration_count", 0) + 1
            
            # Save evolution output for observability
            if output_dir := state.get("output_dir"):
                from deep_sci_fi.deep_sci_fi_writer import save_output
                save_output(output_dir, f"04d_cs_evolution_iter{iteration_count}.md", result.get("current_chapter", ""))
                print(f"💾 Evolution output saved to 04d_cs_evolution_iter{iteration_count}.md")
            
            return {**state, **result, "iteration_count": iteration_count}
        
        async def meta_review_node(state: CSChapterState) -> CSChapterState:
            """Meta-review agent node"""
            print("⚖️ CS Meta-Review: Making final quality decision...")
            
            try:
                result = await self.meta_review_agent.review_chapter(state)
                print(f"✅ Meta-review result: chapter_ready={result.get('chapter_ready')}, needs_iteration={result.get('needs_iteration')}")
                
                # Save meta-review output for observability
                if output_dir := state.get("output_dir"):
                    from deep_sci_fi.deep_sci_fi_writer import save_output
                    iteration = state.get("iteration_count", 0)
                    save_output(output_dir, f"04e_cs_meta_review_iter{iteration}.md", result.get("final_decision", ""))
                    print(f"💾 Meta-review saved to 04e_cs_meta_review_iter{iteration}.md")
                
                merged_state = {**state, **result}
                print(f"📊 Meta-review routing: chapter_ready={merged_state.get('chapter_ready')}")
                return merged_state
                
            except Exception as e:
                print(f"❌ Meta-review failed: {str(e)}")
                return {**state, "meta_review_complete": False, "chapter_ready": True}  # Force completion on failure
        
        # Define routing functions
        def route_after_reflection(state: CSChapterState) -> str:
            """Route after reflection based on whether improvement is needed"""
            if state.get("needs_improvement", False):
                return "evolution"
            else:
                return "meta_review"
        
        def route_after_meta_review(state: CSChapterState) -> str:
            """Route after meta-review based on final decision"""
            if state.get("chapter_ready", False):
                return END
            elif state.get("needs_iteration", False):
                # Check if we've exceeded max iterations
                iteration_count = state.get("iteration_count", 0)
                max_iterations = state.get("max_iterations", 3)
                if iteration_count >= max_iterations:
                    print(f"⚠️ Max iterations ({max_iterations}) reached. Finalizing chapter.")
                    return END
                else:
                    return "reflection"  # Go back for another iteration
            else:
                return END
        
        # Build the graph
        workflow = StateGraph(CSChapterState)
        
        # Add nodes
        workflow.add_node("meta_analysis", meta_analysis_node)
        workflow.add_node("generation", generation_node)
        workflow.add_node("reflection", reflection_node)
        workflow.add_node("evolution", evolution_node)
        workflow.add_node("meta_review", meta_review_node)
        
        # Add edges
        workflow.add_edge(START, "meta_analysis")
        workflow.add_edge("meta_analysis", "generation")
        workflow.add_edge("generation", "reflection")
        
        # Conditional routing
        workflow.add_conditional_edges(
            "reflection",
            route_after_reflection,
            {"evolution": "evolution", "meta_review": "meta_review"}
        )
        workflow.add_edge("evolution", "meta_review")
        workflow.add_conditional_edges(
            "meta_review", 
            route_after_meta_review,
            {"reflection": "reflection", END: END}
        )
        
        return workflow.compile()
    
    def initialize_cs_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize CS-specific state variables in the main state"""
        
        # Add CS-specific state variables with defaults
        cs_additions = {
            # Initialize CS state
            "research_cache": state.get("research_cache", {}),
            "iteration_count": 0,
            "max_iterations": 3,
            
            # Initialize flags
            "meta_analysis_complete": False,
            "generation_complete": False,
            "reflection_complete": False,
            "evolution_complete": False,
            "meta_review_complete": False,
            "needs_improvement": False,
            "chapter_ready": False,
            "needs_iteration": False,
            "improvement_applied": False,
            
            # Initialize CS outputs
            "chapter_analysis": "",
            "chapter_evaluation": "",
            "final_decision": "",
        }
        
        # Merge with existing state
        return {**state, **cs_additions}


# Global instance for use by main workflow
cs_chapter_orchestrator = CSChapterOrchestrator() 