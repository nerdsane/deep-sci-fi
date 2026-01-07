# Async Trajectory Processing Design
**Date:** 2026-01-01
**Status:** Design phase

---

## Problem Statement

Currently, trajectory processing (LLM summary generation, outcome scoring, embedding generation) is **synchronous** and **blocks** the caller:

1. Agent completes a run
2. RunManager calls `_create_trajectory_from_run()`
3. If trajectory capture is enabled, it creates a trajectory record
4. **BUT:** The trajectory is not processed (no summary, no score, no embedding)
5. To process, you must manually call `POST /v1/trajectories/{id}/process`
6. This call **blocks for 5-15 seconds** while LLMs generate summaries and scores

**Impact:**
- Agent runs are blocked during processing
- Can't scale to high-volume capture
- No automatic processing after capture
- UI shows unprocessed trajectories with no summaries

---

## Goals

1. **Non-blocking capture** - Agent runs complete immediately
2. **Automatic processing** - New trajectories processed without manual intervention
3. **Scalable** - Handle 100+ trajectories/hour
4. **Reliable** - Retry failed processing, graceful degradation
5. **Observable** - Track processing status and progress

---

## Design Options

### Option 1: Python asyncio + Background Tasks ⭐ RECOMMENDED

**How it works:**
- Use Python's `asyncio` to run processing in background tasks
- No external dependencies (Redis, RabQ, Celery, etc.)
- Letta server already uses asyncio for FastAPI

**Implementation:**
```python
# In letta/services/trajectory_service.py

import asyncio
from typing import Optional

class TrajectoryService:
    def __init__(self, ...):
        self._processing_tasks = {}  # Track background tasks

    async def create_and_process_async(
        self,
        agent_id: str,
        data: dict,
        process: bool = True
    ) -> Trajectory:
        """Create trajectory and optionally process asynchronously."""
        # 1. Create trajectory record (fast, <100ms)
        trajectory = await self.create_trajectory(agent_id, data)

        # 2. If processing enabled, spawn background task
        if process:
            task = asyncio.create_task(
                self._process_trajectory_background(trajectory.id)
            )
            self._processing_tasks[trajectory.id] = task

        return trajectory

    async def _process_trajectory_background(self, trajectory_id: str):
        """Background task to process trajectory with retries."""
        try:
            # Process with LLM (5-15 seconds)
            await self.process_trajectory(trajectory_id)

            # Update status to 'processed'
            await self.update_trajectory(
                trajectory_id,
                {"processing_status": "completed"}
            )
        except Exception as e:
            # Log error and mark as failed
            logger.error(f"Failed to process trajectory {trajectory_id}: {e}")
            await self.update_trajectory(
                trajectory_id,
                {
                    "processing_status": "failed",
                    "processing_error": str(e)
                }
            )
```

**Pros:**
- ✅ No external dependencies
- ✅ Simple to implement
- ✅ Works with existing Letta async infrastructure
- ✅ Good for moderate volume (up to ~100 trajectories/hour)
- ✅ Task tracking built-in

**Cons:**
- ❌ Tasks lost if server restarts (not persisted)
- ❌ No distributed processing (single server)
- ❌ Limited observability (no UI for task queue)

**When to use:** Good for DSF's needs (moderate volume, single server deployment)

---

### Option 2: Job Queue (Celery + Redis)

**How it works:**
- Use Celery for distributed task queue
- Redis as message broker
- Separate worker processes consume jobs

**Implementation:**
```python
# In letta/worker/celery_app.py
from celery import Celery

celery_app = Celery('letta', broker='redis://localhost:6379/0')

@celery_app.task(bind=True, max_retries=3)
def process_trajectory_task(self, trajectory_id: str):
    """Celery task to process trajectory."""
    try:
        service = TrajectoryService(...)
        service.process_trajectory(trajectory_id)
    except Exception as e:
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))

# In trajectory_service.py
def create_trajectory_with_async_processing(agent_id, data):
    trajectory = create_trajectory(agent_id, data)

    # Queue processing job
    process_trajectory_task.delay(trajectory.id)

    return trajectory
```

