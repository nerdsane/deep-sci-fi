Position Paper: Trajectories as a Foundation for Continual Learning Agents
Sesh Nalla | Dec 31, 2025 | Exploring could this be a Agentic AI Foundations
Abstract
This position paper argues that structured decision traces—trajectories—represent a missing primitive in the emerging agent ecosystem. I position trajectories alongside existing conventions (Skills, AGENTS.md, MCP) and articulate why they're the critical substrate for continual learning. Trajectories enable four capabilities: display (frontend rendering), context learning (retrieval), reinforcement learning (training), and simulation (counterfactual reasoning). Beyond passive data capture, trajectories function as "optimization statistics"—enabling dynamic improvement of the entire agent stack, analogous to how database query optimizers use statistics to improve execution plans. I examine industry approaches, connect to Sutton's recent work on continual learning and world models, and confront the hard questions: why this might fail and what would change my mind.
1. The Core Thesis
Agents that cannot learn from their own experience are fundamentally limited.

Today's agents execute tasks, produce outputs, and forget. The next invocation starts fresh. Any learning happens through:

Expensive retraining (months, millions of dollars)
Manual prompt engineering (doesn't scale)
Static retrieval (documents, not decisions)

I believe there's a better path: capture agent decision traces (trajectories) in a format that enables both inference-time learning and post-training improvement.

Others are building toward this insight. Yet no one has proposed an open, portable standard—the kind of interoperability that transformed observability when OpenTelemetry emerged. I think that's a gap worth addressing, and I want to make the case for why.
2. What I Mean by "Trajectories"
A trajectory is a complete record of an agent's execution: observations, reasoning, actions, results, and outcomes. Think of it as a structured trace—similar to distributed tracing spans—that preserves decision dynamics with the semantic richness needed for learning.

The key distinction from existing formats:

Format
Captures
Optimized For
Logs
Events, errors
Debugging
OpenTelemetry
Spans, timing
Through LangFuse, LogFire (Captures LLM calls, prompts, etc)
Performance monitoring, Debugging
LangSmith
LLM calls, prompts
Observability
Trajectories
Decisions, reasoning, outcomes
Learning


3. Where Trajectories Fit in the Agent Ecosystem
An agent ecosystem is emerging with several complementary primitives. I think trajectories complete this picture—but I want to be precise about how.
3.1 The Emerging Stack
Primitive
What It Defines
Nature
Example
Skills
What agents CAN do
Static capabilities
read_file, search_web, run_sql
AGENTS.md
How agents SHOULD behave
Static instructions
"Always ask before deleting files"
MCP
How agents GET context
Dynamic retrieval
Query a database, fetch docs
Trajectories
What agents DID do
Dynamic evidence
"Resolved incident X by doing Y, Z"

3.2 Why Trajectories Are Different
Skills define the action space. They're reusable, composable, and static. But skills don't tell you when to use them or why one sequence works better than another. Trajectories provide that context—they're the evidence of skill usage in practice.

AGENTS.md provides instructions and persona. It's valuable for alignment but inherently limited: you can't anticipate every situation. Trajectories complement AGENTS.md by showing what actually worked. Over time, patterns from trajectories could even inform updates to AGENTS.md—closing the loop from execution to instruction.

MCP is a protocol for context retrieval. It answers "how do I get relevant information to the agent?" Trajectories are a type of content that MCP could serve. In fact, I think trajectory retrieval via MCP is a natural integration: query for similar past decisions, inject them as context. MCP provides the transport; trajectories provide the content.
3.3 The Relationships
                    ┌─────────────┐
                    │  AGENTS.md   │ ◄─── could be updated based on
                    │ (instructions)│     trajectory patterns
                    └──────┬──────┘
                           │ guides
                           ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Skills    │────►│    Agent    │◄────│     MCP     │
│ (capabilities)│     │ (execution) │     │  (context)  │
└─────────────┘     └──────┬──────┘     └──────▲──────┘
                           │                    │
                           │ produces           │ serves
                           ▼                    │
                    ┌─────────────┐─────────────┘
                    │ Trajectories │
                    │  (evidence)  │
                    └─────────────┘
3.4 What This Means for the Proposal
I'm not proposing trajectories as a replacement for any of these primitives. I'm proposing they complete the picture:

Skills + Trajectories: Skills define what's possible; trajectories show what actually worked
AGENTS.md + Trajectories: Instructions define intent; trajectories provide evidence for refinement
MCP + Trajectories: MCP retrieves context; trajectories are a high-value context type for learning

The design implication: the trajectory format should be compatible with MCP retrieval patterns and should reference skills by name when actions invoke them.
4. The Continual Learning Funnel
I believe trajectories matter because they enable a progression I call the continual learning funnel:

┌─────────────────────────────────────────────────────────────┐
│                    AGENT EXECUTION                          │
│         (Generates trajectories as byproduct)               │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│               CONTEXT LEARNING (Inference-time)             │
│    • Retrieve similar trajectories as few-shot examples     │
│    • No model changes, immediate benefit                    │
│    • Low investment, bounded returns                        │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│            REINFORCEMENT LEARNING (Post-training)           │
│    • Fine-tune on curated trajectory corpus                 │
│    • Credit assignment across steps                         │
│    • High investment, compounding returns                   │
└─────────────────────────────────────────────────────────────┘
Why This Funnel Matters
Stage 1 is free—agents already execute tasks. The question is whether we capture that execution in a useful format.

Stage 2 (context learning) is the immediate payoff. Retrieve relevant past trajectories, include them as examples, and the agent performs better. This is RAG for decisions. No training required. I believe this alone justifies trajectory capture, even if RL never happens.

Stage 3 (reinforcement learning) is the compounding payoff. Once you have enough high-quality trajectories, you can fine-tune. The agent improves permanently, produces better trajectories, which feed the next round.

The key insight: the same trajectory format serves both stages. Capture once, benefit twice. Without a unified format, organizations must choose—build for retrieval or build for training. That's a false choice.
4.1 The Third Capability: Simulation and Counterfactuals
The funnel describes learning from what happened. Trajectories also enable reasoning about what might happen—simulation and counterfactual analysis.

┌─────────────────────────────────────────────────────────────┐
│                    TRAJECTORY CORPUS                         │
└───────┬─────────────────────┬─────────────────────┬─────────┘
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐   ┌─────────────────┐   ┌─────────────────┐
│    Context    │   │   Simulation    │   │       RL        │
│   Learning    │   │ & Counterfactual│   │    Training     │
│  (retrieval)  │   │   (prediction)  │   │   (fine-tune)   │
└───────────────┘   └─────────────────┘   └─────────────────┘

Simulation: Given a current state and proposed action, predict likely outcomes based on similar trajectories. This is the query optimizer's cost estimation applied to agent decisions—estimate the consequence before committing.

Counterfactual analysis: Given a completed trajectory, ask "what if the agent had chosen differently at step N?" By finding similar decision points in the corpus, you can estimate alternative outcomes. This enables:

Planning: Simulate multiple action branches, select the path with highest predicted success
Debugging: Understand why an agent failed by exploring what alternatives existed
Training signal: Generate synthetic negative examples ("this would have failed") without actual failures
4.2 World Model Derivation (Speculative)
I want to be upfront: this is the most speculative part of the proposal. The hypothesis is that accumulated trajectories enable emergent world models—predictive structures that generalize beyond retrieved examples.

How this might work:

Graph induction: Extract entities from observations/actions as nodes; decision sequences as directed edges. The corpus becomes a traversable graph of "situations → actions → outcomes."

Structural embeddings: Apply walk-based algorithms to produce vectors capturing decision patterns. Similar situations cluster; successful action sequences become identifiable paths.

Simulation layer: Train or index a lightweight model to predict next states given hypothetical actions. This could be as simple as nearest-neighbor over embeddings, or as complex as a learned transition model.

The analogy to trace analysis: This resembles how APM systems build service dependency maps from spans—structure emerges from accumulated traces without upfront schema design. The difference is that trajectory graphs encode decision dynamics, not just call graphs.

Why I'm uncertain: World model derivation from unstructured trajectories is an open research problem. Sutton's Oak architecture proposes specific mechanisms (FC-STOMP progression); I'm proposing a data format, not an algorithm. Whether useful world models emerge from trajectory corpora—and at what scale—requires empirical validation.

Why I include it anyway: Simulation is qualitatively different from retrieval or training. If trajectories only enabled context learning and RL, they'd still be valuable. If they also enable simulation, they become transformative—agents could reason about hypotheticals before acting, similar to how humans plan by imagining consequences.

4.3 The Four Use Cases
A unified trajectory format should serve four distinct purposes. Each has slightly different data requirements:

Use Case
Primary Need
Key Fields
Display
Render conversation history
Content, visibility flags, rich types
Context Learning
Retrieve similar examples
Embeddings, entities, outcome
Simulation
Predict counterfactuals
Full context, entities, history
RL Training
Fine-tune on rewards
Rewards, credit assignment, actions


Display needs visibility controls (send_to_user, persist) and rich content types (widgets, dashboards, structured responses). This is often overlooked in ML-focused formats.

Context Learning needs searchable structure: embeddings over observations, tagged entities, and outcome signals to filter for successful examples.

Simulation needs the full execution context: what the agent knew (observations, entities), what options existed (available tools), and what happened (actions, results). This enables "what if" reasoning.

RL Training needs reward signals at both step and trajectory level, clean action/result pairs for credit assignment, and exportability to training infrastructure.

A single format can serve all four if designed with these requirements in mind. The alternative—separate representations per use case—leads to conversion function proliferation and inevitable drift.

5. Trajectories as Optimization Statistics
Here's where I want to push beyond what I've seen articulated elsewhere.

The learning funnel describes how trajectories improve the agent. Trajectories could also improve the ecosystem primitives themselves—AGENTS.md, Skills, and MCP tool discovery. This closes the feedback loop on the entire agent stack, turning telemetry from passive observation into active system improvement.
5.1 The Database Query Optimizer Analogy
Consider how database query optimizers work:

Statistics collection: The database tracks table sizes, column distributions, index selectivity
Plan generation: When a query arrives, the optimizer generates candidate execution plans
Cost estimation: Using collected statistics, it estimates the cost of each plan
Plan selection: It chooses the lowest-cost plan

The key connection I’m making: the optimizer learns from data patterns to make better execution decisions. Over time, it accumulates statistics that inform increasingly sophisticated plan selection.

I think agent systems need a similar pattern:

Database Optimizer
Agent System
Table statistics
Trajectory corpus
Query plan
Tool selection sequence
Cost estimation
Utility prediction
Plan selection
Action choice


5.2 Dynamic AGENTS.md Evolution
AGENTS.md files are static. You write instructions once; the agent follows them forever. But what if instructions could evolve based on what actually works?

Recent work supports this idea. The SCOPE framework ("Self-evolving Context Optimization via Prompt Evolution") synthesizes guidelines from execution traces to automatically evolve agent prompts. Their "Dual-Stream" approach balances tactical fixes (resolving immediate errors) with strategic principles (long-term improvements).

With trajectories, you could:

Identify instruction gaps: Trajectories where agents struggled despite following AGENTS.md reveal missing guidance
Validate instructions: Instructions that correlate with successful trajectories are worth keeping; others may need revision
Generate candidate updates: LLMs can propose AGENTS.md patches based on trajectory patterns (the Promptomatix and EvoPrompt approaches)
A/B test changes: Deploy instruction variants, measure trajectory outcomes, converge on what works

This isn't speculative—it's prompt optimization (like DSPy, GEPA, etc) applied to agent instructions, with trajectories as the feedback signal.
5.3 Skills Discovery and Deprecation
Skills are typically hand-authored. But trajectories reveal actual usage patterns:

Skill gaps: Recurring trajectory patterns where agents improvise (multiple tool calls to accomplish what should be one skill) suggest missing abstractions
Skill sequences: Trajectories capture which skills are commonly used together—candidates for composite skills
Underused skills: Skills that rarely appear in successful trajectories may be poorly designed or redundant
Failure patterns: Skills that frequently appear in failed trajectories need investigation

This is collaborative filtering applied to tool selection: "Agents that succeeded in similar situations used these skills in this order."
5.4 MCP Tool Discovery Optimization
The MCP Registry now has ~2000 servers. Finding the right tool is increasingly a search problem—reminiscent of service discovery (dns) challenges in microservices architectures. Current approaches use semantic matching, fuzzy search, keyword search, etc on tool descriptions, which works for simple cases. Trajectories can enable something richer: behavioral matching based on historical success patterns (match the current situation to situations where tools succeeded)

The parallel to query optimization: A SQL optimizer doesn't try every possible join order—it uses statistics to prune the search space. Similarly, trajectory-informed tool discovery could:

Predict which tools are likely useful before calling them
Rank tools by historical success rate in similar contexts
Suggest tool sequences based on what worked before

This evolves MCP toward active recommendation: "here are tools that worked in situations like yours, ranked by historical success rate."
5.5 The Unified View
All three optimizations share a pattern:

Primitive
Current State
Trajectory-Informed
AGENTS.md
Static instructions
Evolving guidelines
Skills
Hand-authored tools
Usage-informed catalog
MCP discovery
Semantic search
Behavioral recommendation


6. Intellectual Context: Sutton on Continual Learning
I want to acknowledge relevant intellectual context while being precise about where this proposal aligns and diverges.

Rich Sutton's NeurIPS 2025 talk, "The Oak Architecture: A Vision of SuperIntelligence from Experience", argued that AI has "lost its way" and needs to return to first principles:

Agents that learn continually
World models built from runtime experience
Meta-learning how to generalize

His Oak architecture proposes a specific solution: model-based RL with continually-learning components, meta-learned parameters, and abstractions built through a progression he calls FC-STOMP.
6.1 Where This Proposal Aligns
Sutton's emphasis on learning from experience resonates with trajectories as a primitive. You can't do continual learning without captured experience. You can't build world models from runtime without structured traces of runtime.

In this sense, trajectories are necessary infrastructure for Sutton's vision—though not sufficient. Capturing experience is step one; learning from it effectively is the harder problem. The simulation capability I describe (Section 4.2) is a modest step toward world models—using trajectory corpora to predict outcomes—without claiming to solve the full world model problem.
6.2 Where This Proposal Differs
The proposals operate at different layers:

Sutton proposes an architecture for how agents should learn. I'm proposing a data format for capturing what they do. Architecture and interchange format are complementary concerns.
Oak is a research agenda exploring new capabilities. Trajectories are engineering infrastructure enabling interoperability—closer to OpenTelemetry than to a new learning algorithm.
Sutton focuses on the learning algorithm. I'm focused on the data substrate that feeds such algorithms.

Trajectories are a prerequisite for continual learning—necessary infrastructure, currently missing from the open ecosystem.
6.3 The Connection to the Bitter Lesson
Sutton's famous Bitter Lesson argued that methods leveraging computation scale better than methods encoding human knowledge. The implication for agents: hand-crafted rules lose to learned behaviors.

Trajectories support this by providing raw material for learning. Static AGENTS.md files encode human knowledge upfront; trajectory-derived improvements emerge from experience at scale. The bitter lesson suggests learned approaches will dominate as data accumulates.

I hold this connection loosely. The bitter lesson addresses research strategy; trajectories address data infrastructure. The connection is suggestive rather than definitive.
7. What Industry Is Doing (and My Take)
7.1 Fireworks AI: Reinforcement Fine-Tuning
Fireworks RFT offers trajectory-based RL as a managed service. Their "product-model co-design" creates a feedback loop: agent runs → trajectories → scoring → training → better agent.

What they got right: Treating trajectories as training fuel. The flywheel concept is sound—similar to how observability data can inform system improvements when properly structured.

What concerns me: It's a walled garden. Their format is proprietary. You're locked into Fireworks infrastructure. If the economics of managed RL don't work for your scale, you can't take your trajectories elsewhere.

My take: Fireworks validates demand but doesn't solve the portability problem.
7.2 Microsoft: Agent Lightning
Agent Lightning is an open framework for agent RL. They recognized that trajectory format matters—their LightningRL component converts multi-step traces into transitions for standard RL trainers.

What they got right: Framework-agnostic design. The insight that you need to bridge agent execution to RL training infrastructure.

What concerns me: It's training-focused. Context learning (retrieval) isn't the primary use case. The format is internal to the framework, not proposed as an interchange standard.

My take: Microsoft validates the technical approach but isn't solving for ecosystem portability.
7.3 The Gap I See
Neither Fireworks nor Microsoft is proposing an open interchange format. Both assume you'll use their stack end-to-end.

But I think the real value unlocks when trajectories are portable:

Trajectories from LangGraph agents usable in CrewAI systems
Corpora shareable across organizations (with appropriate redaction)
Training on one platform, inference on another

This is the OpenTelemetry argument: observability got better when traces became portable. I believe the same will happen for agent learning.
7.4 What About Everyone Else?
Fireworks and Microsoft aren't the only players. But surveying the landscape:

LangSmith/LangChain and OTeL formats: Great for observability, not designed for learning
Weights & Biases: Experiment tracking, training-focused but not agent-aware
OpenAI/Anthropic: Closed systems, no trajectory interchange
Academic work (Decision Transformer, ReAct): Valuable foundations, but research formats not production-ready

No one is championing open trajectory interchange. That's either because it's not valuable (possible) or because it's a coordination problem no one wants to solve (my bet).
8. Why This Might Fail (And My Responses)
I want to confront the strongest objections honestly.
8.1 "Most trajectories are garbage"
The objection: Agent execution is noisy. Most trajectories are mediocre or wrong. Garbage in, garbage out.

My response: True, and this is familiar territory. High-volume telemetry systems face the same challenge—most traces are routine, and the interesting ones need to be surfaced. The solution is curation: Fireworks explicitly scores trajectories before training; Microsoft's rStar2 filters for quality. The format should support quality signals (outcome, feedback_score, human review flags) that enable intelligent sampling and filtering. Think tail-based sampling applied to learning: retain the trajectories that matter.
8.2 "Context learning doesn't actually work"
The objection: Retrieving similar trajectories might not help. The agent might ignore them or be confused by irrelevant details.

My response: This is an empirical question I can't definitively answer yet. But preliminary evidence is encouraging:

Few-shot prompting works generally
RAG over documents works generally
The combination (RAG over decision traces) is a natural extension

I acknowledge this needs validation. It's in the prerequisites.
8.3 "RL is too expensive and fragile"
The objection: Fine-tuning is expensive. RL is unstable. Reward hacking is real. Most organizations won't do it.

My response: Fair. But the funnel structure means RL is optional. Context learning alone provides value. Trajectories captured for retrieval can later feed RL when the organization is ready. The format should support both without requiring both.
8.4 "No one will share trajectories"
The objection: Trajectories contain competitive intelligence. Organizations won't share them, so "ecosystem portability" is a fantasy.

My response: Partially agree. Cross-organization sharing may be limited. But cross-framework portability within an organization is still valuable. And some domains (open-source, research, public sector) may share. The standard should support private corpora as the default, with sharing as optional.
8.5 "Standards are premature"
The objection: It's too early to standardize. Let a thousand formats bloom, then converge on what works.

My response: This is the strongest objection. I'm genuinely uncertain. Counter-arguments:

The space is consolidating around a few agent frameworks
Fireworks and Microsoft have already made format choices
Early coordination prevents fragmentation

But I acknowledge: a premature standard that's wrong is worse than no standard. That's why this is a position paper, not a proposal.
9. What Would Change My Mind
I want to be explicit about what evidence would make me abandon this:

Context learning doesn't improve agent performance — If experiments show that trajectory retrieval doesn't help (or hurts), the retrieval value proposition fails.

Simulation doesn't outperform naive approaches — If counterfactual prediction from trajectories is no better than random or heuristic baselines, the simulation thesis fails.

Existing formats are sufficient — If LangSmith traces or OpenTelemetry spans can be repurposed for learning and simulation without modification, a new format is unnecessary.

Framework maintainers don't care — If LangGraph, CrewAI, AutoGen maintainers say portability isn't a problem they have, I'm solving the wrong issue.

The curation problem is unsolvable — If trajectory quality is so noisy that no amount of filtering produces useful signal for any of the three capabilities, the whole premise fails.

I'll actively seek disconfirming evidence in the next steps.
10. Preliminary Format Sketch
This is illustrative, not normative. I expect it to change substantially based on implementation experience.

{
  "trajectory_id": "string (UUID, analogous to trace_id)",
  "version": "0.1-draft",

  "metadata": {
    "task_description": "string",
    "domain": "string",
    "timestamp_start": "ISO 8601",
    "timestamp_end": "ISO 8601",
    "duration_ms": "number",
    "agent_id": "string",
    "framework": "string",
    "environment": "string (prod, staging, dev)",
    "outcome": "success | partial_success | failure",
    "feedback_score": "optional number (0-1)",
    "human_reviewed": "boolean",
    "tags": ["array of strings"],
    "parent_trajectory_id": "optional string (for sub-agent calls)"
  },

  "context": {
    "referrer": "string (URL or path where agent invoked)",
    "user": {
      "id": "string",
      "handle": "string",
      "org_id": "string",
      "teams": ["array of team identifiers"],
      "timezone": "string"
    },
    "entities": [
      {
        "type": "string (service, dashboard, monitor, etc.)",
        "id": "string",
        "name": "string",
        "metadata": "object (type-specific attributes)"
      }
    ],
    "resources": [
      {
        "type": "string (document, api, database, etc.)",
        "uri": "string",
        "accessed_at": "ISO 8601"
      }
    ],
    "custom_context": "string (user-provided context)"
  },

  "system_message": {
    "content": "string (system prompt)",
    "timestamp": "ISO 8601"
  },

  "turns": [
    {
      "turn_id": "integer",
      "span_id": "string (unique within trajectory)",
      "parent_span_id": "optional string (for nested operations)",
      "timestamp": "ISO 8601",
      "duration_ms": "number",
      "error": "boolean",
      "turn_reward": "optional number",

      "messages": [
        {
          "message_id": "string",
          "role": "user | assistant | system | tool",
          "timestamp": "ISO 8601",

          "content": {
            "type": "text | widget | dashboard | tool_call | tool_response | structured",
            "data": "object (type-specific content)",
            "text": "optional string (text representation for non-text types)"
          },

          "reasoning": "optional string (chain-of-thought, assistant only)",

          "visibility": {
            "send_to_user": "boolean (should render in UI)",
            "persist": "boolean (should save to storage)"
          },

          "context_snapshot": {
            "entities": ["array of entity refs active at this message"],
            "available_tools": ["array of tool names available"]
          }
        }
      ]
    }
  ],

  "final_reward": "optional number (trajectory-level outcome signal)"
}
10.1 Format Design Decisions
Turn-based structure: Messages are grouped into turns (user input → agent response cycles). This provides a natural unit for slicing trajectories—you can process by turn for training data augmentation, or by full trajectory for end-to-end evaluation.

Rich content types: The content.type field supports multiple content types beyond text:

text: Plain text or markdown
widget: UI components (charts, tables, interactive elements)
dashboard: Dashboard definitions or references
tool_call: Structured tool invocation
tool_response: Tool execution results
structured: Domain-specific structured responses

This matters for display use cases where agents produce visual outputs.

Context entities: The context.entities array captures structured knowledge about what the agent knew—services, dashboards, monitors, users referenced in the conversation. This enables:

Similarity matching: "Find trajectories involving this service"
Simulation: "What entities were in scope when this decision was made?"
Training filtering: "Train only on trajectories involving production services"

Visibility controls: The visibility object on each message indicates:

send_to_user: Whether this message should render in UI (some tool calls are internal)
persist: Whether this message should be saved (ephemeral vs. permanent)

These are essential for display use cases but often missing from ML-focused formats.

Context snapshots: Each message can include a context_snapshot capturing the state at that moment—which entities were active, which tools were available. This enables simulation by reconstructing decision points.
10.2 Trajectory Slicing Patterns
A single trajectory can be processed in multiple ways for different purposes. These ingestor patterns define how to slice:

Pattern
Description
Use Case
Identity
Full trajectory as single unit
End-to-end evaluation, display
Turns
Each turn as separate trajectory
Training data generation, per-turn judging
Prefixes
Sliding window of N turns
Data augmentation, partial trajectory scoring
Messages
Individual messages
Fine-grained analysis, message-level annotation


Example: A 5-turn trajectory can produce:

1 identity slice (the full trajectory)
5 turn slices (one per turn)
10 prefix slices (turns 1, 1-2, 1-3, 1-4, 1-5, plus 2, 2-3, etc.)

The format should support efficient slicing without duplicating data. Turns are the natural unit—they group related messages and provide clear boundaries.
10.3 Annotations as Linked Entities
Annotations (evaluator scores, human feedback, labels) should link to trajectories rather than embed within them:

{
  "annotation_id": "string",
  "trajectory_id": "string (foreign key)",
  "turn_id": "optional integer (null = trajectory-level)",
  "message_id": "optional string (null = turn-level)",

  "evaluator": {
    "id": "string",
    "type": "human | model | heuristic",
    "version": "string"
  },

  "score": "number",
  "label": "optional string",
  "feedback": "optional string",
  "timestamp": "ISO 8601"
}

Why separate?

Multiple evaluators can annotate the same trajectory
Annotations can be added retroactively without modifying trajectories
Different retention policies for trajectories vs. annotations
Cleaner schema evolution—annotation format can change independently

This follows the pattern from APM: traces are immutable once written; annotations are a separate layer.

Design rationale:

trajectory_id and span_id follow distributed tracing conventions for correlation
parent_trajectory_id and parent_span_id enable hierarchical trace structures (sub-agent calls, nested tool invocations)
duration_ms at both levels enables latency analysis and performance debugging
environment tag supports filtering production vs. development trajectories
reasoning enables context learning (retrievable chain-of-thought)
step_reward and final_reward enable RL (credit assignment)
human_reviewed and feedback_score enable curation and quality filtering
framework enables portability tracking and framework-specific analysis
Minimal required fields; most are optional to reduce ingestion friction
10.4 Open Questions
Branching/backtracking: How to represent exploration and rollback? Tree structure vs. linear with annotations? The current linear turn model doesn't capture agent backtracking.
Compression: Full reasoning is verbose. What's the right fidelity tradeoff? Can we summarize reasoning while preserving learning signal?
Privacy: Should reasoning be redactable without breaking utility? Need field-level controls similar to PII scrubbing in logs. The visibility flags help but may not be sufficient.
Retention: What's the decay curve for trajectory value? Recent traces vs. historical corpus have different utility profiles.
Schema evolution: How do we version the format? Strict versioning vs. additive changes vs. transformation layers?
Cross-framework content types: The content.type enum will differ across frameworks. How to standardize or map between them?
11. Open Challenges
11.1 Privacy and Security
Concern
Severity
Mitigation Ideas
PII in trajectories
High
Redaction pipeline, opt-out fields
Trajectory poisoning
Medium
Provenance tracking, anomaly detection
IP exposure via reasoning
High
Optional reasoning, summarization

11.2 Quality and Curation
This is the hard problem. Not solved by format alone. Needs:

Scoring heuristics (outcome-based, model-based)
Human review workflows
Diversity metrics (not just quality—coverage matters)
11.3 Scale
Anyone who has operated high-volume trace pipelines knows these challenges:

Storage: Trajectories are verbose. Need tiered storage, compression, and intelligent retention policies—hot storage for recent/high-value traces, cold storage for historical corpus.
Cardinality: Unbounded tag values (task descriptions, agent IDs) can explode index sizes. Need cardinality management strategies similar to metrics systems.
Retrieval: Efficient similarity search over structured traces requires careful index design. Embedding-based retrieval adds latency and cost.
Sampling: At scale, you can't keep everything. Need sampling strategies that preserve learning signal—tail-based sampling for failures, head-based for routine successes.
Training integration: Export paths to RL infrastructure (Fireworks, Lightning, custom) with appropriate batching and format conversion.
12. Prerequisites for Formal Proposal
Before proposing a standard, I need to validate assumptions:
12.1 Build and Test
Deliverable
Validates
Reference SDK
Format is practical to produce/consume
LangGraph integration
Cross-framework capture works
Trajectory retrieval demo
Context learning improves performance
Simulation prototype
Counterfactual predictions have measurable accuracy
Agent Lightning export
RL compatibility is achievable

12.2 Gather Evidence
Question
Method
Does trajectory retrieval help?
A/B test with/without retrieval
Does simulation improve planning?
Compare simulated vs. naive action selection
What's minimum corpus size?
Learning curve experiments
Do frameworks want this?
Maintainer interviews

12.3 Seek Disconfirmation
Talk to skeptics
Try to break the format with edge cases
Document failures publicly
13. Next Steps
Build reference implementation — Minimal SDK, real trajectories from internal agents
Run context learning experiment — Does retrieval actually help?
Engage framework maintainers — Is portability a real problem?
Publish findings — Including failures
Iterate or abandon — Based on evidence
14. Conclusion
I believe trajectories are the missing primitive for continual learning agents. The funnel from execution to context learning to RL is the path to agents that improve through use.

We've seen this pattern before. Observability transformed when traces became portable and structured. APM moved from "look at this dashboard" to "here's why your system is slow, and here's what to do about it." The same evolution is possible for agent systems if we build the right data infrastructure.

Fireworks and Microsoft validate pieces of this vision. Neither solves for open interchange. I think that's a gap worth filling.

But I hold this belief provisionally. The hard questions—does context learning work? is curation tractable? do frameworks care?—remain open. This position paper is an invitation to find out.

If I'm wrong, I want to know. If I'm right, let's build it (and bring credibility to Datadog in the Agentic Observability space).
Appendix A: The Learning Funnel in Practice
Hypothetical: Incident Response Agent

Week
Activity
Trajectories
Outcome
1-4
Agent handles incidents
500 generated
Baseline performance
5-8
Context learning enabled
Retrieved as examples
+15% resolution speed (hypothesis)
8-12
Corpus curated
300 high-quality selected
—
12-16
RL fine-tuning
Training completed
+25% additional improvement (hypothesis)


This is speculative. The percentages are illustrative. Validating this progression is the point of the experiments.

