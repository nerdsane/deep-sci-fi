# Evaluation System Implementation Plan for Letta

## Overview

Implementing the two-layer evaluation system from the agent design philosophy:
1. **Agent-callable evaluation tools** - For self-assessment during execution
2. **External evaluation system** - For systematic quality measurement and tracking

## Architecture

### Database Schema

#### 1. EvaluationResult Table

```python
# /letta/orm/evaluation_result.py

from sqlalchemy import Column, String, Float, ForeignKey, JSON, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from letta.orm.base import Base
from letta.orm.mixins import OrganizationMixin
import uuid
from datetime import datetime

class EvaluationResult(Base, OrganizationMixin):
    """Stores individual evaluation results"""

    __tablename__ = "evaluation_results"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign keys
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id"), nullable=False)
    step_id = Column(UUID(as_uuid=True), ForeignKey("steps.id"), nullable=True)  # Optional, for step-level evals
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)

    # Evaluation metadata
    evaluation_type = Column(String, nullable=False)  # "consistency", "depth", "abstraction", etc.
    evaluator_version = Column(String, nullable=False)  # Track eval tool versions for reproducibility
    is_agent_initiated = Column(Boolean, default=False)  # True if agent called this, False if external eval

    # Results
    score = Column(Float, nullable=True)  # Overall score (0.0-1.0 or custom scale)
    passed = Column(Boolean, nullable=True)  # Binary pass/fail if applicable
    details = Column(JSON, nullable=False)  # Structured evaluation details

    # Timing
    evaluated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    evaluation_duration_ms = Column(Float, nullable=True)  # How long eval took

    # Indexing for fast queries
    __table_args__ = (
        Index("idx_eval_run", "run_id"),
        Index("idx_eval_type", "evaluation_type"),
        Index("idx_eval_agent", "agent_id"),
        Index("idx_eval_time", "evaluated_at"),
        Index("idx_eval_org", "organization_id"),
    )
```

#### 2. EvaluationMetric Table (Aggregates)

```python
# /letta/orm/evaluation_metric.py

from sqlalchemy import Column, String, Float, Integer, DateTime, Index, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from letta.orm.base import Base
from letta.orm.mixins import OrganizationMixin, ProjectMixin
import uuid
from datetime import datetime

class EvaluationMetric(Base, OrganizationMixin, ProjectMixin):
    """Aggregate evaluation metrics over time periods"""

    __tablename__ = "evaluation_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Scope
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True)  # Null = all agents
    evaluation_type = Column(String, nullable=False)

    # Time period
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    granularity = Column(String, nullable=False)  # "hour", "day", "week", "month"

    # Aggregates
    run_count = Column(Integer, nullable=False, default=0)
    avg_score = Column(Float, nullable=True)
    min_score = Column(Float, nullable=True)
    max_score = Column(Float, nullable=True)
    std_dev = Column(Float, nullable=True)
    pass_rate = Column(Float, nullable=True)  # % of runs that passed

    # Trends (compared to previous period)
    score_trend = Column(Float, nullable=True)  # +/- change in avg score

    calculated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_metric_agent_type", "agent_id", "evaluation_type"),
        Index("idx_metric_period", "period_start", "period_end"),
        Index("idx_metric_org_project", "organization_id", "project_id"),
    )
```

### Agent-Callable Evaluation Tools

Create `/letta/functions/function_sets/evaluations.py`:

```python
"""
Evaluation tools that agents can use for self-assessment.

These tools align with the Bitter Lesson philosophy:
- They ENABLE capability, don't PRESCRIBE workflows
- Agents choose when/if to use them
- Same tools used for both agent self-eval and external eval
"""

from typing import Dict, Any, Optional, List
from letta.schemas.agent import AgentState

# ============================================================================
# 1. CONSISTENCY VERIFICATION
# ============================================================================

def verify_consistency(
    world: Dict[str, Any],
    agent_state: Optional[AgentState] = None
) -> Dict[str, Any]:
    """
    Check world for logical contradictions.

    Agent uses this to verify their world is logically consistent.
    Returns actionable contradictions to fix.

    Args:
        world: World data structure to verify
        agent_state: Optional agent state for context

    Returns:
        {
            "consistent": bool,
            "contradictions": [
                {
                    "elements": ["entity1", "rule2"],
                    "description": "Rule2 requires X but entity1 has Y",
                    "severity": "major|minor",
                    "suggestion": "Consider changing entity1 to..."
                }
            ],
            "edge_cases_checked": int,
            "verification_approach": "logical_reasoning|z3|manual_check"
        }
    """
    # Implementation would:
    # 1. Extract rules and entities from world
    # 2. Build logical model (Z3, or LLM-based reasoning)
    # 3. Check for contradictions
    # 4. Return structured feedback

    # Placeholder implementation
    return {
        "consistent": True,
        "contradictions": [],
        "edge_cases_checked": 0,
        "verification_approach": "logical_reasoning"
    }

# ============================================================================
# 2. DEPTH ASSESSMENT
# ============================================================================

def assess_depth(
    content: str,
    content_type: str,  # "research" | "simulation" | "world" | "narrative"
    agent_state: Optional[AgentState] = None
) -> Dict[str, Any]:
    """
    Evaluate how deep/thorough content is.

    Agent uses this to self-assess quality of their work.
    Provides specific suggestions for going deeper.

    Args:
        content: The content to assess (research output, simulation description, etc)
        content_type: Type of content being assessed
        agent_state: Optional agent state

    Returns:
        {
            "depth_score": float (1.0-5.0),
            "depth_category": "surface|medium|deep",
            "reasoning": str,
            "strengths": [str],
            "could_go_deeper": [str],  # Specific suggestions
            "comparison": "shallow|typical|above_average|deep",
            "follow_up_questions": [str]  # Questions to explore deeper
        }
    """
    # Implementation would:
    # 1. Analyze content with LLM
    # 2. Compare against quality rubrics
    # 3. Generate specific suggestions
    # 4. Return structured feedback

    return {
        "depth_score": 3.0,
        "depth_category": "medium",
        "reasoning": "Content shows some connections but could explore more",
        "strengths": [],
        "could_go_deeper": [],
        "comparison": "typical",
        "follow_up_questions": []
    }

# ============================================================================
# 3. NOVELTY ASSESSMENT
# ============================================================================

def check_novelty(
    current: Dict[str, Any],
    previous: Optional[Dict[str, Any]] = None,
    agent_state: Optional[AgentState] = None
) -> Dict[str, Any]:
    """
    Assess what's new/surprising compared to previous state.

    Agent uses this to understand information gain from their actions.
    Helps decide whether to continue exploring or pivot.

    Args:
        current: Current world state
        previous: Previous world state to compare against
        agent_state: Optional agent state

    Returns:
        {
            "novelty_score": float (0.0-1.0),
            "new_elements": {
                "entities": [str],
                "rules": [str],
                "relationships": [str]
            },
            "surprisingness": float (0.0-1.0),
            "insights": [str],
            "significance": "trivial|minor|moderate|major|breakthrough",
            "information_gain": str  # Description of what was learned
        }
    """
    # Implementation would:
    # 1. Diff current vs previous (if provided)
    # 2. Analyze significance of changes
    # 3. Calculate novelty metrics
    # 4. Return structured assessment

    return {
        "novelty_score": 0.5,
        "new_elements": {
            "entities": [],
            "rules": [],
            "relationships": []
        },
        "surprisingness": 0.5,
        "insights": [],
        "significance": "moderate",
        "information_gain": "Added some new elements"
    }

# ============================================================================
# 4. ABSTRACTION CHECK
# ============================================================================

def check_abstraction(
    world: Dict[str, Any],
    agent_state: Optional[AgentState] = None
) -> Dict[str, Any]:
    """
    Detect unnecessary concreteness (names, cultural specifics).

    Agent uses this to ensure world remains abstract and universal.
    Provides specific suggestions for each concrete element found.

    Args:
        world: World data to check
        agent_state: Optional agent state

    Returns:
        {
            "abstraction_score": float (0.0-1.0),
            "concrete_names": [
                {
                    "name": "John Smith",
                    "context": "entity description",
                    "suggestion": "The Merchant",
                    "reasoning": "Use role-based naming"
                }
            ],
            "cultural_specifics": [
                {
                    "element": "Christmas",
                    "context": "festival description",
                    "suggestion": "The Renewal Ceremony",
                    "reasoning": "Invent culture-neutral events"
                }
            ],
            "unnecessary_details": [str],
            "examples_of_good_abstraction": [str]
        }
    """
    # Implementation would:
    # 1. Scan world for names (proper nouns, real places, etc)
    # 2. Detect cultural references
    # 3. Suggest abstract alternatives
    # 4. Return structured feedback

    return {
        "abstraction_score": 0.8,
        "concrete_names": [],
        "cultural_specifics": [],
        "unnecessary_details": [],
        "examples_of_good_abstraction": []
    }

# ============================================================================
# 5. NARRATIVE EVALUATION
# ============================================================================

def evaluate_narrative(
    story: str,
    world: Dict[str, Any],
    agent_state: Optional[AgentState] = None
) -> Dict[str, Any]:
    """
    Assess story quality and world-grounding.

    Agent uses this to check if their story is compelling and follows world rules.

    Args:
        story: The narrative text to evaluate
        world: World rules the story should follow
        agent_state: Optional agent state

    Returns:
        {
            "structure": {
                "has_conflict": bool,
                "has_stakes": bool,
                "character_agency": bool,
                "arc_complete": bool
            },
            "grounding": {
                "follows_world_rules": bool,
                "rules_used": [str],
                "violations": [str]
            },
            "quality": {
                "emotional_resonance": float (1-5),
                "interestingness": float (1-5),
                "originality": float (1-5)
            },
            "feedback": str,
            "strengths": [str],
            "weaknesses": [str]
        }
    """
    # Implementation would:
    # 1. Analyze story structure
    # 2. Check against world rules
    # 3. Assess quality dimensions
    # 4. Return structured feedback

    return {
        "structure": {
            "has_conflict": True,
            "has_stakes": True,
            "character_agency": True,
            "arc_complete": True
        },
        "grounding": {
            "follows_world_rules": True,
            "rules_used": [],
            "violations": []
        },
        "quality": {
            "emotional_resonance": 3.0,
            "interestingness": 3.0,
            "originality": 3.0
        },
        "feedback": "Story has good structure",
        "strengths": [],
        "weaknesses": []
    }

# ============================================================================
# TOOL METADATA FOR LETTA REGISTRATION
# ============================================================================

EVALUATION_TOOLS = [
    {
        "name": "verify_consistency",
        "description": "Check world for logical contradictions. Returns specific contradictions to fix.",
        "category": "evaluation",
        "auto_error": True
    },
    {
        "name": "assess_depth",
        "description": "Evaluate how deep/thorough content is. Returns suggestions for going deeper.",
        "category": "evaluation",
        "auto_error": True
    },
    {
        "name": "check_novelty",
        "description": "Assess what's new/surprising. Helps understand information gain.",
        "category": "evaluation",
        "auto_error": True
    },
    {
        "name": "check_abstraction",
        "description": "Detect unnecessary concrete names/cultural specifics. Returns suggestions for abstraction.",
        "category": "evaluation",
        "auto_error": True
    },
    {
        "name": "evaluate_narrative",
        "description": "Assess story quality and world-grounding. Returns structured feedback.",
        "category": "evaluation",
        "auto_error": True
    }
]
```