**Starting workers:**
```bash
# Terminal 1: Run Letta server
letta server

# Terminal 2: Run Celery workers
celery -A letta.worker.celery_app worker --loglevel=info
```

**Pros:**
- ✅ Persisted jobs (survives restarts)
- ✅ Distributed processing (multiple workers)
- ✅ Advanced features (retries, scheduling, rate limiting)
- ✅ Great monitoring tools (Flower dashboard)
- ✅ Scales to high volume (1000s/hour)

**Cons:**
- ❌ External dependencies (Redis or RabbitMQ)
- ❌ More complex setup and deployment
- ❌ Overkill for moderate volume
- ❌ Needs separate worker processes

**When to use:** Production deployments with high volume or multiple servers

---

### Option 3: Database Job Queue (PostgreSQL)

**How it works:**
- Use PostgreSQL as a job queue
- Background thread polls for unprocessed trajectories
- No external dependencies beyond Postgres

**Implementation:**
```python
# Add to trajectory table
class Trajectory(Base):
    # ... existing fields ...
    processing_status = Column(
        String,
        default='pending',  # pending, processing, completed, failed
        nullable=False
    )
    processing_started_at = Column(DateTime, nullable=True)
    processing_completed_at = Column(DateTime, nullable=True)
    processing_error = Column(Text, nullable=True)

# Background worker thread
import threading
import time

class TrajectoryProcessor:
    def __init__(self, service: TrajectoryService):
        self.service = service
        self.running = False
        self.thread = None

    def start(self):
        """Start background processing thread."""
        self.running = True
        self.thread = threading.Thread(target=self._process_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop background processing."""
        self.running = False
        if self.thread:
            self.thread.join()

    def _process_loop(self):
        """Continuously process pending trajectories."""
        while self.running:
            try:
                # Get next unprocessed trajectory
                trajectory = self.service.get_next_unprocessed()

                if trajectory:
                    self._process_one(trajectory)
                else:
                    # Nothing to process, sleep
                    time.sleep(5)
            except Exception as e:
                logger.error(f"Processing loop error: {e}")
                time.sleep(10)

    def _process_one(self, trajectory):
        """Process a single trajectory."""
        try:
            # Mark as processing
            self.service.update_trajectory(
                trajectory.id,
                {
                    "processing_status": "processing",
                    "processing_started_at": datetime.utcnow()
                }
            )

            # Process with LLM
            self.service.process_trajectory(trajectory.id)

            # Mark as completed
            self.service.update_trajectory(
                trajectory.id,
                {
                    "processing_status": "completed",
                    "processing_completed_at": datetime.utcnow()
                }
            )
        except Exception as e:
            # Mark as failed
            self.service.update_trajectory(
                trajectory.id,
                {
                    "processing_status": "failed",
                    "processing_error": str(e)
                }
            )

# In letta server startup
processor = TrajectoryProcessor(trajectory_service)
processor.start()
```

**Pros:**
- ✅ No external dependencies (uses existing Postgres)
- ✅ Persisted jobs (survives restarts)
- ✅ Simple to implement
- ✅ Good for moderate volume
- ✅ Easy to query job status

**Cons:**
- ❌ Not ideal for high volume (polling overhead)
- ❌ Single-server processing (no distribution)
- ❌ Manual retry logic needed

**When to use:** Good middle ground - persisted jobs without external dependencies

---

## Recommendation for DSF

**Use Option 1 (asyncio) initially, with Option 3 (Postgres queue) as backup**

**Reasoning:**
1. DSF volume is moderate (~10-50 trajectories/day)
2. Single server deployment (no need for distribution)
3. Minimize complexity and dependencies
4. Can migrate to Celery later if needed

**Implementation Plan:**

### Step 1: Add Processing Status to Schema
```python
# In trajectory.py ORM
processing_status = Column(String, default='pending')
processing_error = Column(Text, nullable=True)
```

