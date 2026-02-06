"""Social rules mixin — react, follow, comment."""

from hypothesis.stateful import rule

from tests.simulation import strategies as strat


class SocialRulesMixin:
    """Rules for social interactions."""

    @rule()
    def react_to_world(self):
        """Random agent reacts to a world."""
        if not self.state.worlds:
            return
        world_id = list(self.state.worlds.keys())[0]
        agent = self._random_agent()
        data = strat.social_reaction_data(target_type="world", target_id=world_id)
        resp = self.client.post(
            "/api/social/react",
            headers=self._headers(agent),
            json=data,
        )
        self._track_response(resp, f"react to world {world_id}")

    @rule()
    def follow_world(self):
        """Random agent follows a world."""
        if not self.state.worlds:
            return
        world_id = list(self.state.worlds.keys())[0]
        agent = self._random_agent()
        data = strat.follow_data(target_type="world", target_id=world_id)
        resp = self.client.post(
            "/api/social/follow",
            headers=self._headers(agent),
            json=data,
        )
        self._track_response(resp, f"follow world {world_id}")

    @rule()
    def unfollow_world(self):
        """Random agent unfollows a world."""
        if not self.state.worlds:
            return
        world_id = list(self.state.worlds.keys())[0]
        agent = self._random_agent()
        resp = self.client.post(
            "/api/social/unfollow",
            headers=self._headers(agent),
            json={"target_type": "world", "target_id": world_id},
        )
        self._track_response(resp, f"unfollow world {world_id}")

    @rule()
    def post_comment(self):
        """Random agent comments on a world."""
        if not self.state.worlds:
            return
        world_id = list(self.state.worlds.keys())[0]
        agent = self._random_agent()
        data = strat.comment_data(target_type="world", target_id=world_id)
        resp = self.client.post(
            "/api/social/comment",
            headers=self._headers(agent),
            json=data,
        )
        self._track_response(resp, f"comment on world {world_id}")
