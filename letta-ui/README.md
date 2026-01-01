# Letta UI

Open source observability dashboard for Letta agents.

## Features

- **Agents**: View and manage all Letta agents
- **Runs**: Monitor execution runs with step details
- **Trajectories**: Explore execution traces for continual learning
- **Resources**: Memory blocks, tools, MCP servers (coming soon)
- **Messages**: Conversation thread visualization (coming soon)
- **Settings**: Configuration management (coming soon)

## Tech Stack

- React + TypeScript
- Radix UI (accessible components)
- Tailwind CSS (custom earth-tone palette)
- Bun (runtime + dev server)

## Development

```bash
# Install dependencies
bun install

# Start dev server (with HMR)
bun run dev

# Type check
bun run typecheck

# Build for production
bun run build
```

The dev server runs at http://localhost:3000 and proxies API requests to the Letta server at http://localhost:8283.

## Configuration

Set `LETTA_BASE_URL` to point to your Letta server:

```bash
export LETTA_BASE_URL=http://localhost:8283
bun run dev
```

## Design Philosophy

This UI avoids generic "AI dashboard" aesthetics with:
- JetBrains Mono for headers (technical yet refined)
- Warm earth-tone palette (sand, rust, sage, midnight)
- Asymmetric layouts with intentional spacing
- Smooth micro-interactions and animations
- Card-based composition with subtle shadows

## API Integration

The dashboard connects to Letta's REST API endpoints:
- `/v1/agents/` - Agent management
- `/v1/runs/` - Execution monitoring
- `/v1/trajectories/` - Continual learning data
- `/v1/blocks/` - Memory blocks
- `/v1/tools/` - Tool registry
- `/v1/mcp-servers/` - MCP server integration