### External Evaluation System

Create `/letta/services/evaluation_manager.py`:

```python
"""
EvaluationManager - Orchestrates external (systematic) evaluation.

This is separate from agent self-evaluation:
- Runs evaluation tools systematically on completed runs
- Tracks metrics over time
- Compares across runs
- Used to inform system improvement, not to constrain agents
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from datetime import datetime, timedelta
import asyncio

from letta.orm.evaluation_result import EvaluationResult
from letta.orm.evaluation_metric import EvaluationMetric
from letta.orm.run import Run
from letta.schemas.evaluation_result import EvaluationResultCreate, EvaluationResultUpdate
from letta.functions.function_sets.evaluations import (
    verify_consistency,
    assess_depth,
    check_novelty,
    check_abstraction,
    evaluate_narrative
)


class EvaluationManager:
    """Manages external evaluation of agent runs"""

    # Map evaluation types to functions
    EVALUATORS = {
        "consistency": verify_consistency,
        "depth": assess_depth,
        "novelty": check_novelty,
        "abstraction": check_abstraction,
        "narrative": evaluate_narrative
    }

    EVALUATOR_VERSION = "1.0.0"  # Track version for reproducibility

    def __init__(self):
        pass

    # ========================================================================
    # CORE EVALUATION METHODS
    # ========================================================================

    async def evaluate_run(
        self,
        run_id: str,
        evaluation_types: List[str],
        db: AsyncSession,
        actor_user_id: Optional[str] = None
    ) -> List[EvaluationResult]:
        """
        Run external evaluation on a completed run.

        Args:
            run_id: ID of the run to evaluate
            evaluation_types: Which evaluations to run (e.g., ["consistency", "depth"])
            db: Database session
            actor_user_id: User triggering evaluation

        Returns:
            List of evaluation results
        """
        # 1. Fetch run and messages
        run = await self._get_run(run_id, db)
        if not run:
            raise ValueError(f"Run {run_id} not found")

        # 2. Extract world/content from run messages
        world_data, story_data = await self._extract_evaluation_data(run, db)

        # 3. Run each evaluation
        results = []
        for eval_type in evaluation_types:
            if eval_type not in self.EVALUATORS:
                continue

            start_time = datetime.utcnow()

            # Call the evaluation function
            evaluator = self.EVALUATORS[eval_type]
            eval_result = await self._run_evaluator(
                evaluator,
                eval_type,
                world_data,
                story_data,
                run
            )

            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

            # 4. Store result
            db_result = EvaluationResult(
                run_id=run.id,
                agent_id=run.agent_id,
                evaluation_type=eval_type,
                evaluator_version=self.EVALUATOR_VERSION,
                is_agent_initiated=False,  # External eval
                score=eval_result.get("score"),
                passed=eval_result.get("passed"),
                details=eval_result,
                evaluated_at=datetime.utcnow(),
                evaluation_duration_ms=duration_ms,
                organization_id=run.organization_id
            )
            db.add(db_result)
            results.append(db_result)

        await db.commit()
        return results

    async def _run_evaluator(
        self,
        evaluator_func,
        eval_type: str,
        world_data: Optional[Dict],
        story_data: Optional[str],
        run: Run
    ) -> Dict[str, Any]:
        """Run a specific evaluator and standardize output"""

        # Call appropriate evaluator based on type
        if eval_type == "consistency":
            result = evaluator_func(world=world_data)
        elif eval_type == "depth":
            result = evaluator_func(
                content=story_data or str(world_data),
                content_type="world"
            )
        elif eval_type == "abstraction":
            result = evaluator_func(world=world_data)
        elif eval_type == "narrative":
            result = evaluator_func(story=story_data, world=world_data)
        elif eval_type == "novelty":
            # For novelty, we'd need to compare to previous runs
            # Simplified here
            result = evaluator_func(current=world_data, previous=None)
        else:
            result = {}

        # Standardize: ensure we have a score and passed flag
        if "score" not in result:
            result["score"] = self._calculate_score(result, eval_type)
        if "passed" not in result:
            result["passed"] = result.get("score", 0) >= 0.7  # Default threshold

        return result

    def _calculate_score(self, result: Dict, eval_type: str) -> float:
        """Calculate a standardized 0.0-1.0 score from eval result"""

        if eval_type == "consistency":
            # Consistent = 1.0, contradictions reduce score
            contradiction_count = len(result.get("contradictions", []))
            return max(0.0, 1.0 - (contradiction_count * 0.2))

        elif eval_type == "depth":
            # depth_score is 1-5, normalize to 0-1
            depth_score = result.get("depth_score", 3.0)
            return (depth_score - 1) / 4.0

        elif eval_type == "abstraction":
            # Already 0-1
            return result.get("abstraction_score", 0.5)

        elif eval_type == "narrative":
            # Average of quality metrics (1-5)
            quality = result.get("quality", {})
            avg = sum([
                quality.get("emotional_resonance", 3),
                quality.get("interestingness", 3),
                quality.get("originality", 3)
            ]) / 3
            return (avg - 1) / 4.0

        elif eval_type == "novelty":
            # Already 0-1
            return result.get("novelty_score", 0.5)

        return 0.5  # Default

    # ========================================================================
    # BATCH EVALUATION
    # ========================================================================

    async def evaluate_recent_runs(
        self,
        agent_id: Optional[str],
        hours: int,
        evaluation_types: List[str],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Evaluate all runs from the last N hours.

        Useful for batch processing and generating aggregate metrics.
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        # Fetch runs
        query = select(Run).where(
            and_(
                Run.created_at >= cutoff,
                Run.status == "completed"
            )
        )
        if agent_id:
            query = query.where(Run.agent_id == agent_id)

        result = await db.execute(query)
        runs = result.scalars().all()

        # Evaluate each run
        all_results = []
        for run in runs:
            results = await self.evaluate_run(
                run_id=str(run.id),
                evaluation_types=evaluation_types,
                db=db
            )
            all_results.extend(results)

        return {
            "runs_evaluated": len(runs),
            "evaluations_completed": len(all_results),
            "timestamp": datetime.utcnow().isoformat()
        }

    # ========================================================================
    # METRICS AGGREGATION
    # ========================================================================

    async def calculate_metrics(
        self,
        agent_id: Optional[str],
        evaluation_type: str,
        period_start: datetime,
        period_end: datetime,
        granularity: str,
        db: AsyncSession
    ) -> EvaluationMetric:
        """
        Calculate aggregate metrics for a time period.

        This powers dashboards and trend analysis.
        """
        # Fetch all evaluation results in period
        query = select(EvaluationResult).where(
            and_(
                EvaluationResult.evaluation_type == evaluation_type,
                EvaluationResult.evaluated_at >= period_start,
                EvaluationResult.evaluated_at < period_end
            )
        )
        if agent_id:
            query = query.where(EvaluationResult.agent_id == agent_id)

        result = await db.execute(query)
        results = result.scalars().all()

        if not results:
            return None

        # Calculate aggregates
        scores = [r.score for r in results if r.score is not None]
        passes = [r.passed for r in results if r.passed is not None]

        import statistics

        metric = EvaluationMetric(
            agent_id=agent_id,
            evaluation_type=evaluation_type,
            period_start=period_start,
            period_end=period_end,
            granularity=granularity,
            run_count=len(results),
            avg_score=statistics.mean(scores) if scores else None,
            min_score=min(scores) if scores else None,
            max_score=max(scores) if scores else None,
            std_dev=statistics.stdev(scores) if len(scores) > 1 else None,
            pass_rate=sum(passes) / len(passes) if passes else None,
            calculated_at=datetime.utcnow()
        )

        # Calculate trend (compare to previous period)
        prev_start = period_start - (period_end - period_start)
        prev_metric = await self.calculate_metrics(
            agent_id, evaluation_type, prev_start, period_start, granularity, db
        )
        if prev_metric and prev_metric.avg_score and metric.avg_score:
            metric.score_trend = metric.avg_score - prev_metric.avg_score

        db.add(metric)
        await db.commit()

        return metric

    # ========================================================================
    # QUERY METHODS
    # ========================================================================

    async def get_run_evaluations(
        self,
        run_id: str,
        db: AsyncSession
    ) -> List[EvaluationResult]:
        """Get all evaluation results for a run"""
        query = select(EvaluationResult).where(
            EvaluationResult.run_id == run_id
        ).order_by(desc(EvaluationResult.evaluated_at))

        result = await db.execute(query)
        return result.scalars().all()

    async def get_agent_metrics(
        self,
        agent_id: str,
        evaluation_type: Optional[str],
        limit: int,
        db: AsyncSession
    ) -> List[EvaluationMetric]:
        """Get recent metrics for an agent"""
        query = select(EvaluationMetric).where(
            EvaluationMetric.agent_id == agent_id
        )
        if evaluation_type:
            query = query.where(EvaluationMetric.evaluation_type == evaluation_type)

        query = query.order_by(desc(EvaluationMetric.period_end)).limit(limit)

        result = await db.execute(query)
        return result.scalars().all()

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    async def _get_run(self, run_id: str, db: AsyncSession) -> Optional[Run]:
        """Fetch run by ID"""
        result = await db.execute(
            select(Run).where(Run.id == run_id)
        )
        return result.scalar_one_or_none()

    async def _extract_evaluation_data(
        self,
        run: Run,
        db: AsyncSession
    ) -> tuple[Optional[Dict], Optional[str]]:
        """
        Extract world and story data from run messages.

        This is application-specific - you'll need to adapt based on
        how your DSF agents structure their messages.
        """
        # Placeholder: extract from run.metadata or messages
        # In practice, you'd:
        # 1. Fetch messages for this run
        # 2. Parse out world JSON and story text
        # 3. Return structured data

        world_data = run.metadata.get("world") if run.metadata else None
        story_data = run.metadata.get("story") if run.metadata else None

        return world_data, story_data
```

