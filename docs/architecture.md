# DSF Agent Architecture

## Overview

DSF Agent is a reference implementation showing how to use Letta's generic evaluation tools for deep sci-fi world-building. It demonstrates the "tools over workflows" philosophy - the agent has access to evaluation tools and decides when and how to use them.

## System Architecture

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
│                 │  - Evaluation tools
│                 │  - LLM calls (Anthropic)
└─────────────────┘
```

## Components

### Agents (`agents/`)

- **`dsf_agent.py`**: Main agent class using Letta client
  - Connects to local Letta server
  - Creates agents with DSF system prompt
  - Manages agent lifecycle

- **`prompts.py`**: DSF system prompt
  - Worldbuilding guidance
  - Quality standards
  - Evaluation tool usage instructions

### Tools

**Platform Tools** (from Letta server):
- `assess_output_quality()` - LLM-as-judge quality assessment
- `check_logical_consistency()` - Find logical contradictions
- `compare_versions()` - Measure improvement between versions
- `analyze_information_gain()` - Assess novelty of changes

**External Tools** (from letta-code):
- `world_manager` - Save/load/diff/update worlds (accessed via letta-code)

### Schemas (`schemas/`)

- **`world.py`**: World data structure definitions (matches letta-code types)

### Examples (`examples/`)

- **`simple_world.py`**: Basic world creation example
- More examples TBD (iterative refinement, simulation testing, etc.)

## How It Works

1. **User** interacts via `letta-code` CLI/TUI
2. **letta-code** connects to DSF agent running on Letta server
3. **DSF agent** has access to:
   - DSF system prompt (worldbuilding guidance)
   - Evaluation tools (assess quality, check consistency, etc.)
   - Memory system (track world state)
   - Research tools (web_search, run_code)
4. **Agent decides** when to use evaluation tools based on context
5. **World storage** managed by letta-code's world_manager tool
6. **Evaluation results** inform agent's decisions about quality

## Tool Usage Philosophy

### Evaluation Tools

DSF Agent uses Letta platform evaluation tools:

1. **`assess_output_quality(content, rubric, type)`**
   - Usage: Check world quality against custom rubrics
   - Example: `assess_output_quality(world, "consistent, abstract, deep, researched", "json")`
   - Returns: score, reasoning, strengths, improvements, meets_criteria

2. **`check_logical_consistency(content, rules, format)`**
   - Usage: Find contradictions in world rules
   - Example: `check_logical_consistency(world, format="json")`
   - Returns: consistent, contradictions (elements, description, severity), checks_performed

3. **`compare_versions(current, previous, criteria)`**
   - Usage: Measure improvement between iterations
   - Example: `compare_versions(world_v2, world_v1, "depth, abstraction, consistency")`
   - Returns: improved, changes, better_aspects, worse_aspects, recommendation

4. **`analyze_information_gain(after, before, metric)`**
   - Usage: Assess novelty of changes
   - Example: `analyze_information_gain(world_v2, world_v1, "novelty")`
   - Returns: information_gain (0-1), new_facts, insights, significance

### World Management (via letta-code)

World storage remains in `letta-code/.dsf/worlds/`:
- DSF agent can reference worlds via file paths
- `world_manager` tool in letta-code handles save/load/diff
- Clean separation: letta-code = UI + storage, dsf-agent = business logic

## Design Philosophy

See [.planning/letta-experiments/agent_design_philosophy.md](../.planning/letta-experiments/agent_design_philosophy.md)

Key principles:
- **Tools not workflows** - Agent chooses when/if to use evaluation tools
- **Evaluation over prescription** - Return feedback, agent decides action
- **Scale with better models** - Better judgment, not more rules
- **Parameters not hard-coding** - Rubrics and criteria as inputs

## Running the Stack Locally

See [../README.md](../README.md) for setup instructions.

Quick overview:
1. Start Letta server: `letta server`
2. Run DSF agent: `python examples/simple_world.py`
3. Optional: Use letta-code CLI for enhanced UI
