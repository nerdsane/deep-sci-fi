"""Notification rules mixin — poll pending, mark read."""

from hypothesis.stateful import rule


class NotificationRulesMixin:
    """Rules for notification lifecycle."""

    @rule()
    def poll_notifications(self):
        """Random agent polls for pending notifications."""
        agent = self._random_agent()
        resp = self.client.get(
            "/api/notifications/pending?mark_as_read=false&limit=10",
            headers=self._headers(agent),
        )
        self._track_response(resp, "poll notifications")
        if resp.status_code == 200:
            body = resp.json()
            notifications = body.get("notifications", [])
            # Store one notification ID for mark_read rule
            if notifications and not hasattr(self, "_pending_notification_ids"):
                self._pending_notification_ids = {}
            if notifications:
                for n in notifications[:3]:
                    nid = n.get("id")
                    if nid:
                        if not hasattr(self, "_pending_notification_ids"):
                            self._pending_notification_ids = {}
                        self._pending_notification_ids[nid] = agent.agent_id

    @rule()
    def process_notifications(self):
        """Admin triggers notification processing (background job)."""
        resp = self.client.post(
            "/api/platform/process-notifications",
            headers=self._admin_headers(),
            json={"batch_size": 10},
        )
        self._track_response(resp, "process notifications")

    @rule()
    def mark_notification_read(self):
        """Agent marks a notification as read."""
        if not hasattr(self, "_pending_notification_ids") or not self._pending_notification_ids:
            return
        nid = list(self._pending_notification_ids.keys())[0]
        agent_id = self._pending_notification_ids[nid]
        agent = self.state.agents.get(agent_id)
        if not agent:
            del self._pending_notification_ids[nid]
            return
        resp = self.client.post(
            f"/api/notifications/{nid}/read",
            headers=self._headers(agent),
        )
        self._track_response(resp, f"mark notification read {nid}")
        # Remove from pending regardless of result (may already be read)
        del self._pending_notification_ids[nid]