### REST API Endpoints

Create `/letta/server/rest_api/routers/v1/evaluations.py`:

```python
"""
REST API endpoints for evaluation system.

Provides:
- Trigger evaluation on completed runs
- Query evaluation results
- Get aggregate metrics
- Dashboard data for visualization
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime, timedelta

from letta.server.rest_api.dependencies import get_db, get_current_user
from letta.services.evaluation_manager import EvaluationManager
from letta.schemas.evaluation_result import (
    EvaluationResultResponse,
    EvaluationTriggerRequest,
    EvaluationMetricResponse,
    EvaluationDashboardResponse
)

router = APIRouter(prefix="/evaluations", tags=["evaluations"])


# ============================================================================
# TRIGGER EVALUATIONS
# ============================================================================

@router.post("/runs/{run_id}/evaluate")
async def evaluate_run(
    run_id: str,
    request: EvaluationTriggerRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """
    Trigger external evaluation on a completed run.

    Example request:
    {
        "evaluation_types": ["consistency", "depth", "abstraction"]
    }
    """
    manager = EvaluationManager()

    try:
        results = await manager.evaluate_run(
            run_id=run_id,
            evaluation_types=request.evaluation_types,
            db=db,
            actor_user_id=user_id
        )

        return {
            "run_id": run_id,
            "evaluations_completed": len(results),
            "results": [EvaluationResultResponse.from_orm(r) for r in results]
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/agents/{agent_id}/evaluate-recent")
async def evaluate_recent_runs(
    agent_id: str,
    hours: int = Query(24, ge=1, le=168),
    evaluation_types: List[str] = Query(["consistency", "depth", "abstraction"]),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """
    Evaluate all recent runs for an agent.

    Useful for batch processing and catching up on evaluations.
    """
    manager = EvaluationManager()

    result = await manager.evaluate_recent_runs(
        agent_id=agent_id,
        hours=hours,
        evaluation_types=evaluation_types,
        db=db
    )

    return result


# ============================================================================
# QUERY EVALUATION RESULTS
# ============================================================================

@router.get("/runs/{run_id}")
async def get_run_evaluations(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
) -> List[EvaluationResultResponse]:
    """
    Get all evaluation results for a specific run.
    """
    manager = EvaluationManager()
    results = await manager.get_run_evaluations(run_id=run_id, db=db)

    return [EvaluationResultResponse.from_orm(r) for r in results]


# ============================================================================
# METRICS & ANALYTICS
# ============================================================================

@router.get("/agents/{agent_id}/metrics")
async def get_agent_metrics(
    agent_id: str,
    evaluation_type: Optional[str] = None,
    limit: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
) -> List[EvaluationMetricResponse]:
    """
    Get aggregate metrics for an agent over time.

    Returns time-series data for dashboards and trend analysis.
    """
    manager = EvaluationManager()
    metrics = await manager.get_agent_metrics(
        agent_id=agent_id,
        evaluation_type=evaluation_type,
        limit=limit,
        db=db
    )

    return [EvaluationMetricResponse.from_orm(m) for m in metrics]


@router.get("/agents/{agent_id}/dashboard")
async def get_evaluation_dashboard(
    agent_id: str,
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
) -> EvaluationDashboardResponse:
    """
    Get comprehensive dashboard data for an agent.

    Returns:
    - Current scores for each evaluation type
    - Trends over time
    - Pass rates
    - Recent failures
    """
    manager = EvaluationManager()

    # Fetch recent metrics for all eval types
    eval_types = ["consistency", "depth", "abstraction", "narrative", "novelty"]

    dashboard_data = {
        "agent_id": agent_id,
        "period_days": days,
        "evaluation_types": {}
    }

    for eval_type in eval_types:
        metrics = await manager.get_agent_metrics(
            agent_id=agent_id,
            evaluation_type=eval_type,
            limit=days,
            db=db
        )

        if metrics:
            latest = metrics[0]
            dashboard_data["evaluation_types"][eval_type] = {
                "current_score": latest.avg_score,
                "pass_rate": latest.pass_rate,
                "trend": latest.score_trend,
                "run_count": latest.run_count
            }

    return dashboard_data


# ============================================================================
# COMPARISON & ANALYSIS
# ============================================================================

@router.get("/compare")
async def compare_agents(
    agent_ids: List[str] = Query(...),
    evaluation_type: str = Query("consistency"),
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """
    Compare evaluation metrics across multiple agents.

    Useful for A/B testing different agent configurations.
    """
    manager = EvaluationManager()

    comparison_data = {}

    for agent_id in agent_ids:
        metrics = await manager.get_agent_metrics(
            agent_id=agent_id,
            evaluation_type=evaluation_type,
            limit=days,
            db=db
        )

        if metrics:
            latest = metrics[0]
            comparison_data[agent_id] = {
                "avg_score": latest.avg_score,
                "pass_rate": latest.pass_rate,
                "run_count": latest.run_count,
                "trend": latest.score_trend
            }

    return {
        "evaluation_type": evaluation_type,
        "period_days": days,
        "agents": comparison_data
    }
```

