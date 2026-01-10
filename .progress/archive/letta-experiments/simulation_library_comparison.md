# Simulation Library Comparison for Letta Platform

## The Question

For a future-forward platform like Letta, what simulation library should we use?

## Key Libraries Compared

### 1. Mesa (Agent-Based Modeling)
- **Status**: Active (v3.4.0, Dec 2024)
- **Stars**: 3.3k
- **Type**: Agent-Based Modeling (ABM)
- **Paradigm**: Autonomous agents with behaviors

### 2. SimPy (Discrete Event Simulation)
- **Status**: Active (v4.1, 2024)
- **Stars**: 1.1k
- **Type**: Discrete Event Simulation (DES)
- **Paradigm**: Processes, resources, events

### 3. NetLogo (Classic ABM)
- **Status**: Active but Java-based
- **Type**: ABM with GUI
- **Paradigm**: Agent-based with Logo scripting

### 4. Agents.jl (Julia)
- **Status**: Active, very fast
- **Type**: ABM in Julia
- **Paradigm**: High-performance ABM

### 5. HASH (Commercial)
- **Status**: Active, cloud-based
- **Type**: Multi-paradigm simulation
- **Paradigm**: Visual modeling + code

---

## Mesa vs SimPy: Different Use Cases

### Mesa (Agent-Based Modeling)

**Paradigm**: Autonomous agents with local behaviors → emergent global patterns

**Example: Station Communication Breakdown**
```python
class PersonAgent(Agent):
    def __init__(self, unique_id, model):
        self.interface_working = True
        self.frustration = 0

    def step(self):
        # Each agent acts autonomously
        if not self.interface_working:
            self.frustration += 1

        # Interact with neighbors
        for neighbor in self.model.get_neighbors(self):
            if neighbor.frustration > 5:
                self.frustration += 1  # Emotional contagion

# Emergent behavior: Frustration cascades through network
```

**Good for:**
- Social dynamics (opinion spread, norms, cooperation)
- Markets (buyers/sellers with strategies)
- Ecology (predator/prey, foraging)
- Crowds (pedestrians, evacuation, traffic)
- Organizations (team dynamics, decision-making)

**Key feature**: Emergence - global patterns from local interactions

---

### SimPy (Discrete Event Simulation)

**Paradigm**: Processes compete for resources, events happen in sequence

**Example: Station Communication System**
```python
def person_communication(env, comm_system):
    """A person trying to communicate"""
    print(f'Person arrives at {env.now}')

    # Request communication slot
    with comm_system.request() as req:
        yield req  # Wait in queue

        # Use communication system
        yield env.timeout(random.uniform(1, 3))  # Communication time

    print(f'Person done at {env.now}')

# Setup
env = simpy.Environment()
comm_system = simpy.Resource(env, capacity=10)  # 10 parallel channels

# Generate arrivals
for i in range(100):
    env.process(person_communication(env, comm_system))

env.run(until=100)
# Output: Wait times, utilization, throughput
```

**Good for:**
- Queueing systems (customer service, call centers)
- Manufacturing (assembly lines, production)
- Networks (packet routing, bandwidth)
- Logistics (supply chains, warehouses)
- Healthcare (patient flow, bed allocation)

**Key feature**: Optimization - minimize wait times, maximize throughput

---

## When to Use Each

| Scenario | Mesa (ABM) | SimPy (DES) |
|----------|-----------|-------------|
| **People with emotions interact** | ✅ Yes | ❌ No |
| **Information spreads through network** | ✅ Yes | ❌ No |
| **Market with buyers/sellers** | ✅ Yes | ⚠️ Possible |
| **Customers queue for service** | ❌ No | ✅ Yes |
| **Network packet routing** | ❌ No | ✅ Yes |
| **Manufacturing assembly line** | ❌ No | ✅ Yes |
| **Traffic flow optimization** | ⚠️ Both work | ⚠️ Both work |
| **Resource allocation** | ⚠️ Possible | ✅ Yes |

