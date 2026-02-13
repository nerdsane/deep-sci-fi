"""Media generation rules mixin — generate cover images and videos."""

import uuid

from hypothesis.stateful import rule

from tests.simulation.state_mirror import MediaGenerationRef
from tests.simulation import strategies as strat


class MediaRulesMixin:
    """Rules for media generation endpoints."""

    @rule()
    def generate_world_cover_image(self):
        """Agent requests a cover image for a world."""
        if not self.state.worlds:
            return
        world_id = self._first_world_id()
        agent = self._random_agent()
        data = strat.image_prompt_data()
        resp = self.client.post(
            f"/api/media/worlds/{world_id}/cover-image",
            headers=self._headers(agent),
            json=data,
        )
        self._track_response(resp, f"generate world cover {world_id}")
        if resp.status_code == 200:
            body = resp.json()
            gen_id = body.get("generation_id")
            if gen_id:
                self.state.media_generations[gen_id] = MediaGenerationRef(
                    generation_id=gen_id,
                    target_type="world",
                    target_id=world_id,
                    media_type="cover_image",
                    requested_by=agent.agent_id,
                )

    @rule()
    def generate_story_cover_image(self):
        """Agent requests a cover image for a story."""
        if not self.state.stories:
            return
        sid = list(self.state.stories.keys())[0]
        agent = self._random_agent()
        data = strat.image_prompt_data()
        resp = self.client.post(
            f"/api/media/stories/{sid}/cover-image",
            headers=self._headers(agent),
            json=data,
        )
        self._track_response(resp, f"generate story cover {sid}")
        if resp.status_code == 200:
            body = resp.json()
            gen_id = body.get("generation_id")
            if gen_id:
                self.state.media_generations[gen_id] = MediaGenerationRef(
                    generation_id=gen_id,
                    target_type="story",
                    target_id=sid,
                    media_type="cover_image",
                    requested_by=agent.agent_id,
                )

    @rule()
    def generate_story_video(self):
        """Agent requests a video for a story."""
        if not self.state.stories:
            return
        sid = list(self.state.stories.keys())[0]
        agent = self._random_agent()
        data = strat.video_prompt_data()
        resp = self.client.post(
            f"/api/media/stories/{sid}/video",
            headers=self._headers(agent),
            json=data,
        )
        self._track_response(resp, f"generate story video {sid}")
        if resp.status_code == 200:
            body = resp.json()
            gen_id = body.get("generation_id")
            if gen_id:
                self.state.media_generations[gen_id] = MediaGenerationRef(
                    generation_id=gen_id,
                    target_type="story",
                    target_id=sid,
                    media_type="video",
                    requested_by=agent.agent_id,
                )

    @rule()
    def trigger_backfill(self):
        """Admin triggers media backfill for uncovered content."""
        data = strat.backfill_data()
        resp = self.client.post(
            "/api/media/backfill",
            headers=self._admin_headers(),
            json=data,
        )
        self._track_response(resp, "backfill media")

    @rule()
    def trigger_backfill_stories_only(self):
        """Admin triggers backfill with include_stories=False."""
        resp = self.client.post(
            "/api/media/backfill",
            headers=self._admin_headers(),
            json={"include_stories": False},
        )
        self._track_response(resp, "backfill media (no stories)")

    @rule()
    def poll_generation_status(self):
        """Poll the status of a media generation.

        No auth headers — the status endpoint is intentionally public
        so agents can poll without re-authenticating.
        """
        if not self.state.media_generations:
            return
        gen_id = list(self.state.media_generations.keys())[0]
        resp = self.client.get(
            f"/api/media/{gen_id}/status",
        )
        self._track_response(resp, f"poll generation {gen_id}")

    # -------------------------------------------------------------------------
    # Negative tests: verify proper error handling without 500s
    # -------------------------------------------------------------------------

    @rule()
    def generate_cover_for_nonexistent_world(self):
        """Attempt to generate a cover for a nonexistent world — must return 404."""
        agent = self._random_agent()
        fake_id = str(uuid.uuid4())
        resp = self.client.post(
            f"/api/media/worlds/{fake_id}/cover-image",
            headers=self._headers(agent),
            json=strat.image_prompt_data(),
        )
        self._track_response(resp, f"cover for nonexistent world {fake_id}")
        assert resp.status_code == 404, (
            f"Expected 404 for nonexistent world, got {resp.status_code}"
        )

    @rule()
    def generate_cover_for_nonexistent_story(self):
        """Attempt to generate a cover for a nonexistent story — must return 404."""
        agent = self._random_agent()
        fake_id = str(uuid.uuid4())
        resp = self.client.post(
            f"/api/media/stories/{fake_id}/cover-image",
            headers=self._headers(agent),
            json=strat.image_prompt_data(),
        )
        self._track_response(resp, f"cover for nonexistent story {fake_id}")
        assert resp.status_code == 404, (
            f"Expected 404 for nonexistent story, got {resp.status_code}"
        )

    @rule()
    def non_admin_backfill(self):
        """Non-admin tries to trigger backfill — must be rejected."""
        agent = self._random_agent()
        resp = self.client.post(
            "/api/media/backfill",
            headers=self._headers(agent),
            json=strat.backfill_data(),
        )
        self._track_response(resp, "non-admin backfill")
        assert resp.status_code in (401, 403), (
            f"Non-admin backfill should return 401/403 but got {resp.status_code}"
        )
