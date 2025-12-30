# DSF Agent - Deep Sci-Fi World Building

A reference implementation of an agent that uses Letta's evaluation and simulation tools to build logically consistent, deeply researched science fiction worlds.

## Philosophy

**Tools over workflows. Evaluation over prescription. Scale with better models.**

Based on the Bitter Lesson: methods that leverage computation and learning scale better than methods that bake in human knowledge.

## What This Is

DSF Agent demonstrates how to use Letta's generic evaluation and simulation tools for creative world-building:

- **Evaluation Tools**: Self-assess quality, find contradictions, measure improvement
- **Simulation Tools**: Test mechanics with ABM, explore social dynamics with LLM roleplay
- **Agent-Directed**: No prescribed workflows, agent chooses when/if to use tools

## Quick Start

```bash
# Install dependencies
pip install -e .

# Set up environment
cp .env.example .env
# Edit .env with your LETTA_API_KEY

# Create a simple world
python examples/simple_world.py
```

## Architecture

```
dsf-agent/
├── agents/          # DSF agent setup and system prompts
├── tools/           # Custom tool definitions (if needed)
├── examples/        # Usage examples
├── schemas/         # World data structures
├── tests/           # Tests
└── .planning/       # Design documents and implementation plan
```

## Key Features

### Evaluation-Driven Quality

- **Self-assessment**: Agent checks its own work
- **Iterative refinement**: Improve based on feedback
- **Multiple criteria**: Consistency, depth, abstraction, novelty

### Simulation-Based Testing

- **Mechanical simulation**: Test world rules with Mesa ABM
- **Social exploration**: Explore character dynamics with LLM roleplay
- **Emergent discovery**: Find non-obvious patterns

### Principled Design

- **Abstract roles**: "The Navigator" not "John Smith"
- **Logical consistency**: No contradictions in world rules
- **Deep research**: Conceptual connections, not surface facts

## Documentation

- [Implementation Plan](.planning/letta-experiments/IMPLEMENTATION_PLAN.md)
- [Agent Design Philosophy](.planning/letta-experiments/agent_design_philosophy.md)
- [Tool Designs](.planning/letta-experiments/generic_eval_abm_tools_design.md)

## Status

**Phase 0: Repository Setup** ✅ Complete
**Phase 1: Eval Tools** ⏳ In Progress (in letta repo)
**Phase 4: DSF Agent** ⏳ Waiting for Phase 1

See [IMPLEMENTATION_PLAN.md](.planning/letta-experiments/IMPLEMENTATION_PLAN.md) for full roadmap.

## Contributing

This is a reference implementation for Letta's evaluation and simulation tools. Contributions welcome!

1. Follow the Bitter Lesson: tools not workflows
2. Keep it generalizable (not DSF-specific)
3. Demonstrate best practices for tool usage

## License

MIT