## Implementation Phases

### Phase 1: Database Setup (Week 1)
- [ ] Create `evaluation_result.py` ORM model
- [ ] Create `evaluation_metric.py` ORM model
- [ ] Generate Alembic migration
- [ ] Run migration, verify tables created

### Phase 2: Evaluation Tools (Week 1-2)
- [ ] Implement `/letta/functions/function_sets/evaluations.py`
- [ ] Start with placeholder implementations
- [ ] Register tools in Letta's tool system
- [ ] Test tools callable from agent

### Phase 3: External Evaluation System (Week 2-3)
- [ ] Implement `EvaluationManager` service
- [ ] Create evaluation schemas in `/letta/schemas/`
- [ ] Wire up to existing run/message infrastructure
- [ ] Test batch evaluation on sample runs

### Phase 4: REST API (Week 3)
- [ ] Implement `/routers/v1/evaluations.py`
- [ ] Test endpoints with Swagger UI
- [ ] Add authentication/authorization checks
- [ ] Document API usage

### Phase 5: Tool Implementation (Week 4-6)
- [ ] Implement `verify_consistency()` with real logic
- [ ] Implement `assess_depth()` with LLM-as-judge
- [ ] Implement `check_abstraction()` with pattern matching
- [ ] Implement `evaluate_narrative()` with structure analysis
- [ ] Implement `check_novelty()` with diff analysis

