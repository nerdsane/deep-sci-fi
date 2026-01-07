# ART vs Letta Trajectories: Implementation-Level Comparison

**Date:** 2026-01-01  
**Comparing:**
- **ART/Unsloth**: OpenPipe/ART v0.5.4 (GitHub main)
- **Your implementation**: Letta backend + DSF-specific work

---

## 🎯 Executive Summary

**ART** is a **product** - vertically integrated training-as-a-service.  
**Your work** is **infrastructure** - portable trajectory substrate for ecosystem.

Both capture execution traces ("trajectories"), but with fundamentally different architectures and goals.

---

## 📊 Data Structure Comparison

### ART's Trajectory

```python
# src/art/trajectories.py:38-46
class Trajectory(pydantic.BaseModel):
    messages_and_choices: MessagesAndChoices  # OpenAI format messages + Choice objects
    tools: Tools | None = None                # Tool definitions
    additional_histories: list[History] = []  # Sub-agents/branching
    reward: float                             # REQUIRED for GRPO
    metrics: dict[str, float | int | bool] = {}  # Custom metrics (win rate, etc)
    auto_metrics: dict[str, float | int | bool] = {}  # Auto-computed metrics
    metadata: dict[str, MetadataValue] = {}   # Arbitrary metadata
    logs: list[str] = []                      # Debug logs
    start_time: datetime                      # Timing
```

**Key characteristics:**
- **Reward-centric**: `reward` is required field (training-first design)
- **Messages + Choices**: Stores both input messages AND OpenAI `Choice` objects (to distinguish trainable vs non-trainable)
- **Flat list**: `messages_and_choices` is linear sequence
- **Sub-agents**: `additional_histories` for complex multi-agent scenarios
- **Training-focused**: No summaries, embeddings, or search metadata

### Your Trajectory

```python
# letta/letta/schemas/trajectory.py:23-59
class Trajectory(TrajectoryBase):
    id: str                                    # UUID
    agent_id: str                              # Agent relationship
    data: Dict[str, Any]                       # FLEXIBLE - any structure
    
    # LLM-generated (for search/learning)
    searchable_summary: Optional[str]          # Natural language summary
    outcome_score: Optional[float]             # 0-1 quality score
    score_reasoning: Optional[str]             # Explanation
    
    # Metadata
    created_at: datetime
    updated_at: Optional[datetime]
    organization_id: Optional[str]
    
    # embedding: List[float]  # Internal only, excluded from API
```

**Key characteristics:**
- **Search-centric**: Includes `searchable_summary`, `outcome_score`, embedding
- **Flexible structure**: `data` is unstructured JSON (any agent type)
- **Storage-first**: Designed for Postgres + pgvector retrieval
- **Turn-based inside data**: Your converter creates structured turns within `data.turns`
- **No reward field**: Outcome score is 0-1, not RL reward

---

## 🔄 Trajectory Capture Architecture

### ART: Auto-Capture via HTTP Interception

```python
# src/art/auto_trajectory.py:105-146
def patch_httpx():
    """Monkey-patch httpx to intercept OpenAI API calls"""
    original_close = httpx._models.Response.close
    
    def patched_close(self):
        original_close(self)
        if context := auto_trajectory_context_var.get(None):
            context.handle_httpx_response(self)  # Extract messages + choices
```

**How it works:**
1. User calls `capture_auto_trajectory(coroutine)`
2. Sets context var with empty `Trajectory`
3. Patches httpx to intercept all HTTP responses
4. When OpenAI API returns, extracts messages + choices
5. Appends to trajectory automatically

**Pros:**
- ✅ Zero boilerplate - captures ANY OpenAI SDK usage automatically
- ✅ Works with existing codebases (add 1 wrapper function)
- ✅ Framework-agnostic (LangChain, CrewAI, raw OpenAI)