### Step 2: Modify Trajectory Capture
```python
# In run_manager.py
async def _create_trajectory_from_run(self, run: Run):
    """Create and queue trajectory for background processing."""
    trajectory_data = self.trajectory_converter.convert(run, steps, messages)

    # Create trajectory with pending status
    trajectory = await self.trajectory_service.create_and_process_async(
        agent_id=run.agent_id,
        data=trajectory_data,
        process=True  # Enable async processing
    )
```

### Step 3: Background Processing Task
```python
# In trajectory_service.py
async def create_and_process_async(self, agent_id, data, process=True):
    trajectory = await self.create_trajectory(agent_id, data)

    if process:
        asyncio.create_task(self._process_background(trajectory.id))

    return trajectory

async def _process_background(self, trajectory_id):
    """Background task with retry logic."""
    max_retries = 3
    retry_count = 0

    while retry_count < max_retries:
        try:
            await self.process_trajectory(trajectory_id)
            return  # Success
        except Exception as e:
            retry_count += 1
            if retry_count >= max_retries:
                # Mark as failed
                await self.update_trajectory(
                    trajectory_id,
                    {"processing_status": "failed", "processing_error": str(e)}
                )
            else:
                # Wait before retry (exponential backoff)
                await asyncio.sleep(2 ** retry_count)
```

---

## Migration Path

**Phase 1: Asyncio (Week 1)**
- Implement async processing with background tasks
- Add processing_status field
- Update UI to show processing status

**Phase 2: Monitoring (Week 2)**
- Add metrics (processing time, success rate)
- Create admin endpoint to view queue status
- Add alerts for failed processing

**Phase 3: Scale (If Needed)**
- Migrate to Postgres queue (Option 3) for persistence
- Or migrate to Celery (Option 2) for distribution
- Add worker monitoring dashboard

---

## Testing Strategy

1. **Unit Tests:**
   - Test async processing creates background task
   - Test retry logic on failures
   - Test status updates

2. **Integration Tests:**
   - Create trajectory, verify it gets processed
   - Verify processing status transitions
   - Test error handling

3. **Load Tests:**
   - Create 100 trajectories rapidly
   - Verify all get processed
   - Measure processing throughput

---

## Monitoring & Observability

**Metrics to Track:**
- Processing queue size (pending trajectories)
- Average processing time
- Success/failure rate
- Retry count distribution

**Endpoints to Add:**
```python
GET /v1/trajectories/stats
{
  "total": 1000,
  "pending": 5,
  "processing": 2,
  "completed": 980,
  "failed": 13,
  "avg_processing_time_seconds": 8.3
}

GET /v1/trajectories/queue
{
  "queue_size": 5,
  "oldest_pending": "2026-01-01T10:30:00Z",
  "estimated_processing_time_seconds": 42
}
```

---

## Questions to Answer

1. **Should processing be opt-in or automatic?**
   - Recommendation: Automatic with env var to disable
   - `TRAJECTORY_AUTO_PROCESS=true` (default)

2. **Should we batch process?**
   - Recommendation: No, process individually
   - LLM calls are independent, no benefit to batching

3. **What about rate limiting?**
   - Recommendation: Add semaphore to limit concurrent processing
   - Max 5 concurrent LLM calls to avoid quota issues

4. **Retry strategy?**
   - Recommendation: 3 retries with exponential backoff
   - 2s, 4s, 8s delays between retries

5. **Should failed trajectories be retried later?**
   - Recommendation: Yes, add manual retry endpoint
   - `POST /v1/trajectories/{id}/retry`

---

## Summary

**Recommended Approach: Python asyncio + Background Tasks**

**Why:**
- Simple, no new dependencies
- Works with Letta's async architecture
- Good enough for DSF's volume
- Easy to upgrade later if needed

**What to Build:**
1. Add `processing_status` field to trajectories
2. Implement `create_and_process_async()` method
3. Add background task with retry logic
4. Update UI to show processing status
5. Add monitoring endpoints

**Estimated Time:** 2-3 days

**Alternative:** If we need persistence (survive restarts), use Postgres queue (Option 3). If we need high volume/distribution, use Celery (Option 2).