### Phase 6: Metrics & Dashboard (Week 6-7)
- [ ] Implement aggregate metrics calculation
- [ ] Create periodic metric calculation job
- [ ] Build simple dashboard endpoint
- [ ] Test time-series queries

### Phase 7: Integration & Testing (Week 7-8)
- [ ] Test full flow: agent run → evaluation → metrics
- [ ] Verify agent can call eval tools during execution
- [ ] Verify external eval runs systematically
- [ ] Load testing on evaluation endpoints
- [ ] Documentation and examples

## Key Design Decisions

### 1. Same Tools for Agent & External Eval
✅ **Aligned with philosophy**: Agent has access to same evaluation capabilities
✅ **Fair**: Only eval on criteria agent could check
✅ **Scalable**: Better models use eval tools more strategically

### 2. Separate Agent-Initiated vs External Eval
- `is_agent_initiated` flag tracks source
- Agent decides when to eval (self-directed)
- External eval runs systematically (measurement)
- Both stored in same table for comparison

### 3. Versioned Evaluators
- `evaluator_version` field tracks eval tool versions
- Important for reproducibility
- Can compare "same eval, different versions"
- Enables eval tool improvement over time

### 4. Flexible Eval Data Structure
- `details` JSON field stores full eval output
- `score` and `passed` for quick filtering
- Supports arbitrary eval-specific data
- Can evolve eval output without schema changes