**Rule of thumb:**
- **Agents with behaviors** → Mesa
- **Processes with resources** → SimPy

---

## What Can Mesa Actually Do? Concrete Examples

### Example 1: Opinion Dynamics

**Scenario**: 100 people with political opinions. People influence neighbors.

```python
from mesa import Agent, Model
from mesa.space import NetworkGrid
from mesa.time import RandomActivation
import networkx as nx

class PersonAgent(Agent):
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        self.opinion = random.uniform(-1, 1)  # -1=left, 1=right

    def step(self):
        # Get neighbors' average opinion
        neighbors = self.model.grid.get_neighbors(self.pos)
        if neighbors:
            avg_opinion = sum(n.opinion for n in neighbors) / len(neighbors)
            # Shift toward neighbors (but not fully)
            self.opinion += 0.1 * (avg_opinion - self.opinion)

class OpinionModel(Model):
    def __init__(self, num_agents):
        self.schedule = RandomActivation(self)

        # Create social network
        G = nx.watts_strogatz_graph(num_agents, k=6, p=0.1)
        self.grid = NetworkGrid(G)

        # Create agents
        for i in range(num_agents):
            agent = PersonAgent(i, self)
            self.schedule.add(agent)
            self.grid.place_agent(agent, i)

    def step(self):
        self.schedule.step()

# Run
model = OpinionModel(100)
for _ in range(50):
    model.step()

# Result: Opinions polarize into clusters or converge to consensus
# Depends on network structure (emergent!)
```

**What emerges:**
- Opinion clusters form
- Polarization or consensus
- Depends on network topology (not explicitly programmed)

---

### Example 2: Market Dynamics

**Scenario**: Buyers and sellers trading. Prices adjust based on supply/demand.

```python
class BuyerAgent(Agent):
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        self.valuation = random.uniform(50, 150)  # What I'll pay
        self.has_item = False

    def step(self):
        if not self.has_item:
            # Look for sellers
            sellers = [a for a in self.model.schedule.agents
                      if isinstance(a, SellerAgent) and a.has_item]
            if sellers:
                seller = random.choice(sellers)
                # Try to negotiate
                if seller.price <= self.valuation:
                    # Trade!
                    self.has_item = True
                    seller.has_item = False
                    self.model.trades.append(seller.price)

class SellerAgent(Agent):
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        self.cost = random.uniform(20, 80)  # My production cost
        self.price = self.cost + random.uniform(10, 50)  # Initial asking
        self.has_item = True

    def step(self):
        # Adjust price based on market
        if self.has_item and self.model.schedule.steps > 5:
            # If no one bought, lower price
            self.price = max(self.cost, self.price * 0.95)

class MarketModel(Model):
    def __init__(self, num_buyers, num_sellers):
        self.schedule = RandomActivation(self)
        self.trades = []

        for i in range(num_buyers):
            self.schedule.add(BuyerAgent(i, self))

        for i in range(num_sellers):
            self.schedule.add(SellerAgent(num_buyers + i, self))

    def step(self):
        self.schedule.step()

# Run
model = MarketModel(100, 50)
for _ in range(50):
    model.step()

# Result: Price discovery! Converges to equilibrium
# Efficiency: Most mutually beneficial trades happen
```

**What emerges:**
- Price discovery (finds equilibrium)
- Some buyers/sellers don't trade (market segmentation)
- Price volatility early, then stability

---

### Example 3: Disease Spread (SIR Model)

**Scenario**: Infected people spread disease to susceptible neighbors.

