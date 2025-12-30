# DSF Agent Architecture

## Overview

DSF Agent is a reference implementation showing how to use Letta's generic evaluation and simulation tools for creative world-building.

## Components

### Agents (`agents/`)

- **`dsf_agent.py`**: Main agent class that uses Letta client
- **`prompts.py`**: System prompts and instructions

### Tools (`tools/`)

Custom tools if needed. Currently empty - using Letta platform tools.

### Schemas (`schemas/`)

- **`world.py`**: World data structure definitions

### Examples (`examples/`)

Usage examples demonstrating tool usage patterns.

## Tool Usage

DSF Agent uses Letta platform tools (not custom implementations):

### Evaluation Tools

1. **`assess_output_quality(content, rubric, type)`**
   - Usage: Check world quality against DSF rubrics
   - Example: `assess_output_quality(world, "consistent, abstract, deep", "json")`

2. **`check_logical_consistency(content, rules, format)`**
   - Usage: Find contradictions in world rules
   - Example: `check_logical_consistency(world, format="json")`

3. **`compare_versions(current, previous, criteria)`**
   - Usage: Measure improvement between world iterations
   - Example: `compare_versions(world_v2, world_v1, "depth, abstraction")`

4. **`analyze_information_gain(after, before, metric)`**
   - Usage: Assess novelty of changes
   - Example: `analyze_information_gain(world_v2, world_v1, "novelty")`

### Simulation Tools

5. **`simulate_mechanics(scenario, context, steps)`**
   - Usage: Test world rules with Mesa ABM
   - Example: `simulate_mechanics("station with interface failures", world, 50)`

6. **`simulate_interactions(scenario, agents, rounds)`**
   - Usage: Explore character dynamics with LLM roleplay
   - Example: `simulate_interactions("5 characters react to crisis", agents, 5)`

## Integration with letta-code

World storage remains in `letta-code/.dsf/worlds/`:
- DSF agent references this via file paths
- `world_manager` tool in letta-code handles save/load/diff
- Clean separation: letta-code = UI, dsf-agent = business logic

## Design Philosophy

See [.planning/letta-experiments/agent_design_philosophy.md](../.planning/letta-experiments/agent_design_philosophy.md)

Key principles:
- Tools not workflows
- Evaluation over prescription
- Scale with better models