### 5. Time-Series Metrics
- Pre-aggregate metrics for fast dashboard queries
- Trends calculated automatically
- Supports hourly/daily/weekly/monthly granularity
- Can compare agent performance over time

## Integration with Existing Letta Features

### Metrics Integration
- Hook into existing `otel/metric_registry.py`
- Add evaluation-specific metrics:
  ```python
  count_evaluation_executed
  hist_evaluation_duration_ms
  gauge_avg_evaluation_score
  ```

### Step Feedback Integration
- Existing feedback system (`FeedbackType.POSITIVE/NEGATIVE`)
- Can correlate human feedback with eval scores
- Research question: Do eval scores predict human feedback?

### Run Lifecycle Integration
- Hook into run completion event
- Optionally auto-trigger evaluations
- Store eval results linked to runs

## Open Questions

### Q1: When to trigger external evaluation?
**Options:**
- Immediate (on run completion)
- Batched (every N hours)
- On-demand (user triggers)
- Sampling (evaluate X% of runs)

**Recommendation**: Start with on-demand + batched
- User can trigger via API when needed
- Periodic job evaluates recent runs
- Add auto-eval later if needed

### Q2: How to implement tool logic?
**Options:**
- LLM-as-judge (call Claude with rubric)
- Rule-based (regex, pattern matching)
- Hybrid (rules + LLM for edge cases)
- External services (Z3 for consistency, etc)

