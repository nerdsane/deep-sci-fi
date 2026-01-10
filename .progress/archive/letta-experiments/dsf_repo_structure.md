# DSF Agent Repository Structure

When going the custom tools route (via letta-client SDK), here's where your code lives:

## Folder Structure

```
dsf-agent/                          # Your new repo
├── README.md
├── pyproject.toml                  # Dependencies (letta-client, etc.)
├── .env.example                    # Environment variables template
│
├── tools/                          # Custom tool implementations
│   ├── __init__.py
│   ├── evaluations.py              # Evaluation tools (verify_consistency, etc.)
│   ├── world_management.py         # World save/load/diff tools
│   ├── simulation.py               # ABM simulation tool
│   └── research.py                 # Research tool
│
├── agents/                         # Agent setup and configuration
│   ├── __init__.py
│   ├── dsf_agent.py               # DSF agent creator/manager
│   └── prompts.py                 # System prompts for agent
│
├── schemas/                        # Data structures
│   ├── __init__.py
│   ├── world.py                   # World data schema
│   ├── simulation_result.py       # Simulation output schema
│   └── evaluation_result.py       # Evaluation output schema
│
├── services/                       # Business logic
│   ├── __init__.py
│   ├── world_builder.py           # World building orchestration
│   ├── evaluator.py               # External evaluation runner
│   └── storage.py                 # World persistence
│
├── cli/                           # Command-line interface (optional)
│   ├── __init__.py
│   └── main.py                    # CLI commands
│
├── examples/                       # Usage examples
│   ├── simple_world.py            # Basic world creation
│   ├── iterative_refinement.py   # Iterative world building
│   └── batch_evaluation.py       # Batch eval of multiple worlds
│
├── tests/                         # Tests
│   ├── test_tools.py
│   ├── test_world_building.py
│   └── test_evaluations.py
│
└── outputs/                       # Generated outputs (gitignored)
    ├── worlds/                    # Saved worlds
    ├── evaluations/               # Eval results
    └── stories/                   # Generated stories
```

## Key Files Explained

### `tools/evaluations.py` - Your Custom Eval Tools

```python
"""
Evaluation tools for DSF agent.

These are registered as custom tools via letta-client API.
"""

def verify_consistency(world: dict) -> dict:
    """
    Check world for logical contradictions.

    This function source code will be sent to Letta API.
    Agent can call this tool during execution.

    Args:
        world: World data structure

    Returns:
        Consistency check results
    """
    import json

    # Your implementation here
    contradictions = []

    # Example: Check if FTL travel exists but rules forbid it
    has_ftl = any('FTL' in str(e) for e in world.get('entities', []))
    forbids_ftl = any('no FTL' in str(r) for r in world.get('rules', []))

    if has_ftl and forbids_ftl:
        contradictions.append({
            'elements': ['entities', 'rules'],
            'description': 'World has FTL entities but rules forbid FTL',
            'severity': 'major'
        })

    return {
        'consistent': len(contradictions) == 0,
        'contradictions': contradictions,
        'edge_cases_checked': 1
    }


def assess_depth(content: str, content_type: str) -> dict:
    """Evaluate depth of research/analysis"""
    # Implementation
    pass


def check_abstraction(world: dict) -> dict:
    """Check for concrete names vs abstract roles"""
    # Implementation
    pass


# Export tool definitions for registration
EVAL_TOOLS = {
    'verify_consistency': verify_consistency,
    'assess_depth': assess_depth,
    'check_abstraction': check_abstraction,
}
```

### `tools/world_management.py` - World Persistence Tools

```python
"""World save/load/diff tools"""

def save_world(world: dict, checkpoint_name: str) -> dict:
    """
    Save world to storage.

    Note: This will be executed in Letta's sandbox, so it needs
    to use available storage mechanisms (could be via API calls
    to your service).
    """
    import json
    import os

    # In sandbox, might need to save via HTTP to your service
    # Or use Letta's file storage if configured

    filepath = f"/tmp/worlds/{checkpoint_name}.json"
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with open(filepath, 'w') as f:
        json.dump(world, f, indent=2)

    return {
        'saved': True,
        'path': filepath,
        'timestamp': str(datetime.now())
    }


def load_world(checkpoint_name: str) -> dict:
    """Load world from storage"""
    pass


def diff_worlds(checkpoint1: str, checkpoint2: str) -> dict:
    """Compare two world states"""
    pass


WORLD_TOOLS = {
    'save_world': save_world,
    'load_world': load_world,
    'diff_worlds': diff_worlds,
}
```

### `agents/dsf_agent.py` - Agent Setup

