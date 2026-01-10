# ABM Implementation Approaches

## Approach A: Real Agent-Based Modeling (Mesa)

### How It Works

**Step 1: LLM translates scenario → simulation config**

```python
# Agent calls:
simulate_scenario(
    "Station with 50 people using neural interfaces. "
    "Interfaces sometimes malfunction (10% chance per timestep). "
    "People try to communicate emotional states."
)

# LLM translates to:
{
    "agent_types": [
        {
            "type": "Person",
            "count": 50,
            "behaviors": [
                "try_communicate_emotion",
                "react_to_interface_state"
            ],
            "properties": {
                "has_interface": true,
                "interface_working": true,
                "emotional_state": "random"
            }
        }
    ],
    "environment_rules": [
        "interface_malfunction_rate": 0.1,
        "communication_requires_working_interface": true
    ],
    "timesteps": 50,
    "measure": ["communication_success_rate", "frustration_levels"]
}
```

**Step 2: Run actual ABM simulation**

```python
from mesa import Agent, Model
from mesa.time import RandomActivation
from mesa.datacollection import DataCollector

class PersonAgent(Agent):
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        self.interface_working = True
        self.emotional_state = random.choice(['calm', 'excited', 'frustrated'])
        self.communication_attempts = 0
        self.successful_communications = 0

    def step(self):
        # Check for interface malfunction
        if random.random() < 0.1:
            self.interface_working = False

        # Try to communicate
        self.communication_attempts += 1
        if self.interface_working:
            # Find another person to communicate with
            other = random.choice(self.model.schedule.agents)
            if other.interface_working:
                self.successful_communications += 1
                # Emotional state affects communication quality
                if self.emotional_state == 'frustrated':
                    # Frustration cascades
                    other.emotional_state = 'frustrated'
        else:
            # Failed communication increases frustration
            self.emotional_state = 'frustrated'

class StationModel(Model):
    def __init__(self, num_people, malfunction_rate):
        self.num_agents = num_people
        self.schedule = RandomActivation(self)

        # Create agents
        for i in range(num_people):
            agent = PersonAgent(i, self)
            self.schedule.add(agent)

        self.datacollector = DataCollector(
            model_reporters={
                "Working_Interfaces": lambda m: sum([a.interface_working for a in m.schedule.agents]),
                "Frustrated_People": lambda m: sum([a.emotional_state == 'frustrated' for a in m.schedule.agents]),
                "Success_Rate": lambda m: sum([a.successful_communications for a in m.schedule.agents]) /
                                          sum([a.communication_attempts for a in m.schedule.agents])
            }
        )

    def step(self):
        self.datacollector.collect(self)
        self.schedule.step()

# Run simulation
model = StationModel(num_people=50, malfunction_rate=0.1)
for _ in range(50):
    model.step()

results = model.datacollector.get_model_vars_dataframe()
```

**Step 3: LLM analyzes results for emergent behavior**

```python
# Simulation results:
{
    "timestep_data": {
        "working_interfaces": [50, 48, 45, 42, ...],  # Degradation over time
        "frustrated_people": [5, 8, 15, 28, ...],     # Cascade effect
        "success_rate": [0.85, 0.80, 0.65, 0.40, ...] # Declining
    }
}

# LLM synthesizes:
{
    "outcome": "Communication system degraded rapidly. By timestep 30, \
                frustration cascaded through the population.",
    "emergent_behaviors": [
        "Frustration cascade: Once interfaces started failing, frustration \
         spread person-to-person faster than the technical failures.",
        "Tipping point at ~20% malfunction rate: System resilience collapsed \
         when 10 interfaces failed simultaneously."
    ],
    "interactions": [
        "Failed communication attempts increased frustration, which made \
         subsequent communications less effective even with working interfaces.",
        "People avoided communicating with visibly frustrated individuals, \
         creating isolation clusters."
    ],
    "surprises": [
        "Emotional contagion was more impactful than technical failure rate.",
        "System failure was non-linear: gradual decline suddenly collapsed."
    ],
    "suggests": [
        "In this world, emotional states propagate through the network \
         independently of interface status.",
        "Need redundancy or emotional regulation mechanisms to prevent cascade."
    ]
}
```