**Recommendation**: Hybrid approach
- `check_abstraction`: Rule-based (detect proper nouns, cultural references)
- `verify_consistency`: Z3 or LLM with logical reasoning
- `assess_depth`, `evaluate_narrative`: LLM-as-judge
- `check_novelty`: Diff-based + LLM synthesis

### Q3: Should agents auto-suggest evaluations?
**Current**: Agent must explicitly call eval tools
**Alternative**: Agent manager suggests "You might want to run check_abstraction"

**Recommendation**: Start without auto-suggest
- Keep it pure: agent decides entirely
- If agents consistently forget, add soft hints in system prompt
- Monitor agent eval tool usage in external metrics

### Q4: How to handle eval tool failures?
**Options:**
- Fail the run (blocking)
- Log error, continue (non-blocking)
- Retry with backoff
- Fall back to simpler eval

**Recommendation**: Non-blocking with retry
- Agent eval tools: return error message, agent decides what to do
- External eval: retry 3x, log failure, continue
- Track eval failure rate as metric

## Success Metrics

Track these to know if evaluation system is working:

1. **Coverage**: % of runs with evaluation results
2. **Agent Usage**: How often agents call eval tools
3. **Score Distribution**: Are scores meaningful (not all 0.5)?
4. **Correlation**: Do eval scores predict human feedback?
5. **Trends**: Do scores improve over time?
6. **Performance**: Eval duration < 5s per run
7. **Reliability**: Eval failure rate < 1%

## Next Steps

1. **Review this plan** - Get feedback on architecture
2. **Start Phase 1** - Create database schema
3. **Build placeholder tools** - Get infrastructure working end-to-end
4. **Implement one eval tool fully** - Prove out the pattern
5. **Iterate** - Expand to other eval types based on learnings
