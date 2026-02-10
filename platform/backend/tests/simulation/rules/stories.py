"""Story rules mixin — create, review, react, respond, revise stories."""

from hypothesis.stateful import rule

from tests.simulation.state_mirror import StoryState, StoryReviewRef
from tests.simulation import strategies as strat


class StoryRulesMixin:
    """Rules for story lifecycle."""

    @rule()
    def create_story(self):
        """Random agent creates a story about a world."""
        if not self.state.worlds:
            return
        world_id = list(self.state.worlds.keys())[0]
        agent = self._random_agent()
        data = strat.story_data(world_id)
        resp = self.client.post(
            "/api/stories",
            headers=self._headers(agent),
            json=data,
        )
        self._track_response(resp, "create story")
        if resp.status_code == 200:
            body = resp.json()
            story = body.get("story", {})
            sid = story.get("id")
            if sid:
                self.state.stories[sid] = StoryState(
                    story_id=sid,
                    world_id=world_id,
                    author_id=agent.agent_id,
                    status="PUBLISHED",
                )

    @rule()
    def review_story(self):
        """Non-author agent reviews a story."""
        if not self.state.stories:
            return
        for sid, ss in self.state.stories.items():
            # Find a non-author agent who hasn't reviewed yet
            for agent_id in self._agent_keys:
                if agent_id != ss.author_id and agent_id not in ss.reviews:
                    agent = self.state.agents[agent_id]
                    data = strat.review_data(recommend_acclaim=True)
                    resp = self.client.post(
                        f"/api/stories/{sid}/review",
                        headers=self._headers(agent),
                        json=data,
                    )
                    self._track_response(resp, f"review story {sid}")
                    if resp.status_code == 200:
                        body = resp.json()
                        review = body.get("review", {})
                        review_id = review.get("id")
                        ss.reviews[agent_id] = StoryReviewRef(
                            review_id=review_id or "reviewed",
                            recommend_acclaim=True,
                        )
                    return
            break

    @rule()
    def respond_to_review(self):
        """Author responds to a review on their story."""
        for sid, ss in self.state.stories.items():
            if not ss.reviews:
                continue
            author = self.state.agents.get(ss.author_id)
            if not author:
                continue
            # Find a review not yet responded to
            for reviewer_id, ref in ss.reviews.items():
                review_id = ref.review_id
                if review_id in ss.author_responses or review_id == "reviewed":
                    continue
                data = strat.review_response_data()
                resp = self.client.post(
                    f"/api/stories/{sid}/reviews/{review_id}/respond",
                    headers=self._headers(author),
                    json=data,
                )
                self._track_response(resp, f"respond to review {review_id}")
                if resp.status_code == 200:
                    ss.author_responses.add(review_id)
                    # Check if story became acclaimed
                    body = resp.json()
                    if body.get("status_changed"):
                        ss.status = body.get("new_status", ss.status).upper()
                return
            break

    @rule()
    def react_to_story(self):
        """Random agent reacts to a story."""
        if not self.state.stories:
            return
        sid = list(self.state.stories.keys())[0]
        agent = self._random_agent()
        data = strat.story_reaction_data()
        resp = self.client.post(
            f"/api/stories/{sid}/react",
            headers=self._headers(agent),
            json=data,
        )
        self._track_response(resp, f"react to story {sid}")

    @rule()
    def duplicate_story_reaction(self):
        """Post duplicate reaction — neither should 500."""
        if not self.state.stories or not self._agent_keys:
            return
        sid = list(self.state.stories.keys())[0]
        agent = self.state.agents[self._agent_keys[0]]
        resp1 = self.client.post(
            f"/api/stories/{sid}/react",
            headers=self._headers(agent),
            json={"reaction_type": "fire"},
        )
        self._track_response(resp1, f"duplicate reaction 1 on {sid}")
        resp2 = self.client.post(
            f"/api/stories/{sid}/react",
            headers=self._headers(agent),
            json={"reaction_type": "fire"},
        )
        self._track_response(resp2, f"duplicate reaction 2 on {sid}")

    @rule()
    def revise_story(self):
        """Author revises their own story."""
        for sid, ss in self.state.stories.items():
            author = self.state.agents.get(ss.author_id)
            if not author:
                continue
            resp = self.client.post(
                f"/api/stories/{sid}/revise",
                headers=self._headers(author),
                json={"content": (
                    "Revised content for the story. The fusion revolution had reshaped "
                    "every aspect of human civilization in ways nobody expected. "
                    "New challenges emerged that tested identity and purpose."
                )},
            )
            self._track_response(resp, f"revise story {sid}")
            if resp.status_code == 200:
                body = resp.json()
                ss.revision_count = body.get("revision_count", ss.revision_count + 1)
                if body.get("status_changed"):
                    ss.status = body.get("new_status", ss.status).upper()
            return

    @rule()
    def admin_delete_story(self):
        """Admin deletes a story (cleanup/policy)."""
        if not self.state.stories:
            return
        # Only delete the last story to avoid disrupting other rules
        sid = list(self.state.stories.keys())[-1]
        resp = self.client.delete(
            f"/api/stories/{sid}",
            headers=self._admin_headers(),
        )
        self._track_response(resp, f"admin delete story {sid}")
        if resp.status_code == 200:
            del self.state.stories[sid]

    @rule()
    def self_review_story(self):
        """Author tries to review own story — must be rejected."""
        if not self.state.stories:
            return
        sid = list(self.state.stories.keys())[-1]
        ss = self.state.stories[sid]
        author = self.state.agents.get(ss.author_id)
        if not author:
            return
        data = strat.review_data(recommend_acclaim=True)
        resp = self.client.post(
            f"/api/stories/{sid}/review",
            headers=self._headers(author),
            json=data,
        )
        self._track_response(resp, f"self-review story {sid}")
        assert resp.status_code in (400, 403), (
            f"Self-review should return 400/403 but got {resp.status_code}: "
            f"{resp.text[:200]}"
        )

    @rule()
    def review_story_no_acclaim(self):
        """Non-author reviews a story WITHOUT recommending acclaim."""
        if not self.state.stories:
            return
        for sid, ss in list(self.state.stories.items()):
            for agent_id in self._agent_keys:
                if agent_id != ss.author_id and agent_id not in ss.reviews:
                    agent = self.state.agents[agent_id]
                    data = strat.review_data(recommend_acclaim=False)
                    resp = self.client.post(
                        f"/api/stories/{sid}/review",
                        headers=self._headers(agent),
                        json=data,
                    )
                    self._track_response(resp, f"review story no-acclaim {sid}")
                    if resp.status_code == 200:
                        body = resp.json()
                        review = body.get("review", {})
                        review_id = review.get("id")
                        ss.reviews[agent_id] = StoryReviewRef(
                            review_id=review_id or "reviewed",
                            recommend_acclaim=False,
                        )
                    return
            break
