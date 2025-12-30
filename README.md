# DSF Agent - Deep Sci-Fi World Building

A reference implementation of an agent that uses Letta's evaluation tools to build logically consistent, deeply researched science fiction worlds.

## Philosophy

**Tools over workflows. Evaluation over prescription. Scale with better models.**

This agent demonstrates how to use generic Letta platform tools for specialized creative work. Rather than hard-coding a worldbuilding workflow, the agent has access to evaluation tools and decides when and how to use them based on context.

## Features

- **Powerful Reasoning**: Uses Claude Opus 4.5 for world-building
- **Fast Evaluation**: Uses Claude Sonnet 4.5 for quality checks
- **Self-Evaluating**: Agent can assess its own work using `assess_output_quality`
- **Consistency Checking**: Find logical contradictions with `check_logical_consistency`
- **Iterative Improvement**: Measure progress with `compare_versions` and `analyze_information_gain`
- **Deep Research**: Use web search and code execution to verify scientific plausibility
- **World Management**: Save, load, and track world iterations (via letta-code)

## Quick Start

### 1. Set up your API key (one time)

```bash
# Add your Anthropic API key to Letta's .env file
echo "ANTHROPIC_API_KEY=your_key_here" >> ~/Development/letta/.env
```

**Important**: The API key goes in `~/Development/letta/.env` (NOT in dsf-agent/.env)
- The Letta server running in Docker needs it
- No LETTA_API_KEY needed for local server

### 2. Start everything

```bash
cd ~/Development/dsf-agent

# Start Letta server + letta-code UI
./start.sh

# When done, stop everything
./stop.sh
```

The script will:
1. ✓ Check prerequisites (Docker, API keys)
2. ✓ Switch to evaluation-tools branch
3. ✓ Build and start Letta server with Docker
4. ✓ Wait for server to be ready
5. ✓ Ask if you want to start letta-code UI (say yes!)
6. ✓ You're ready to use letta-code normally

### Manual Way (if you prefer)

<details>
<summary>Click to expand manual instructions</summary>

#### 1. Start Letta Server (with evaluation tools)

```bash
# In ~/Development/letta directory
cd ~/Development/letta

# Make sure you're on the evaluation-tools branch
git checkout evaluation-tools

# Start with Docker (builds from source)
docker compose -f dev-compose.yaml up -d --build

# Check status
docker compose -f dev-compose.yaml ps

# View logs
docker compose -f dev-compose.yaml logs -f
```

The server will start on `http://localhost:8283`

#### 2. Use letta-code to interact with DSF agent

```bash
# In ~/Development/letta-code directory
cd ~/Development/letta-code

# Start the CLI/TUI (it will connect to the running Letta server)
bun run dev
```

#### 3. Stop everything

```bash
# Stop Letta server
cd ~/Development/letta
docker compose -f dev-compose.yaml down
```

</details>

## Architecture

```
┌─────────────────┐
│   letta-code    │  (UI Layer - TypeScript/Bun)
│   (CLI/TUI)     │  - User interface
│                 │  - world_manager tool (save/load/diff)
│                 │  - World storage (.dsf/worlds/*.json)
└────────┬────────┘
         │
         │ HTTP/WebSocket
         │
┌────────▼────────┐
│   dsf-agent     │  (Agent Logic - Python)
│  (Letta Client) │  - DSF system prompt
│                 │  - Agent configuration
│                 │  - Usage examples
└────────┬────────┘
         │
         │ Letta Client Library
         │
┌────────▼────────┐
│  Letta Server   │  (Platform - Python)
│   (localhost)   │  - Agent execution
│                 │  - Evaluation tools ✨ NEW
│                 │  - LLM calls (Anthropic)
└─────────────────┘
```

See [docs/architecture.md](docs/architecture.md) for detailed documentation.

## Setup

### Prerequisites

- Docker & docker-compose
- Letta repo with evaluation-tools branch
- Anthropic API key (for Claude models)
- Optional: letta-code for enhanced UI

### Configuration

Add your API key to Letta's .env file:

```bash
# Create/edit ~/Development/letta/.env
echo "ANTHROPIC_API_KEY=your_key_here" >> ~/Development/letta/.env
```

**Note**: No configuration needed in dsf-agent repo itself! Everything is configured in the Letta server.

## Usage

Just use letta-code normally! The DSF agent with evaluation tools is available automatically.

```bash
# Start everything
cd ~/Development/dsf-agent
./start.sh

# Say yes to starting letta-code
# Then use letta-code CLI as usual
# Your DSF system prompt and evaluation tools are active!
```

The agent will automatically have access to:
- Your custom DSF system prompt (from prompts.py)
- All 4 evaluation tools from Letta platform
- Research tools (web_search, run_code)
- Memory system
- World manager (via letta-code)

## Available Tools

### Evaluation Tools (from Letta platform) ✨

- **`assess_output_quality(content, rubric, type)`** - LLM-as-judge quality assessment
  - Check world quality against custom rubrics
  - Returns: score, reasoning, strengths, improvements, meets_criteria

- **`check_logical_consistency(content, rules, format)`** - Find contradictions
  - Verify world rules don't contradict each other
  - Returns: consistent, contradictions (elements, description, severity), checks_performed

- **`compare_versions(current, previous, criteria)`** - Measure improvement
  - See if iterations actually improved the world
  - Returns: improved, changes, better_aspects, worse_aspects, recommendation

- **`analyze_information_gain(after, before, metric)`** - Assess novelty
  - Check if new iteration added genuinely new depth
  - Returns: information_gain (0-1), new_facts, insights, significance

### Research & Validation Tools

- **`web_search`** - Research real science and technology
- **`run_code`** - Execute simulations and calculations to verify plausibility
- **`memory`** - Track world state across iterations
- **`conversation_search`** - Search past interactions

### World Management (via letta-code)

- **`world_manager`** - Save/load/diff worlds (accessed through letta-code)

## Design Principles

1. **Tools not workflows** - Agent decides when to evaluate, not a fixed sequence
2. **Parameters not hard-coding** - Rubrics and criteria as inputs, not hardcoded rules
3. **Evaluation over prescription** - Return feedback, agent decides action
4. **Scale with better models** - Better LLMs = better judgment, not more rules

See [.planning/letta-experiments/agent_design_philosophy.md](.planning/letta-experiments/agent_design_philosophy.md) for full philosophy.

## Testing the Stack

To test everything works:

1. **Add your API key**:
   ```bash
   echo "ANTHROPIC_API_KEY=your_key_here" >> ~/Development/letta/.env
   ```

2. **Start the stack**:
   ```bash
   cd ~/Development/dsf-agent
   ./start.sh
   # Say yes to starting letta-code
   ```

3. **Use letta-code normally**:
   - The DSF agent is active with your custom prompt
   - Evaluation tools are available automatically
   - Just chat and build worlds as usual!

## Status

- ✅ Phase 0: Repository setup
- ✅ Phase 1: Evaluation tools in Letta platform
- ✅ Phase 4: Basic DSF agent implementation
- ⏳ Phase 2: Simulation tools (TBD)
- ⏳ Additional examples and tests (TBD)

## Documentation

- [Architecture](docs/architecture.md)
- [Implementation Plan](.planning/letta-experiments/IMPLEMENTATION_PLAN.md)
- [Agent Design Philosophy](.planning/letta-experiments/agent_design_philosophy.md)
- [Tool Designs](.planning/letta-experiments/generic_eval_abm_tools_design.md)

## Contributing

This is a reference implementation. Feel free to adapt for your own use cases!

## License

MIT
