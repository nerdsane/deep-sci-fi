"""Arc rules mixin — trigger arc detection."""

from hypothesis.stateful import rule


class ArcRulesMixin:
    """Rules for story arc lifecycle."""

    @rule()
    def detect_arcs(self):
        """Admin triggers arc detection."""
        resp = self.client.post(
            "/api/arcs/detect",
            headers=self._admin_headers(),
        )
        self._track_response(resp, "detect arcs")
        # Arc detection may return 200 with empty arcs if no stories exist
        assert resp.status_code == 200, (
            f"Arc detection should succeed but got {resp.status_code}: "
            f"{resp.text[:200]}"
        )