```python
"""
DSF Agent creator and manager.

This is where you set up your agent with custom tools.
"""

from letta_client import Letta
import os
import inspect

from tools.evaluations import EVAL_TOOLS
from tools.world_management import WORLD_TOOLS
from agents.prompts import DSF_SYSTEM_PROMPT


class DSFAgent:
    """Deep Sci-Fi World Building Agent"""

    def __init__(self, api_key: str = None):
        self.client = Letta(api_key=api_key or os.getenv('LETTA_API_KEY'))
        self.agent_id = None
        self.tool_ids = []

    def setup(self):
        """Register tools and create agent"""
        print("Registering custom tools...")

        # 1. Register all eval tools
        for tool_name, tool_func in EVAL_TOOLS.items():
            tool = self.client.tools.create(
                source_code=inspect.getsource(tool_func),
                description=tool_func.__doc__,
                tags=['dsf', 'evaluation']
            )
            self.tool_ids.append(tool.name)
            print(f"  ✓ Registered {tool_name}")

        # 2. Register world management tools
        for tool_name, tool_func in WORLD_TOOLS.items():
            tool = self.client.tools.create(
                source_code=inspect.getsource(tool_func),
                description=tool_func.__doc__,
                tags=['dsf', 'world']
            )
            self.tool_ids.append(tool.name)
            print(f"  ✓ Registered {tool_name}")

        # 3. Create agent with all tools
        print("\nCreating DSF agent...")
        agent = self.client.agents.create(
            model='openai/gpt-4.1',
            embedding='openai/text-embedding-3-small',
            memory_blocks=[
                {
                    'label': 'human',
                    'value': 'User wants to build deep sci-fi worlds'
                },
                {
                    'label': 'persona',
                    'value': DSF_SYSTEM_PROMPT
                }
            ],
            tools=self.tool_ids + [
                'send_message',          # Built-in Letta tools
                'memory',
                'conversation_search',
                'archival_memory_insert',
                'archival_memory_search',
            ]
        )

        self.agent_id = agent.id
        print(f"  ✓ Agent created: {self.agent_id}")

        return agent

    def create_world(self, prompt: str):
        """Create a world from a prompt"""
        response = self.client.agents.messages.create(
            agent_id=self.agent_id,
            input=prompt
        )

        return response

    def get_world(self, checkpoint_name: str):
        """Retrieve a saved world"""
        # Implementation depends on your storage strategy
        pass


# Usage example
if __name__ == '__main__':
    agent = DSFAgent()
    agent.setup()

    response = agent.create_world(
        "Create a world about post-scarcity civilization with memory limitations"
    )

    print(response)
```

### `agents/prompts.py` - System Prompts

```python
"""System prompts for DSF agent"""

DSF_SYSTEM_PROMPT = """
You are a Deep Sci-Fi world building agent.

Your goal: Create logically consistent, deeply researched science fiction worlds.

CORE PRINCIPLES:

1. Logical Consistency
   - No contradictions in world rules
   - All entity properties follow from rules
   - Use verify_consistency() to check your work

2. Abstraction
   - Use roles, not names: "The Magistrate" not "John Smith"
   - Use functions, not places: "The Trading Hub" not "Boston"
   - Invent culture: "The Renewal" not "Christmas"
   - Use check_abstraction() to verify

3. Deep Research
   - Go beyond surface facts
   - Connect non-obvious concepts
   - Build conceptual models
   - Use assess_depth() to evaluate

4. Self-Evaluation
   - Check your work before finalizing
   - Iterate based on eval feedback
   - Decide when to go deeper vs. move on

AVAILABLE TOOLS:

Evaluation:
- verify_consistency(world) - Check for contradictions
- assess_depth(content, type) - Evaluate research depth
- check_abstraction(world) - Find concrete names/culture

World Management:
- save_world(world, name) - Save checkpoint
- load_world(name) - Load checkpoint
- diff_worlds(name1, name2) - Compare versions

You decide WHEN and IF to use these tools.
No prescribed workflow - just quality criteria.
"""
```

### `pyproject.toml` - Dependencies

```toml
[project]
name = "dsf-agent"
version = "0.1.0"
description = "Deep Sci-Fi world building agent using Letta"
requires-python = ">=3.10"

dependencies = [
    "letta-client>=0.5.0",
    "pydantic>=2.0.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "black>=23.0.0",
    "ruff>=0.1.0",
]

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_module"
```

### `.env.example`

```bash
# Letta API Configuration
LETTA_API_KEY=your_api_key_here

# Use hosted Letta or self-hosted
LETTA_BASE_URL=https://api.letta.com  # or http://localhost:8283

# OpenAI API Key (if needed for evals)
OPENAI_API_KEY=your_openai_key_here
```

## Where Each Repo Lives on Your Machine

```
~/Development/
├── letta/                    # Forked Letta platform
│   └── (only edit if contributing platform features)
│
├── letta-code/              # Forked Letta CLI
│   ├── .planning/           # Your design docs (keep these!)
│   └── (only edit if contributing CLI features)
│
└── dsf-agent/               # Your DSF application ⭐ CREATE THIS
    ├── tools/               # Custom tools (eval, world management)
    ├── agents/              # Agent setup
    └── ...                  # Rest of structure above
```

## How They Interact

```
┌─────────────────────────────────────────────────────────────┐
│  dsf-agent/ (Your Application)                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Your Code:                                         │    │
│  │  - tools/evaluations.py                            │    │
│  │  - agents/dsf_agent.py                             │    │
│  │  - Uses: letta-client SDK                          │    │
│  └────────────────────────────────────────────────────┘    │
│                          │                                   │
│                          │ HTTP/REST API                     │
│                          ▼                                   │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Letta Server (from letta/ repo)                   │    │
│  │  - Runs your custom tools in sandbox               │    │
│  │  - Manages agent state                             │    │
│  │  - Stores conversations                            │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  letta-code/ (Optional - for CLI interface)       │    │
│  │  - Interactive chat with agent                      │    │
│  │  - Only if you want CLI instead of Python API      │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start Commands

```bash
# 1. Create your DSF agent repo
cd ~/Development
mkdir dsf-agent
cd dsf-agent

# 2. Initialize project
python -m venv venv
source venv/bin/activate
pip install letta-client pydantic python-dotenv

# 3. Create folder structure (from above)
mkdir -p tools agents schemas services cli examples tests outputs/{worlds,evaluations,stories}

# 4. Copy design docs from letta-code
cp -r ~/Development/letta-code/.planning ./docs/planning

# 5. Start coding!
# Create tools/evaluations.py with your eval tools
# Create agents/dsf_agent.py with agent setup
# etc.
```
