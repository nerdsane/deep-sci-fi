# OTS (Open Trajectory Spec) - Standalone Library

**Goal**: Extract OTS from Letta into a standalone, framework-agnostic Python library that brings context learning to any agent framework.

## Package Details

- **Name**: `ots` (`pip install ots`)
- **Repo**: `github.com/nerdsane/ots`
- **Architecture**: Batteries-included with pluggable backends

## Core Design

### What OTS Provides (Generic)

```
ots/
├── models.py              # Core data models (Trajectory, Turn, Decision, Entity, Annotation)
├── extractor.py           # DecisionExtractor (generic) + EntityExtractor interface
├── store.py               # TrajectoryStore with pluggable backends
│   ├── SQLiteBackend      # Ships with library
│   ├── FileBackend        # Ships with library
│   └── MemoryBackend      # Ships with library
├── embeddings.py          # Decision embeddings with pluggable providers
│   └── OpenAIProvider     # Default provider
├── context_learning.py    # Retrieval-based context learning
├── observability.py       # Langfuse + OTel exporters
└── adapters/
    └── base.py            # TrajectoryAdapter interface (frameworks implement)
```

### What Frameworks Provide (Letta example)

```python
# In Letta codebase (not in OTS)
from ots import TrajectoryAdapter, StorageBackend, EntityExtractor

class LettaAdapter(TrajectoryAdapter):
    """Converts Letta trajectory → OTS format"""

class LettaStorageBackend(StorageBackend):
    """Uses Letta's PostgreSQL + TrajectoryManager"""

class DSFEntityExtractor(EntityExtractor):
    """Extracts worlds/stories/rules from DSF tool calls"""
```

## Key Interfaces

### TrajectoryAdapter (frameworks implement)
```python
class TrajectoryAdapter(Protocol):
    def to_ots(self, framework_trajectory: Any) -> OTSTrajectory: ...
    def from_ots(self, ots_trajectory: OTSTrajectory) -> Any: ...
```

### StorageBackend (optional, for custom storage)
```python
class StorageBackend(Protocol):
    async def store(self, trajectory: OTSTrajectory) -> str: ...
    async def get(self, trajectory_id: str) -> Optional[OTSTrajectory]: ...
    async def search(self, query: str, limit: int) -> List[SearchResult]: ...
    async def delete(self, trajectory_id: str) -> bool: ...
```

### EntityExtractor (optional, for domain entities)
```python
class EntityExtractor(Protocol):
    def extract(self, trajectory: OTSTrajectory) -> List[Entity]: ...

# Built-in generic extractor (auto-extracts from tool calls)
class ToolEntityExtractor(EntityExtractor):
    """Zero-config entity extraction from tool calls"""
```

### EmbeddingProvider (optional, for custom embeddings)
```python
class EmbeddingProvider(Protocol):
    async def embed(self, text: str) -> List[float]: ...
    async def embed_batch(self, texts: List[str]) -> List[List[float]]: ...
```

## Usage Examples

### Basic (Standalone)
```python
from ots import TrajectoryStore, ContextLearning

# Works out of the box with SQLite
store = TrajectoryStore()  # Uses SQLite by default
store.store(my_trajectory)

# Context learning
learner = ContextLearning(store)
context = await learner.get_context("user asking about X")
```

### With Letta
```python
from ots import TrajectoryStore, ContextLearning
from letta.ots import LettaAdapter, LettaStorageBackend, DSFEntityExtractor

# Use Letta's storage
store = TrajectoryStore(backend=LettaStorageBackend())

# Convert Letta trajectories
adapter = LettaAdapter()
ots_traj = adapter.to_ots(letta_trajectory)

# Domain-specific entity extraction
store.register_extractor(DSFEntityExtractor())

# Context learning works the same
learner = ContextLearning(store)
context = await learner.get_context("creating a story in Nexus world")
```

## Implementation Phases

### Phase 1: Core Library Setup - COMPLETE
- [x] Create `nerdsane/ots` repo with Python package structure
- [x] Set up pyproject.toml, CI, tests
- [x] Extract `models.py` (already generic, minimal changes)
- [x] Create `protocols.py` with all interfaces

### Phase 2: Storage Layer - COMPLETE
- [x] Create `StorageBackend` protocol
- [x] Implement `SQLiteBackend` (default)
- [x] Implement `FileBackend` (JSON files)
- [x] Implement `MemoryBackend` (for testing)
- [x] Create `TrajectoryStore` facade

### Phase 3: Extraction - COMPLETE
- [x] Create `EntityExtractor` protocol
- [x] Implement `ToolEntityExtractor` (generic, auto-extracts from tool calls)
- [x] Port `DecisionExtractor` (remove Letta dependencies)
- [x] Create `LLMClient` protocol for decision enrichment

### Phase 4: Embeddings & Context Learning - COMPLETE
- [x] Create `EmbeddingProvider` protocol
- [x] Implement `OpenAIEmbeddingProvider`
- [x] Port `ContextLearning` (remove DSF-specific code)

### Phase 5: Observability - COMPLETE
- [x] Port `LangfuseExporter`
- [x] Port `OTelTrajectoryExporter`
- [x] Add convenience functions

### Phase 6: Letta Integration - PENDING
- [ ] Create `letta/ots/` package in Letta codebase
- [ ] Implement `LettaAdapter`
- [ ] Implement `LettaStorageBackend`
- [ ] Move `DSFEntityExtractor` to Letta
- [ ] Update Letta to use OTS library

## Files to Create (OTS Library)

```
ots/
├── __init__.py
├── models.py                 # From letta, minimal changes
├── protocols.py              # All Protocol definitions
├── store/
│   ├── __init__.py
│   ├── base.py               # TrajectoryStore facade
│   ├── sqlite.py             # SQLiteBackend
│   ├── file.py               # FileBackend
│   └── memory.py             # MemoryBackend
├── extraction/
│   ├── __init__.py
│   ├── decisions.py          # DecisionExtractor
│   └── entities.py           # ToolEntityExtractor
├── embeddings/
│   ├── __init__.py
│   ├── base.py               # EmbeddingProvider protocol
│   └── openai.py             # OpenAIEmbeddingProvider
├── learning/
│   ├── __init__.py
│   └── context.py            # ContextLearning
├── observability/
│   ├── __init__.py
│   ├── langfuse.py           # LangfuseExporter
│   └── otel.py               # OTelTrajectoryExporter
└── adapters/
    ├── __init__.py
    └── base.py               # TrajectoryAdapter protocol
```

## Files to Modify (Letta)

```
letta/letta/ots/              # New package
├── __init__.py
├── adapter.py                # LettaAdapter
├── backend.py                # LettaStorageBackend
└── dsf_extractor.py          # DSFEntityExtractor

letta/letta/trajectories/ots/ # Remove (replaced by ots library)
```

## Verification

1. **OTS library tests**: Unit tests for all components with mocked backends
2. **Integration test**: SQLite backend end-to-end (store → retrieve → search → context learning)
3. **Letta integration**: Existing OTS tests should pass with new library
4. **PyPI publish**: `pip install ots` works

## Open Questions

- JSON Schema for OTS format? (for cross-language compatibility)
- Versioning strategy for the spec itself?