**Pros:**
- ✅ Real emergence (not hallucinated by LLM)
- ✅ Reproducible (same config → same results)
- ✅ Fast (50 timesteps runs in <1 second)
- ✅ Quantitative data (graphs, metrics)

**Cons:**
- ❌ Requires translating NL → code (LLM might miss nuances)
- ❌ Limited to simple agent behaviors
- ❌ Less flexible than pure LLM

---

## Approach B: LLM Roleplaying ABM

### How It Works

**Step 1: Agent calls simulation**

```python
simulate_scenario(
    "Station with 50 people using neural interfaces. "
    "Interfaces sometimes malfunction. "
    "People try to communicate emotional states."
)
```

**Step 2: LLM simulates multiple agents**

```python
# Initial prompt for each simulated agent:
agent_prompts = []
for i in range(50):
    agent_prompts.append(f"""
You are Person #{i} on a space station.

YOUR STATE:
- You have a neural interface (currently: {'working' if random() > 0.1 else 'broken'})
- Your emotional state: {random.choice(['calm', 'excited', 'frustrated'])}

RULES:
- You can communicate emotions through your interface (if working)
- If your interface is broken, you feel frustrated
- You can see other people's emotional states (if their interfaces work)

CURRENT SITUATION (Timestep 0):
- You're in the common area
- You see 49 other people

What do you do?
""")

# Run multiple rounds
for timestep in range(10):  # Fewer steps because LLM is slow/expensive
    responses = []
    for prompt in agent_prompts:
        # Each agent gets a turn
        response = await call_llm(prompt, model="claude-haiku-4")
        responses.append(response)

    # Update prompts based on interactions
    # (complex logic to track who interacted with whom)
    agent_prompts = update_agent_contexts(agent_prompts, responses)
```

**Step 3: Synthesize results**

```python
# LLM analyzes all agent behaviors:
synthesis_prompt = f"""
I simulated 50 people on a station over 10 timesteps.

AGENT BEHAVIORS:
{json.dumps(all_responses, indent=2)}

What emergent patterns occurred?
What was surprising?
What does this reveal about the scenario?
"""

result = await call_llm(synthesis_prompt, model="claude-sonnet-4")
```

**Pros:**
- ✅ Very flexible (handles complex social dynamics)
- ✅ Natural language all the way through
- ✅ Can handle nuanced behaviors (emotions, social context)
- ✅ No need for formal behavior encoding

**Cons:**
- ❌ Slow (50 agents × 10 timesteps = 500 LLM calls)
- ❌ Expensive ($0.25 per call × 500 = $125 per simulation!)
- ❌ Less emergent (LLM might hallucinate patterns)
- ❌ Not reproducible (different runs → different results)
- ❌ Risk: LLM "knows" what "should" happen, biases simulation

---

## Approach C: Hybrid (Recommended)

### How It Works

**Use real ABM for mechanics, LLM for complex decisions**

```python
class PersonAgent(Agent):
    def step(self):
        # Simple mechanics: agent-based model
        if random.random() < 0.1:
            self.interface_working = False

        # Complex decision: ask LLM
        if not self.interface_working:
            decision = self.ask_llm_for_decision()
            if decision == "seek_help":
                self.seek_engineer()
            elif decision == "isolate":
                self.move_to_private_area()

        # Simple mechanics: agent-based model
        self.try_communicate()

    def ask_llm_for_decision(self):
        # Only call LLM for complex decisions
        # Most behavior is rule-based
        prompt = f"""
You're a person whose neural interface just broke.
Current emotional state: {self.emotional_state}
Nearby people: {len(self.nearby_agents)}

Do you:
A) Seek help from an engineer
B) Try to communicate without interface
C) Isolate yourself in frustration

Choose one: A, B, or C
"""
        response = call_llm(prompt, model="claude-haiku-4")
        return parse_decision(response)
```

