# DSF Agent - Deep Sci-Fi World Building

A reference implementation of an agent that uses Letta's evaluation tools to build logically consistent, deeply researched science fiction worlds.

## Philosophy

**Tools over workflows. Evaluation over prescription. Scale with better models.**

This agent demonstrates how to use generic Letta platform tools for specialized creative work. Rather than hard-coding a worldbuilding workflow, the agent has access to evaluation tools and decides when and how to use them based on context.

## Features

- **Self-Evaluating**: Agent can assess its own work using `assess_output_quality`
- **Consistency Checking**: Find logical contradictions with `check_logical_consistency`
- **Iterative Improvement**: Measure progress with `compare_versions` and `analyze_information_gain`
- **Deep Research**: Use web search and code execution to verify scientific plausibility
- **World Management**: Save, load, and track world iterations (via letta-code)

## Quick Start

### Easy Way: Use the Startup Script

```bash
cd ~/Development/dsf-agent

# Set your API key
export ANTHROPIC_API_KEY=your_key_here

# Start everything (Letta server + optional letta-code UI)
./start.sh

# When done, stop everything
./stop.sh
```

The script will:
1. ✓ Check prerequisites (Docker, API keys)
2. ✓ Switch to evaluation-tools branch
3. ✓ Build and start Letta server with Docker
4. ✓ Wait for server to be ready
5. ✓ Optionally start letta-code UI
6. ✓ Show you how to test DSF agent

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

#### 2. Run DSF Agent

```bash
# In ~/Development/dsf-agent directory
cd ~/Development/dsf-agent

# Install dependencies
pip install letta-client python-dotenv

# Set up your Anthropic API key
export ANTHROPIC_API_KEY=your_key_here

# Run the example
python examples/simple_world.py
```

#### 3. (Optional) Use letta-code UI

```bash
# In ~/Development/letta-code directory
cd ~/Development/letta-code

# Start the CLI/TUI
bun run dev

# The CLI will connect to your local Letta server
# and provide an enhanced UI for interacting with DSF agent
```

#### Stop everything

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

- Python 3.10+
- Letta server with evaluation-tools branch
- Anthropic API key (for Claude models)

### Installation

```bash
# Clone the repository (if not already)
cd ~/Development/dsf-agent

# Install dependencies
pip install letta-client pydantic python-dotenv
```

### Configuration

Create a `.env` file with:

```bash
# API Keys
ANTHROPIC_API_KEY=your_anthropic_key_here

# Letta Server (optional, defaults shown)
LETTA_SERVER_URL=http://localhost:8283
LETTA_API_KEY=  # Only needed for non-local servers
```

## Usage

### Programmatic Usage

```python
from agents.dsf_agent import DSFAgent

# Connect to local Letta server
dsf = DSFAgent(base_url="http://localhost:8283")
dsf.connect()

# Create agent with DSF system prompt
agent = dsf.create_agent(
    name="dsf-worldbuilder",
    model="claude-sonnet-4-5-20250929"
)

# Create a world
response = dsf.send_message(
    "I want to create a hard sci-fi world about a generation ship "
    "traveling to Proxima Centauri. Focus on the closed ecosystem "
    "and how society evolves over 3 generations."
)

# Agent will use evaluation tools as needed:
# - assess_output_quality() to check world quality
# - check_logical_consistency() to find contradictions
# - compare_versions() when iterating
# - analyze_information_gain() to measure novelty
```

### Running Examples

```bash
# Simple world creation
python examples/simple_world.py

# TBD: More examples coming
# python examples/iterative_refinement.py
# python examples/character_development.py
```

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

1. **Start Letta server** (with evaluation tools):
   ```bash
   cd ~/Development/letta
   git checkout evaluation-tools
   letta server
   ```

2. **Run DSF agent example**:
   ```bash
   cd ~/Development/dsf-agent
   python examples/simple_world.py
   ```

3. **Verify evaluation tools work**:
   - Agent should create world options
   - Agent can use `assess_output_quality()` to self-evaluate
   - Agent can use `check_logical_consistency()` to find contradictions

4. **(Optional) Test with letta-code UI**:
   ```bash
   cd ~/Development/letta-code
   bun run dev
   ```

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