**Cons:**
- ❌ Requires monkey-patching (fragile, breaks with SDK updates)
- ❌ OpenAI-specific (doesn't capture Anthropic, etc.)
- ❌ Context-based (async context vars, complex debugging)

### Your Approach: Explicit Conversion Post-Execution

```python
# letta/letta/services/trajectory_converter.py:32-70
async def from_run(self, run: Run, steps: List[Step], messages: List[Message]) -> TrajectoryCreate:
    """Convert completed run to trajectory"""
    metadata = self._extract_metadata(run, steps, messages)
    turns = self._structure_turns(steps, messages)
    outcome = self._determine_outcome(run, messages)
    
    return TrajectoryCreate(
        agent_id=run.agent_id,
        data={"run_id": run.id, "metadata": metadata, "turns": turns, "outcome": outcome}
    )
```

**Integrated in RunManager:**
```python
# letta/letta/server/run_manager.py:426-434
async def _create_trajectory_from_run(self, run: Run):
    """Hook at end of run completion"""
    if not os.getenv("ENABLE_TRAJECTORY_CAPTURE"):
        return
    
    converter = TrajectoryConverter()
    trajectory_create = await converter.from_run(run, steps, messages)
    await trajectory_service.create(trajectory_create)
```

**Pros:**
- ✅ Clean, testable code (no monkey-patching)
- ✅ Works with Letta's existing Run/Step/Message architecture
- ✅ LLM-agnostic (works with any model)
- ✅ Safe error handling (failures don't break runs)

**Cons:**
- ❌ Letta-specific (requires Run/Step/Message ORM)
- ❌ Requires integration into execution loop
- ❌ Environment variable toggle (manual opt-in)

---

## 🏗️ Architecture: Client/Server vs Integrated

### ART: Split Client/Server (Decoupled)

```
┌─────────────────────────────────┐
│   Your Application (Client)     │
│  - Rollout logic                │
│  - Game/task implementation     │
│  - art.Trajectory creation      │
└───────────┬─────────────────────┘
            │ HTTP
            │ (trajectories JSON)
            ▼
┌─────────────────────────────────┐
│   ART Backend (Server)          │
│  - vLLM inference               │
│  - GRPO training (Unsloth)      │
│  - Checkpoint management        │
│  - OpenAI-compatible API        │
└─────────────────────────────────┘
```

**Key design:**
- Client is **lightweight** (minimal dependencies)
- Server handles **heavy lifting** (GPU, training)
- Communication via **REST API** (trajectories as JSON)
- Server can be **local** or **serverless** (W&B Training)

**Example:**
```python
# examples/2048/train.py
backend = LocalBackend()  # or ServerlessBackend()
await model.register(backend)

# Client gathers trajectories
groups = await art.gather_trajectory_groups(...)

# Server trains model
await model.train(groups, config=art.TrainConfig(...))
```

### Your Approach: Integrated (Monolithic)

```
┌─────────────────────────────────┐
│   Letta Backend (Monolith)      │
│  ┌───────────────────────────┐  │
│  │ Agent Execution           │  │
│  │ (RunManager)              │  │
│  └───────┬───────────────────┘  │
│          │                       │
│          ▼                       │
│  ┌───────────────────────────┐  │
│  │ Trajectory Capture        │  │
│  │ (TrajectoryConverter)     │  │
│  └───────┬───────────────────┘  │
│          │                       │
│          ▼                       │
│  ┌───────────────────────────┐  │
│  │ Storage (Postgres)        │  │
│  │ + pgvector                │  │
│  └───────────────────────────┘  │
└─────────────────────────────────┘
```

**Key design:**
- Everything in **one codebase** (Letta backend)
- Trajectory capture **built into** execution loop
- Storage **co-located** with application
- No client/server split

**Example:**
```python
# letta/letta/server/run_manager.py
async def complete_run(self, run_id: str):
    # Execute agent
    run = await self.run_service.complete(run_id)
    
    # Capture trajectory (integrated)
    await self._create_trajectory_from_run(run)
```

---

## 🎓 GRPO Training: How ART Uses Trajectories

### The Training Loop

```python
# examples/2048/train.py:45-77
for i in range(TRAIN_STEPS):
    # 1. INFERENCE: Gather trajectories (18 parallel games)
    train_groups = await art.gather_trajectory_groups(
        (art.TrajectoryGroup(rollout(model, i) for _ in range(18)) 
         for _ in range(1)),
        after_each=lambda group: ruler_score_group(group, "openai/o3"),
    )
    
    # 2. TRAINING: Fine-tune model on scored trajectories
    await model.train(train_groups, config=art.TrainConfig(learning_rate=1e-5))
```

### Key insight: Group-based relative scoring

```python
# src/art/rewards/ruler.py:220-318
async def ruler_score_group(group: art.TrajectoryGroup, judge_model: str):
    """Score trajectories RELATIVE to each other (not absolute)"""
    
    # 1. Extract messages from all trajectories in group
    message_lists = [traj.messages() for traj in group.trajectories]
    
    # 2. Send ALL trajectories to LLM judge at once
    scores = await ruler(message_lists, judge_model=judge_model)
    
    # 3. Replace trajectory.reward with RULER score
    for traj, score in zip(group.trajectories, scores):
        traj.reward = score.score  # 0-1 score from o3
```

**Why groups?**
- GRPO requires **relative** rewards within a group (not absolute)
- Sending 8-18 trajectories together gives judge **comparative context**
- More efficient than scoring individually

### Your Approach: No RL Yet (Phase 5)

You **don't have RL training** implemented. Your focus is:
1. **Capture** trajectories ✅
2. **Store** in Postgres + pgvector ✅
3. **Retrieve** for context learning ⏳ (planned)
4. **RL training** ❌ (future, possibly integrate with ART)

---

## 🔍 Reward/Scoring Comparison

### ART: Reward is Primary Signal

```python
# examples/tic_tac_toe/rollout.py:94-105
if winner == game["agent_symbol"]:
    trajectory.reward = 1              # Win
elif winner == game["opponent_symbol"]:
    trajectory.reward = 0              # Loss
elif winner == "draw":
    trajectory.reward = 0.5            # Draw

trajectory.metrics["num_moves"] = move_number
```

**Characteristics:**
- `reward` is **required field** (can't create trajectory without it)
- Rewards designed for **GRPO optimization** (relative scale matters)
- Often **hand-crafted** (game outcome, success heuristics)
- RULER **replaces** rewards with LLM-judged scores

### Your Approach: Outcome Score for Curation

```python
# letta/letta/services/trajectory_processing.py:74-136
async def score_trajectory(self, trajectory_data: Dict[str, Any]) -> Tuple[float, str]:
    """LLM evaluates trajectory and assigns 0-1 score"""
    
    prompt = f"""
    Analyze this agent execution and rate its success (0-1):
    - Did it achieve the goal?
    - Was it efficient?
    - Were there errors?
    
    {json.dumps(trajectory_data)}
    """
    
    response = await llm_client.chat.completions.create(...)
    return score, reasoning
```

**Characteristics:**
- `outcome_score` is **optional** (trajectories exist without scores)
- Scores for **filtering/curation**, not training
- Always **LLM-generated** (no hand-crafted heuristics)
- Independent scoring (not group-relative)

---

## 🧮 Metadata & Metrics Comparison

### ART: Training-Focused Metrics

```python
# examples/2048/rollout.py:90-114
trajectory.metrics["max_value"] = max_value
trajectory.metrics["board_value"] = board_value
trajectory.metrics["num_moves"] = move_number
trajectory.metrics["win"] = agent_won
trajectory.metrics["invalid_move"] = 0 or 1

# Reward computed from metrics
if agent_won:
    trajectory.reward = 2  # Double reward for wins
else:
    max_value_reward = (math.log(max_value, 2) - 1) / (...)
    board_value_reward = (math.log(board_value, 2) - 1) / (...)
    trajectory.reward = max_value_reward + (board_value_reward * 0.2)
```

**Purpose:** Metrics inform reward calculation and benchmarking

### Your Approach: Execution-Focused Metadata

```python
# letta/letta/services/trajectory_converter.py:72-116
metadata = {
    "start_time": run.created_at.isoformat(),
    "end_time": run.completed_at.isoformat(),
    "duration_ns": duration_ns,
    "status": run.status,
    "stop_reason": run.stop_reason,
    "step_count": len(steps),
    "message_count": len(messages),
    "tools_used": sorted(list(tools_used)),
    "input_tokens": total_input_tokens,
    "output_tokens": total_output_tokens,
    "models": list(set(step.model for step in steps)),
    "error": run.metadata_.get("error"),
}
```

**Purpose:** Metadata for analysis, debugging, cost tracking

---

## 💾 Storage Comparison

### ART: Filesystem + Logs

**Storage:**
- Trajectories serialized to **JSON files** on disk
- Checkpoint directories organized by step
- Optional S3 export for backup

**No database, no vector search built-in.**

```python
# src/art/backend.py:139-150
async def _experimental_pull_from_s3(self, model: Model, s3_bucket: str, ...):
    """Download trajectory logs from S3"""
```

**Access pattern:**
- Load all trajectories for a training batch
- Filter in-memory by metadata
- No semantic search

### Your Approach: Postgres + pgvector

**Storage:**
```sql
-- letta/alembic/versions/000_add_trajectories_table.py
CREATE TABLE trajectories (
    id UUID PRIMARY KEY,
    agent_id UUID NOT NULL,
    data JSONB NOT NULL,
    searchable_summary TEXT,
    outcome_score FLOAT CHECK (outcome_score >= 0 AND outcome_score <= 1),
    score_reasoning TEXT,
    embedding vector(1536),  -- pgvector
    created_at TIMESTAMP NOT NULL,
    organization_id UUID,
    
    INDEX idx_agent_id (agent_id),
    INDEX idx_outcome_score (outcome_score),
    INDEX idx_created_at (created_at)
);
```

**Access pattern:**
```python
# letta/letta/services/trajectory_service.py:search()
# 1. Generate embedding from query
query_embedding = await generate_embedding(query)

# 2. Vector similarity search (pgvector)
results = session.execute(
    select(Trajectory)
    .where(Trajectory.embedding.cosine_distance(query_embedding) < 0.3)
    .order_by(Trajectory.embedding.cosine_distance(query_embedding))
    .limit(limit)
)
```

**Features:**
- ✅ Semantic search (vector similarity)
- ✅ Structured filtering (outcome_score, agent_id, date)
- ✅ Relational queries (JOIN with agents, orgs)
- ✅ Built-in indexing

---

## 🔧 Tool/Function Integration

### ART: No Agent-Facing Tools

ART trajectories are **for training**, not retrieval.

Agents **don't query** their own history. The training loop happens **offline** - you collect trajectories, train model, deploy new checkpoint.

### Your Approach: Agent-Facing Tools (Planned)

```python
# Planned: letta/letta/functions/function_sets/trajectories.py
def search_trajectories(
    agent_state: AgentState,
    query: str,
    min_score: Optional[float] = None,
    limit: int = 5
) -> str:
    """
    Search past trajectories by similarity.
    
    Use this to find similar situations and learn from past successes.
    
    Example:
      search_trajectories("user wants sci-fi story", min_score=0.7)
    """
```

**Agents can:**
- Search their own history
- Learn from successful examples
- Avoid past failures

**This is your unique contribution** - ART doesn't do inference-time retrieval.

---

## 🎨 RULER Implementation Deep Dive

This is ART's killer feature. Let's see how it works:

```python
# src/art/rewards/ruler.py:53-217
async def ruler(
    message_lists: list[list[ChatCompletionMessageParam]],
    judge_model: str = "openai/o3",
    rubric: str = DEFAULT_RUBRIC,
) -> list[TrajectoryScore]:
    """Score trajectories relative to each other using LLM judge."""
    
    # 1. OPTIMIZATION: Find common prefix to save tokens
    common_prefix_len = 0
    for idx, msg in enumerate(message_lists[0]):
        if all(len(ml) > idx and ml[idx] == msg for ml in message_lists):
            common_prefix_len += 1
        else:
            break
    
    # 2. SERIALIZE: Send all trajectories to judge at once
    user_text = ""
    if common_prefix_len > 0:
        user_text += "<context>\n" + json.dumps(common_prefix[:]) + "\n</context>\n\n"
    
    for idx, messages in enumerate(message_lists, start=1):
        trimmed = messages[common_prefix_len:]
        user_text += f'<trajectory id="{idx}">\n{json.dumps(trimmed)}\n</trajectory>\n'
    
    # 3. JUDGE: LLM scores all trajectories
    judge_prompt = f"""
    All trajectories have the same goal. Score each 0-1.
    
    Grading standards:
    {rubric}  # Default: achieving goal > efficiency > partial credit
    """
    
    response = await acompletion(
        model=judge_model,
        messages=[
            {"role": "system", "content": judge_prompt},
            {"role": "user", "content": user_text}
        ],
        response_format=Response,  # Structured output (list of scores)
    )
    
    # 4. RETURN: Scores for each trajectory
    return parsed.scores  # [TrajectoryScore(id="1", score=0.8, explanation="..."), ...]
```

**Key insights:**

1. **Relative scoring**: Judge sees all trajectories together, understands comparative quality
2. **Token optimization**: Common prefix sent once (system prompt shared by all)
3. **Structured output**: Forces JSON response with Pydantic schema
4. **Default rubric works**: Generic rubric (achieve goal > efficiency) works across tasks
5. **Handles edge cases**: Identical trajectories, missing scores, API failures

**Why this works better than hand-crafted rewards:**
- Task-agnostic (works for games, coding, research)
- No reward engineering (2-3x faster development)
- Scales to complex tasks (email agent beat o3)

---

## 📦 Turn Structure Comparison

### ART: Flat Message List

```python
trajectory = art.Trajectory(
    messages_and_choices=[
        {"role": "system", "content": "You are a 2048 player"},
        {"role": "user", "content": "Board: [[2,0,0,0],...]"},
        Choice(message={"role": "assistant", "content": "<move>left</move>"}),  # OpenAI Choice
        {"role": "user", "content": "Board: [[4,2,0,0],...]"},
        Choice(message={"role": "assistant", "content": "<move>up</move>"}),
        # ... continues
    ],
    reward=0.8,
)
```

**Characteristics:**
- **Flat list**: No explicit turn structure
- **Messages + Choices**: Mixing dictionaries and `Choice` objects
- **Trainable marking**: `Choice` objects indicate trainable tokens
- **Simple**: Easy to serialize/deserialize

### Your Approach: Structured Turns

```python
{
    "run_id": "run-123",
    "metadata": {...},
    "turns": [
        {
            "step_id": "step-1",
            "model": "gpt-4",
            "input_tokens": 150,
            "output_tokens": 50,
            "stop_reason": "tool_calls",
            "messages": [
                {"role": "user", "content": "..."},
                {"role": "assistant", "content": "...", "tool_calls": [...]},
                {"role": "tool", "tool_call_id": "...", "content": "..."}
            ]
        },
        {
            "step_id": "step-2",
            "model": "gpt-4",
            # ...
        }
    ],
    "outcome": "success"
}
```

**Characteristics:**
- **Explicit turns**: Each step is a distinct unit
- **Rich metadata per turn**: Model, tokens, stop reason
- **Tool call tracking**: Tool invocations + responses grouped
- **Multi-step reasoning**: Each turn represents one LLM inference

---

## 🧪 Testing & Examples

### ART: Real-World Task Examples

**They provide 6+ complete examples:**
- ✅ 2048 game (Qwen3 14B learns to play)
- ✅ Tic-tac-toe (beats minimax)
- ✅ Email agent (Qwen 14B beats o3)
- ✅ Codenames (word game)
- ✅ Temporal Clue (reasoning)
- ✅ LangGraph integration

**Each example is:**
- End-to-end runnable (Colab notebooks)
- Benchmarked (charts showing improvement)
- Production-tested (used internally)

### Your Approach: No Examples Yet

**Status:**
- ✅ Infrastructure built (DB, services, API)
- ❌ No example trajectories
- ❌ No demo agents using trajectories
- ❌ No benchmarks showing improvement

**Next step:** Build DSF example showing trajectories improve story quality

---

## 🚀 Deployment & DevOps

### ART: Serverless First

**W&B Training (Serverless RL):**
```python
from art.serverless.backend import ServerlessBackend

backend = ServerlessBackend(api_key="wandb_key")
model.register(backend)

# Backend handles:
# - GPU provisioning
# - Inference cluster (2000+ concurrent)
# - Training infrastructure
# - Checkpoint storage
# - Model serving
```

**Benefits:**
- No GPU management
- Auto-scaling
- Pay-per-use
- Instant deployment

**Also supports:**
- `LocalBackend()` - Run on your GPU
- `SkyPilot` - Ephemeral GPU clusters

### Your Approach: Self-Hosted

**Requires:**
- Postgres database
- pgvector extension
- OpenAI API key (for embeddings)
- Environment variable toggle

**No managed service.**

---

## 📈 What Each Optimizes For

### ART Optimizes For:

1. **Training velocity**: Shortest path from idea to fine-tuned model
2. **Ease of integration**: Wrap existing code, minimal changes
3. **Cost efficiency**: Serverless RL (40% cheaper, 28% faster)
4. **Benchmark performance**: Models that beat GPT-4o/o3
5. **Zero reward engineering**: RULER eliminates manual rewards

### Your Approach Optimizes For:

1. **Portability**: Standard format works across frameworks
2. **Storage & retrieval**: Semantic search, structured queries
3. **Multiple use cases**: Display, retrieval, RL, simulation
4. **Ecosystem improvement**: AGENTS.md evolution, Skills discovery
5. **Open infrastructure**: Not locked into one vendor

---

## 🎯 Critical Differences Summary

| Dimension | ART | Your Approach |
|-----------|-----|---------------|
| **Architecture** | Client/Server split | Monolithic (integrated) |
| **Primary goal** | RL training (GRPO) | Continual learning (retrieval + future RL) |
| **Data capture** | Monkey-patch httpx | Explicit conversion post-run |
| **Storage** | Filesystem + S3 | Postgres + pgvector |
| **Retrieval** | None (training-only) | Semantic search (vector + filters) |
| **Reward/score** | Required field, training signal | Optional, curation signal |
| **Agent access** | No (offline training) | Yes (search_trajectories tool) |
| **Format** | OpenAI messages + Choice | Flexible JSONB (any structure) |
| **Portability** | Proprietary | Designed for interchange |
| **DevOps** | Serverless-first | Self-hosted |
| **Ecosystem focus** | Vertical product | Horizontal infrastructure |

---

## 💡 What You Can Learn from ART

### 1. **RULER is Production-Ready**

Your position paper was uncertain if LLM-based rewards work (Section 8.2). **ART proves they do:**
- Benchmarks show Qwen 14B beats o3 on email task
- Generic rubric works across domains
- Group-based scoring is efficient

**Action:** Adopt RULER for Phase 5 (RL training)

### 2. **Auto-Capture is Powerful**

Their httpx monkey-patching is hacky but **effective**:
- Zero boilerplate for users
- Works with any OpenAI SDK usage
- Framework-agnostic

**Action:** Consider optional auto-capture mode for letta-code

### 3. **Client/Server Split Scales**

Decoupling trajectory gathering from training enables:
- Run client on laptop, train on GPU cluster
- Swap backends (local, cloud, serverless)
- Independent deployment

**Action:** Consider splitting trajectory service from Letta backend (optional remote storage)

### 4. **Examples Sell the Vision**

ART has 6+ runnable examples with benchmarks. You have zero.

**Action:** Build DSF example showing:
- Trajectory capture during story creation
- Retrieval of successful patterns
- Measurable quality improvement

### 5. **Groups > Individual Trajectories**

GRPO doesn't need absolute rewards, just relative ordering within a group.

**Action:** When implementing RL, use group-based scoring (send 8-16 trajectories to judge at once)

---

## 🤔 What ART Could Learn from You

### 1. **Retrieval is Valuable**

ART focuses only on training. **Context learning** (retrieval) is:
- Immediate benefit (no training required)
- Lower cost (no GPU)
- Complementary to RL

**Your hypothesis:** Injecting successful trajectory examples improves performance even without training.

### 2. **Portable Formats Enable Ecosystems**

ART's proprietary format locks users into their stack. **OpenTelemetry won** because traces were portable.

**Your vision:** Trajectories as ecosystem primitive (LangGraph → CrewAI → AutoGen)

### 3. **Storage Enables Analysis**

Filesystem storage limits what you can do. **Postgres + pgvector** enables:
- Semantic search
- Aggregate analytics
- Pattern detection
- Time-series analysis

### 4. **Multi-Use Data is Efficient**

ART trajectories serve one purpose (training). **Your format** serves four:
- Display (UI rendering)
- Retrieval (context learning)
- Simulation (counterfactuals)
- Training (RL)

Capture once, use multiple ways.

### 5. **Ecosystem Feedback Loops**

Using trajectories to improve **Skills**, **AGENTS.md**, **MCP discovery** is broader vision than just model improvement.

---

## 🔮 Recommended Integration Strategy

### Phase 1-3: Build Your Unique Value (Retrieval)

**Focus on what ART doesn't do:**
1. ✅ Trajectory capture (done)
2. ✅ Storage + indexing (done)
3. ⏳ Agent-facing search tools (do next)
4. ⏳ Validate retrieval hypothesis (experiment)

**Goal:** Prove that trajectory retrieval improves agents **without training**.

### Phase 5: Integrate with ART for Training

**Don't reinvent GRPO training. Instead:**

1. **Export to ART format:**
```python
def export_to_art(letta_trajectories: List[Trajectory]) -> List[art.Trajectory]:
    """Convert Letta trajectories to ART format"""
    return [
        art.Trajectory(
            messages_and_choices=convert_turns_to_messages(t.data["turns"]),
            reward=t.outcome_score or 0.5,
            metrics=t.data["metadata"],
        )
        for t in letta_trajectories
    ]
```

2. **Train with ART:**
```python
from art.serverless.backend import ServerlessBackend

# Export trajectories
art_trajectories = export_to_art(letta_trajectories)

# Train using ART
backend = ServerlessBackend(api_key=wandb_key)
model = art.TrainableModel(...)
await model.train(art_trajectories, config=art.TrainConfig(...))
```

3. **Keep your retrieval layer separate** (unique value)

### Long-term: Push for Portable Standard

Once you've proven value:
1. Publish trajectory interchange spec
2. Work with ART, LangChain, etc. on standard
3. Be the "OpenTelemetry for agents"

---

## 🎓 Key Takeaways

1. **ART is a product, you're building infrastructure** - Different goals, complementary
2. **Their capture is clever but fragile** - Monkey-patching vs. your clean integration
3. **RULER validates LLM rewards work** - Adopt it for Phase 5
4. **Retrieval is your unique value** - ART doesn't do this
5. **Storage architecture matters** - Postgres+pgvector > filesystem
6. **Groups > individuals for RL** - Relative scoring is key
7. **Examples needed** - Build DSF demo ASAP
8. **Integration > competition** - Use ART for training, keep retrieval layer

---

## 🚀 Immediate Action Items

1. **Read ART examples** - Study their rollout patterns
2. **Build Phase 2** - Agent search tools (your unique value)
3. **DSF demo** - Prove retrieval works
4. **Document format** - Publish trajectory spec
5. **Test RULER** - Validate automatic rewards
6. **Engage ART team** - Explore collaboration on standards

Your work is **infrastructure**, not a competing product. Focus on portability and ecosystem value.
