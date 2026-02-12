"""World management rules mixin — admin world deletion."""

import uuid

from hypothesis.stateful import rule


class WorldRulesMixin:
    """Rules for world management endpoints."""

    @rule()
    def admin_delete_world(self):
        """Admin deletes a world — cascades to stories, dwellers, etc."""
        if not self.state.worlds:
            return
        world_id = self._first_world_id()
        resp = self.client.delete(
            f"/api/worlds/{world_id}",
            headers=self._admin_headers(),
        )
        self._track_response(resp, f"admin delete world {world_id}")
        if resp.status_code == 200:
            # Remove world and associated state
            self.state.worlds.pop(world_id, None)
            # Remove stories belonging to this world
            story_ids_to_remove = [
                sid for sid, s in self.state.stories.items()
                if s.world_id == world_id
            ]
            for sid in story_ids_to_remove:
                self.state.stories.pop(sid, None)

    @rule()
    def delete_nonexistent_world(self):
        """Admin tries to delete a nonexistent world — must not 500.

        May return 401 (admin key not in DB), 403, or 404 depending on
        auth configuration. The key invariant is no 500.
        """
        fake_id = str(uuid.uuid4())
        resp = self.client.delete(
            f"/api/worlds/{fake_id}",
            headers=self._admin_headers(),
        )
        self._track_response(resp, f"delete nonexistent world {fake_id}")
        assert resp.status_code in (401, 403, 404), (
            f"Expected 401/403/404 for nonexistent world delete, got {resp.status_code}"
        )

    @rule()
    def non_admin_delete_world(self):
        """Non-admin tries to delete a world — must be rejected."""
        if not self.state.worlds:
            return
        world_id = self._first_world_id()
        agent = self._random_agent()
        resp = self.client.delete(
            f"/api/worlds/{world_id}",
            headers=self._headers(agent),
        )
        self._track_response(resp, f"non-admin delete world {world_id}")
        assert resp.status_code in (401, 403), (
            f"Non-admin delete should return 401/403 but got {resp.status_code}"
        )
