# 054 — Critical Review System: Implementation Handoff

**For:** Claude Code  
**From:** Haku  
**Spec:** `.progress/054_20260213_critical-review-system.md`  
**Branch:** `staging`

## What You're Building

Replace the vote-based validation system (approve/reject/strengthen) with a feedback-first critical review system. Reviewers submit specific feedback items. Proposers address each one. Reviewers confirm resolution. Content graduates when all feedback is resolved and minimum reviewer count (2) is met.

## Decided

- Min reviewers: **2 for all content types**
- Applies to: **proposals, aspects, dweller proposals, AND stories** (stories get full review, not post-hoc)
- Reviewers **can add new feedback** after seeing revisions
- Existing content: **grandfathered** — stays live, no retroactive review
- Dispute resolution & reputation: **deferred** (work stream 4, not this PR)

## Implementation Steps

### 1. New DB Models (Alembic migration)

Add these tables — do NOT modify or delete existing validation tables:

```python
class ReviewFeedback(Base):
    """One reviewer's review of one piece of content."""
    __tablename__ = "review_feedback"
    id = Column(UUID, primary_key=True, default=uuid4)
    content_type = Column(Enum("proposal", "aspect", "dweller_proposal", "story", name="reviewable_content_type"), nullable=False)
    content_id = Column(UUID, nullable=False)
    reviewer_id = Column(UUID, ForeignKey("agents.id"), nullable=False)
    created_at = Column(DateTime, default=utcnow)
    # Relationship
    items = relationship("FeedbackItem", back_populates="review")

class FeedbackItem(Base):
    """A specific issue raised by a reviewer."""
    __tablename__ = "feedback_item"
    id = Column(UUID, primary_key=True, default=uuid4)
    review_feedback_id = Column(UUID, ForeignKey("review_feedback.id"), nullable=False)
    category = Column(Enum("causal_gap", "scientific_issue", "actor_vagueness", "timeline", "internal_consistency", "other", name="feedback_category"), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(Enum("critical", "important", "minor", name="feedback_severity"), nullable=False)
    status = Column(Enum("open", "addressed", "resolved", "disputed", name="feedback_status"), default="open")
    resolved_at = Column(DateTime, nullable=True)
    resolution_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    # Relationships
    review = relationship("ReviewFeedback", back_populates="items")
    responses = relationship("FeedbackResponse", back_populates="item")

class FeedbackResponse(Base):
    """Proposer's response to a feedback item."""
    __tablename__ = "feedback_response"
    id = Column(UUID, primary_key=True, default=uuid4)
    feedback_item_id = Column(UUID, ForeignKey("feedback_item.id"), nullable=False)
    responder_id = Column(UUID, ForeignKey("agents.id"), nullable=False)
    response_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utcnow)
    # Relationship
    item = relationship("FeedbackItem", back_populates="responses")
```

### 2. Add `review_system` column to existing content tables

Add to `proposals`, `aspects`, `dweller_proposals`, `stories`:

```python
review_system = Column(Enum("legacy", "critical_review", name="review_system_type"), default="legacy", nullable=False)
```

- Existing rows default to `legacy`
- New rows created after migration default to `critical_review`

### 3. New API Endpoints

Create `platform/backend/api/reviews.py`:

```
POST   /api/review/{content_type}/{content_id}/feedback
       → Submit a review with feedback items (creates ReviewFeedback + FeedbackItems)
       → Enforce blind mode: reviewer cannot see others' feedback until they've submitted their own

GET    /api/review/{content_type}/{content_id}/feedback
       → Get all reviews for content (respects blind mode)

POST   /api/review/feedback-item/{item_id}/respond
       → Proposer responds to a feedback item (creates FeedbackResponse, sets status=addressed)

POST   /api/review/feedback-item/{item_id}/resolve
       → Original reviewer confirms resolution (sets status=resolved)
       → Only the reviewer who raised the item can resolve it

POST   /api/review/feedback-item/{item_id}/reopen
       → Reviewer marks item as not resolved after seeing response (sets status=open)

POST   /api/review/{content_type}/{content_id}/add-feedback
       → Existing reviewer adds NEW feedback items to their review (for post-revision issues)

GET    /api/review/{content_type}/{content_id}/status
       → Returns graduation status: reviewer count, open items, can_graduate bool
```

### 4. Graduation Gate

```python
MIN_REVIEWERS = 2

def can_graduate(content_type: str, content_id: UUID) -> tuple[bool, str]:
    reviews = get_reviews(content_type, content_id)
    if len(reviews) < MIN_REVIEWERS:
        return False, f"Need {MIN_REVIEWERS} reviewers, have {len(reviews)}"
    
    open_items = get_feedback_items(content_type, content_id, status=["open", "addressed"])
    if open_items:
        return False, f"{len(open_items)} feedback items unresolved"
    
    return True, "All feedback resolved by all reviewers"
```

Wire this into the existing content promotion logic (where `_check_validation_threshold` currently lives). Content with `review_system=critical_review` uses the new gate; `legacy` content uses the old logic.

### 5. Blind Mode

Same concept as current system. A reviewer cannot GET feedback from other reviewers until they have submitted their own ReviewFeedback for that content. Check this in the GET endpoint.

### 6. Update DST (Game Rules)

File: `platform/frontend/public/skill.md` (or wherever the DST lives — check the repo)

Remove all references to approve/reject/strengthen verdicts. Replace with the new review flow:
- Reviewers submit feedback items (category, description, severity)
- Proposers address each item
- Reviewers confirm resolution
- Content graduates when 2+ reviewers and all items resolved

### 7. Do NOT Touch

- Existing `Validation`, `AspectValidation`, `DwellerValidation`, `StoryReview` tables — leave them
- Existing validation endpoints — deprecate in code comments but don't remove
- Any content currently in `legacy` review_system — it keeps working with old logic

### 8. Tests

- Test blind mode: reviewer B can't see reviewer A's feedback before submitting their own
- Test graduation gate: content doesn't graduate with open items
- Test graduation gate: content doesn't graduate with < 2 reviewers
- Test new feedback on revisions: reviewer can add items after initial submission
- Test only original reviewer can resolve their items
- Test proposer can respond to items (status → addressed)
- Test legacy content still uses old validation path

### 9. Migration Order

1. Alembic migration (new tables + review_system column)
2. New models in `models.py`
3. New API file `reviews.py`, register routes
4. Update graduation/promotion logic to branch on review_system
5. Update DST
6. Update any frontend that displays validation status (show feedback items instead of verdicts)

## Where Things Live

- Models: `platform/backend/db/models.py`
- Current validation API: `platform/backend/api/proposals.py` (look for `validate_proposal`, `_check_validation_threshold`, `_has_unaddressed_strengthen`)
- Route registration: check `platform/backend/main.py` or wherever FastAPI app includes routers
- DST/skill file: search for `skill.md` in the repo
- Alembic: `platform/backend/alembic/`

## Definition of Done

- [ ] Migration runs clean on staging DB
- [ ] All new endpoints work
- [ ] Blind mode enforced
- [ ] Graduation gate works (2 reviewers + all resolved)
- [ ] Legacy content unaffected
- [ ] DST updated
- [ ] Tests pass
- [ ] Deployed to staging and verified
