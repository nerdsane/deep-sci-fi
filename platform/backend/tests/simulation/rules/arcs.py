"""Arc rules mixin — trigger arc detection."""

from hypothesis.stateful import rule


class ArcRulesMixin:
    """Rules for story arc lifecycle."""

    @rule()
    def detect_arcs(self):
        """Admin triggers arc detection.

        Uses admin headers; may return 401/403 if admin key has no DB user
        (expected in simulation). Only 500s are tracked as errors.
        """
        resp = self.client.post(
            "/api/arcs/detect",
            headers=self._admin_headers(),
        )
        self._track_response(resp, "detect arcs")
        # Admin auth may fail (401/403) in simulation — that's OK.
        # Only 500s indicate real bugs.
        assert resp.status_code != 500, (
            f"Arc detection returned 500: {resp.text[:200]}"
        )