```python
class PersonAgent(Agent):
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        self.state = "S"  # Susceptible
        self.infection_time = 0

    def step(self):
        if self.state == "S":
            # Check if any neighbor is infected
            neighbors = self.model.grid.get_neighbors(self.pos, include_center=False)
            infected_neighbors = [n for n in neighbors if n.state == "I"]
            # Probability of infection
            infection_prob = 1 - (1 - 0.1) ** len(infected_neighbors)
            if random.random() < infection_prob:
                self.state = "I"
                self.infection_time = 0

        elif self.state == "I":
            self.infection_time += 1
            if self.infection_time > 10:
                self.state = "R"  # Recovered

class DiseaseModel(Model):
    def __init__(self, width, height, initial_infected):
        self.grid = MultiGrid(width, height, torus=True)
        self.schedule = RandomActivation(self)

        # Create agents
        for i in range(width * height):
            agent = PersonAgent(i, self)
            self.schedule.add(agent)
            x = i % width
            y = i // width
            self.grid.place_agent(agent, (x, y))

        # Infect initial agents
        for _ in range(initial_infected):
            agent = random.choice(self.schedule.agents)
            agent.state = "I"

    def step(self):
        self.schedule.step()

# Run
model = DiseaseModel(50, 50, initial_infected=10)
for _ in range(100):
    model.step()

# Result: Epidemic curve! S → I → R over time
# Can vary initial conditions, infection rate, recovery time
```

**What emerges:**
- Epidemic curves (S/I/R over time)
- Spatial patterns (clusters of infection)
- Herd immunity thresholds

---

## Why Not SimPy for Letta?

SimPy is great, but for **different use cases**:

**SimPy is better for:**
```python
# Manufacturing: Parts move through assembly line
def assembly_line(env, part):
    yield env.timeout(5)  # Station 1
    yield env.timeout(3)  # Station 2
    yield env.timeout(7)  # Station 3
    # Output: Total time = 15

# Network: Packets compete for bandwidth
def packet_transmission(env, network):
    with network.request() as req:
        yield req
        yield env.timeout(packet_size / bandwidth)
    # Output: Throughput, latency
```

**Mesa is better for:**
```python
# Social: People with opinions influence each other
class PersonAgent(Agent):
    def step(self):
        # Update opinion based on neighbors
        # Emergent: Opinion clusters form

# Market: Buyers/sellers with strategies
class TraderAgent(Agent):
    def step(self):
        # Decide to buy/sell based on price
        # Emergent: Price discovery
```

