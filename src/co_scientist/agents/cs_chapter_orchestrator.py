"""
CS Chapter Writing Orchestrator

This orchestrates the CS agent-based chapter writing system:
- Coordinates all CS agents (meta-analysis, generation, reflection, evolution, meta-review)
- Manages the iterative writing and improvement process
- Handles state management and agent communication
"""

from typing import Dict, Any
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
    """State for CS Chapter Writing System"""
    # Input from main workflow
    selected_story_concept: str
    light_future_context: str
    output_dir: str
    
    # CS agent outputs
    chapter_analysis: str
    current_chapter: str
    research_cache: dict
    chapter_evaluation: str
    final_decision: str
    
    # Control flags
    meta_analysis_complete: bool
    generation_complete: bool
    reflection_complete: bool
    evolution_complete: bool
    meta_review_complete: bool
    needs_improvement: bool
    chapter_ready: bool
    needs_iteration: bool
    improvement_applied: bool
    
    # Iteration tracking
    iteration_count: int
    max_iterations: int


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
            result = await self.meta_analysis_agent.analyze_chapter_requirements(state)
            
            # Save meta-analysis output for observability
            if output_dir := state.get("output_dir"):
                from deep_sci_fi.deep_sci_fi_writer import save_output
                save_output(output_dir, "04a_cs_meta_analysis.md", result.get("chapter_analysis", ""))
                print("💾 Meta-analysis saved to 04a_cs_meta_analysis.md")
            
            return {**state, **result}
        
        async def generation_node(state: CSChapterState) -> CSChapterState:
            """Generation agent node"""
            print("✍️ CS Generation: Writing chapter with just-in-time research...")
            result = await self.generation_agent.write_chapter(state)
            
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
            
            return {**state, **result}
        
        async def reflection_node(state: CSChapterState) -> CSChapterState:
            """Reflection agent node"""
            print("🤔 CS Reflection: Evaluating chapter quality...")
            result = await self.reflection_agent.evaluate_chapter(state)
            
            # Save reflection output for observability
            if output_dir := state.get("output_dir"):
                from deep_sci_fi.deep_sci_fi_writer import save_output
                iteration = state.get("iteration_count", 0)
                save_output(output_dir, f"04c_cs_reflection_iter{iteration}.md", result.get("chapter_evaluation", ""))
                print(f"💾 Reflection saved to 04c_cs_reflection_iter{iteration}.md")
            
            return {**state, **result}
        
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
            result = await self.meta_review_agent.review_chapter(state)
            
            # Save meta-review output for observability
            if output_dir := state.get("output_dir"):
                from deep_sci_fi.deep_sci_fi_writer import save_output
                iteration = state.get("iteration_count", 0)
                save_output(output_dir, f"04e_cs_meta_review_iter{iteration}.md", result.get("final_decision", ""))
                print(f"💾 Meta-review saved to 04e_cs_meta_review_iter{iteration}.md")
            
            return {**state, **result}
        
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
    
    async def write_chapter(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Main entry point for CS chapter writing"""
        
        # Prepare CS chapter state
        cs_state = CSChapterState({
            # Input from main workflow
            "selected_story_concept": state.get("selected_story_concept", ""),
            "light_future_context": state.get("light_future_context", ""),
            "output_dir": state.get("output_dir", ""),
            
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
        })
        
        print("🚀 Starting CS Chapter Writing System...")
        
        # Run the CS chapter writing workflow
        final_state = None
        async for chunk in self.graph.astream(cs_state):
            final_state = chunk
            # Print progress
            if chunk:
                node_name = list(chunk.keys())[0] if chunk else "unknown"
                print(f"✅ CS Agent completed: {node_name}")
        
        if not final_state:
            raise RuntimeError("CS Chapter writing failed - no final state returned")
        
        # Save comprehensive CS process summary for observability
        if output_dir := cs_state.get("output_dir"):
            from deep_sci_fi.deep_sci_fi_writer import save_output
            
            summary = f"""# CS Agent Chapter Writing Process Summary

## Process Overview
- **Total Iterations**: {final_state.get('iteration_count', 0)}
- **Max Iterations**: {final_state.get('max_iterations', 3)}
- **Chapter Ready**: {final_state.get('chapter_ready', False)}
- **Final Status**: {final_state.get('final_decision', 'No decision recorded')}

## Agent Completion Status
- **Meta-Analysis**: {final_state.get('meta_analysis_complete', False)}
- **Generation**: {final_state.get('generation_complete', False)}
- **Reflection**: {final_state.get('reflection_complete', False)}
- **Evolution**: {final_state.get('evolution_complete', False)}
- **Meta-Review**: {final_state.get('meta_review_complete', False)}

## Research Conducted
{len(final_state.get('research_cache', {}))} research queries conducted during chapter writing.

## Iteration History
- **Needed Improvement**: {final_state.get('needs_improvement', False)}
- **Improvements Applied**: {final_state.get('improvement_applied', False)}
- **Iterations Needed**: {final_state.get('needs_iteration', False)}

## Output Files Generated
- 04a_cs_meta_analysis.md - Chapter requirements analysis
- 04b_cs_generation.md - Initial chapter generation
- 04b_cs_research_cache.md - Research conducted during writing
- 04c_cs_reflection_iter[N].md - Quality evaluations (per iteration)
- 04d_cs_evolution_iter[N].md - Chapter improvements (per iteration)  
- 04e_cs_meta_review_iter[N].md - Final decisions (per iteration)
- 04_cs_generated_chapter.md - Final chapter output
- 04_cs_final_decision.md - Final meta-review decision
"""
            save_output(output_dir, "04_cs_process_summary.md", summary)
            print("📊 CS process summary saved to 04_cs_process_summary.md")
        
        # Extract results for main workflow
        return {
            "current_chapter": final_state.get("current_chapter", ""),
            "research_cache": final_state.get("research_cache", {}),
            "chapter_ready": final_state.get("chapter_ready", False),
            "final_decision": final_state.get("final_decision", ""),
            "cs_chapter_complete": True
        }


# Global instance for use by main workflow
cs_chapter_orchestrator = CSChapterOrchestrator() 