**Pros:**
- ✅ Fast (most behavior is ABM, occasional LLM calls)
- ✅ Affordable (10-20 LLM calls per simulation, not 500)
- ✅ Flexible where it matters (complex decisions)
- ✅ Reproducible mechanics with adaptive behavior

**Cons:**
- ❌ More complex to implement
- ❌ Need to decide which behaviors are LLM vs ABM

---

## Comparison Table

| Aspect | Real ABM (Mesa) | LLM Roleplaying | Hybrid |
|--------|----------------|----------------|--------|
| **Speed** | ⚡ <1s | 🐌 1-5 min | ⚡ 5-10s |
| **Cost** | 💰 $0.01 | 💰💰💰 $50-100 | 💰 $1-5 |
| **Emergence** | ✅ Real | ⚠️ Hallucinated | ✅ Real |
| **Flexibility** | ⚠️ Simple behaviors | ✅ Complex behaviors | ✅ Balanced |
| **Reproducible** | ✅ Yes | ❌ No | ⚠️ Mostly |
| **Scale** | ✅ 100s of agents | ❌ 10-20 agents | ✅ 50-100 agents |

---

## Recommendation for Letta Platform

**Start with Approach A (Real ABM)** because:

1. **Light** - Fast, cheap, reproducible
2. **Generalizable** - Works for any domain (LLM translates scenario)
3. **Scalable** - Better models → better scenario translation
4. **Real emergence** - Not hallucinated by LLM

**Can add Approach C (Hybrid) later** if users need more complex agent behaviors.

**Skip Approach B** - Too slow/expensive for platform tool.

---

## Example: Economics Simulation

**User calls:**
```python
simulate_scenario(
    "100 buyers, 50 sellers trading widgets. "
    "Buyers value widgets from $1-$100 (uniform random). "
    "Sellers cost is $20-$80 (uniform random). "
    "Double auction: buyers bid, sellers ask, trades at midpoint."
)
```

**LLM translates to ABM config:**
```python
{
    "agents": [
        {"type": "Buyer", "count": 100, "valuation": "uniform(1, 100)"},
        {"type": "Seller", "count": 50, "cost": "uniform(20, 80)"}
    ],
    "mechanism": "double_auction",
    "timesteps": 20,
    "measure": ["price_convergence", "trade_volume", "surplus"]
}
```

**Real ABM runs:**
- Buyers submit bids based on valuation
- Sellers submit asks based on cost
- Trades happen at midpoint
- Prices adjust based on supply/demand

**Emergent behaviors:**
- Price discovery: converges to ~$50 (equilibrium)
- Early volatility: large price swings at first
- Efficiency: most mutually beneficial trades happen

**LLM synthesizes:**
```
The market quickly found equilibrium around $50, which makes sense given
the overlapping ranges. Interesting: buyers with valuations $20-$50 couldn't
trade (sellers' minimum was $20), creating a gap. About 60% of possible
surplus was captured.

Suggests: In this market design, low-valuation buyers are excluded. A
subsidy or alternative mechanism might improve efficiency.
```

---

## Implementation in Letta

```python
# letta/functions/function_sets/simulation.py

import mesa
from mesa import Agent, Model
from mesa.time import RandomActivation

async def simulate_scenario(
    scenario_description: str,
    context: dict = None,
    focus: str = "emergent_behaviors"
) -> dict:
    # 1. LLM: Translate scenario → ABM config
    config = await translate_scenario_to_config(scenario_description, context)

    # 2. Build Mesa model from config
    model = build_mesa_model(config)

    # 3. Run simulation
    results = run_simulation(model, steps=config.get('timesteps', 50))

    # 4. LLM: Analyze results
    analysis = await analyze_results(
        scenario_description,
        results,
        focus
    )

    return analysis
```

**Key insight**: LLM does the smart work (translation + analysis), Mesa does the mechanical work (simulation). Best of both worlds.
