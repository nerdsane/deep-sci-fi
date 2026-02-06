"""Feedback rules mixin — create, upvote feedback."""

from hypothesis.stateful import rule

from tests.simulation.state_mirror import FeedbackState
from tests.simulation import strategies as strat


class FeedbackRulesMixin:
    """Rules for feedback lifecycle."""

    @rule()
    def submit_feedback(self):
        """Random agent submits feedback."""
        agent = self._random_agent()
        data = strat.feedback_data()
        resp = self.client.post(
            "/api/feedback",
            headers=self._headers(agent),
            json=data,
        )
        self._track_response(resp, "submit feedback")
        if resp.status_code == 200:
            body = resp.json()
            fb_data = body.get("feedback", {})
            fid = fb_data.get("id")
            if fid:
                self.state.feedback[fid] = FeedbackState(
                    feedback_id=fid,
                    creator_id=agent.agent_id,
                )

    @rule()
    def upvote_feedback(self):
        """Non-creator agent upvotes feedback."""
        if not self.state.feedback:
            return
        fid = list(self.state.feedback.keys())[0]
        fb = self.state.feedback[fid]
        for agent_id in self._agent_keys:
            if agent_id != fb.creator_id:
                agent = self.state.agents[agent_id]
                resp = self.client.post(
                    f"/api/feedback/{fid}/upvote",
                    headers=self._headers(agent),
                )
                self._track_response(resp, f"upvote feedback {fid}")
                return