**For Letta agents**, we mostly want:
- Social dynamics (emotions, beliefs, behaviors)
- Creative exploration (what if X happens?)
- Emergent patterns (what's non-obvious?)

→ **Mesa fits better**

But we could add SimPy too if users want queuing/logistics sims!

---

## Should We Support Both ABM and LLM Roleplay?

**Answer: YES! They're complementary, not competitive.**

### Two Different Simulation Types

#### Type 1: Mechanical Simulation (Mesa ABM)

**Use case**: Test cause-effect, find equilibria, measure emergent patterns

**Example**:
```
simulate_scenario(
    "100 people with neural interfaces. Interfaces fail at 10% rate. "
    "People can see each other's emotional states.",
    mode="mechanics"
)
```

**Output**:
- Quantitative: "Communication success dropped from 90% to 40%"
- Emergent: "Frustration cascaded through social clusters"
- Reproducible: Same config → same results

**Characteristics**:
- ⚡ Fast (1-2 seconds)
- 💰 Cheap ($0.01)
- 📊 Quantitative
- 🔄 Reproducible
- 🎯 Tests mechanics

---

#### Type 2: Social Simulation (LLM Roleplay)

**Use case**: Explore social nuances, personality differences, creative scenarios

**Example**:
```
simulate_scenario(
    "5 people with different personalities react to interface failure. "
    "One is stoic, one anxious, one problem-solver, one social, one withdrawn.",
    mode="social",
    num_agents=5  # Smaller scale
)
```

**Output**:
- Qualitative: "The anxious person's panic spread to the social person"
- Narrative: "The problem-solver tried to fix it, but their technical jargon confused others"
- Rich: Personality interactions, unexpected social dynamics

**Characteristics**:
- 🐌 Slower (30 seconds - 2 minutes)
- 💰💰 Expensive ($1-5)
- 📖 Qualitative/narrative
- 🎲 Stochastic (different each time)
- 🎭 Explores personalities/social

---

### Proposed: Two Simulation Tools

```python
# Tool 1: Mechanical ABM (Mesa)
simulate_mechanics(
    scenario: str,
    context: dict = None,
    steps: int = 50
) -> dict

# Tool 2: Social LLM Roleplay
simulate_interactions(
    scenario: str,
    agents: list[dict],  # [{"role": "anxious person", "traits": "..."}]
    rounds: int = 5
) -> dict
```

**Or unified interface with mode:**

```python
simulate_scenario(
    scenario: str,
    mode: "mechanics" | "social",
    context: dict = None
) -> dict
```

**Agent decides which to use based on what they're exploring!**

---

## Comparison Table

| Aspect | Mesa (Mechanics) | LLM Roleplay (Social) |
|--------|-----------------|---------------------|
| **Speed** | ⚡ 1-2s | 🐌 30s-2min |
| **Cost** | 💰 $0.01 | 💰💰 $1-5 |
| **Scale** | 100s of agents | 5-10 agents |
| **Output** | Quantitative + emergent | Qualitative + narrative |
| **Reproducible** | ✅ Yes | ❌ No (stochastic) |
| **Best for** | Testing mechanics | Exploring personalities |
| **Emergence** | Real (from rules) | Simulated (by LLM) |

---

## Use Cases: When to Use Each

### Use Mesa ABM When:
- Testing **mechanics**: "What if X happens at rate Y?"
- Finding **equilibria**: "What price will market settle at?"
- Measuring **scale effects**: "Does behavior change with 100 vs 1000 agents?"
- **Quantitative** questions: "What % of people get infected?"
- Need **reproducibility**: Same inputs → same outputs

**Example**: DSF agent testing world rules
```
"In my world, people can read emotions but not thoughts.
What happens if 10% of people lose this ability?"

→ Use Mesa: Fast, quantitative, tests the mechanic
```

---

### Use LLM Roleplay When:
- Exploring **personalities**: "How do different character types react?"
- Understanding **nuance**: "What subtle social dynamics emerge?"
- Creative **narrative**: "What interesting conflicts arise?"
- **Qualitative** questions: "How does this feel from different perspectives?"
- Need **richness**: Personality quirks, language, social subtlety

**Example**: DSF agent developing character interactions
```
"I have 3 characters: a stoic engineer, an empathetic artist, and
a pragmatic trader. They discover the emotion-reading system is
being manipulated. How do they react differently?"

→ Use LLM Roleplay: Rich personalities, social dynamics, narrative
```

---

## Recommendation for Letta Platform

**Phase 1**: Implement Mesa ABM (`simulate_mechanics`)
- Broader utility (fast, cheap, quantitative)
- Foundation for various domains
- Production-ready library

**Phase 2**: Add LLM Roleplay (`simulate_interactions`)
- Specialized for social/narrative exploration
- Complements Mesa (different use case)
- Higher cost, more experimental

**Both are valuable!** They serve different needs.

---

## Final Answer: Mesa + LLM Roleplay

**For a future-forward platform like Letta:**

1. **Mesa is NOT outdated** (v3.4.0, Dec 2024, actively maintained)
2. **Mesa is the right choice** for mechanical ABM (vs SimPy which is for DES)
3. **But ALSO add LLM roleplay** - it's complementary, not redundant

**The tools:**
```python
# letta/functions/function_sets/simulation.py

async def simulate_mechanics(scenario, context, steps=50):
    """Fast, quantitative ABM using Mesa"""
    # LLM translates scenario → Mesa config
    # Run simulation
    # LLM analyzes emergent patterns

async def simulate_interactions(scenario, agents, rounds=5):
    """Rich, qualitative LLM roleplay"""
    # LLM roleplays each agent
    # Agents interact over rounds
    # LLM synthesizes social dynamics
```

**Agent chooses based on what they're exploring:**
- Testing mechanics? → `simulate_mechanics`
- Exploring social dynamics? → `simulate_interactions`
- Both? → Call both!

This gives Letta users the **best of both worlds**. 🎯
