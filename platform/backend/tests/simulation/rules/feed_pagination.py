"""Feed pagination rules mixin — tests cursor-based pagination correctness.

This closes a harness gap: the ternary precedence bug (commit a69909d) was latent
because no test ever passed a cursor parameter to /api/feed.

These tests verify:
1. First page fetches without cursor
2. Cursor extraction and next page fetch
3. No item ID overlap between pages
4. Chronological ordering preserved across pages (intra-page and cross-page)
5. Edge case: cursor past all results returns 200 with empty items
6. Cursor is a valid ISO timestamp
"""

from datetime import datetime

from hypothesis.stateful import rule

from tests.simulation.rules.base import parse_sse_feed


class FeedPaginationRulesMixin:
    """Rules for testing feed pagination behavior."""

    @rule()
    def feed_pagination_no_overlap(self):
        """Feed pagination returns no duplicate item IDs across pages."""
        resp1 = self.client.get("/api/feed/stream?limit=5")
        self._track_response(resp1, "feed page 1")

        if resp1.status_code != 200:
            return  # Feed may be empty or endpoint unavailable

        data1 = parse_sse_feed(resp1.text)
        items1 = data1.get("items", [])
        cursor = data1.get("next_cursor")

        # If no cursor, fewer than limit items exist — nothing to paginate
        if not cursor:
            return

        resp2 = self.client.get(f"/api/feed/stream?limit=5&cursor={cursor}")
        self._track_response(resp2, "feed page 2")

        if resp2.status_code != 200:
            return

        data2 = parse_sse_feed(resp2.text)
        items2 = data2.get("items", [])

        ids1 = {item["id"] for item in items1}
        ids2 = {item["id"] for item in items2}

        overlap = ids1.intersection(ids2)
        assert not overlap, (
            f"Feed pagination returned duplicate items across pages: {overlap}. "
            f"This indicates the cursor logic is broken (ternary precedence bug or similar)."
        )

    @rule()
    def feed_pagination_chronological(self):
        """Feed items are in descending sort_date order within and across pages."""
        resp1 = self.client.get("/api/feed/stream?limit=5")
        self._track_response(resp1, "feed page 1 chronological")

        if resp1.status_code != 200:
            return

        data1 = parse_sse_feed(resp1.text)
        items1 = data1.get("items", [])
        cursor = data1.get("next_cursor")

        if not cursor or not items1:
            return

        # Validate intra-page ordering on page 1
        dates1 = [item.get("sort_date") for item in items1]
        if all(dates1):
            parsed1 = [datetime.fromisoformat(d) for d in dates1]
            for i in range(len(parsed1) - 1):
                assert parsed1[i] >= parsed1[i + 1], (
                    f"Page 1 items {i} and {i + 1} are out of order: "
                    f"{dates1[i]} < {dates1[i + 1]}"
                )

        resp2 = self.client.get(f"/api/feed/stream?limit=5&cursor={cursor}")
        self._track_response(resp2, "feed page 2 chronological")

        if resp2.status_code != 200:
            return

        data2 = parse_sse_feed(resp2.text)
        items2 = data2.get("items", [])

        if not items2:
            return

        # Validate cross-page boundary: last of page 1 >= first of page 2
        last_date_page1 = items1[-1].get("sort_date")
        first_date_page2 = items2[0].get("sort_date")

        if not last_date_page1 or not first_date_page2:
            return

        last_dt = datetime.fromisoformat(last_date_page1)
        first_dt = datetime.fromisoformat(first_date_page2)

        assert last_dt >= first_dt, (
            f"Feed pagination broke chronological ordering: "
            f"last item of page 1 ({last_date_page1}) is older than "
            f"first item of page 2 ({first_date_page2})"
        )

    @rule()
    def feed_pagination_exhausted_cursor(self):
        """Cursor past all results returns 200 with empty items (no crash)."""
        past_cursor = "1970-01-01T00:00:00"
        resp = self.client.get(f"/api/feed/stream?limit=5&cursor={past_cursor}")
        self._track_response(resp, "feed exhausted cursor")

        assert resp.status_code == 200, (
            f"Feed with exhausted cursor should return 200, "
            f"got {resp.status_code}: {resp.text[:200]}"
        )
        data = parse_sse_feed(resp.text)
        assert "items" in data, "Response missing 'items' key"

    @rule()
    def feed_pagination_cursor_format(self):
        """Cursor returned by feed is a valid ISO timestamp."""
        resp = self.client.get("/api/feed/stream?limit=5")
        self._track_response(resp, "feed cursor format")

        if resp.status_code != 200:
            return

        data = parse_sse_feed(resp.text)
        cursor = data.get("next_cursor")

        if not cursor:
            return  # No cursor when fewer than limit items exist

        try:
            # Cursor format: "ISO_TIMESTAMP~UUID" (or legacy "|" separator)
            sep = "~" if "~" in cursor else "|" if "|" in cursor else None
            if sep:
                ts_part, id_part = cursor.split(sep, 1)
                datetime.fromisoformat(ts_part.replace("Z", "+00:00"))
                from uuid import UUID as _UUID
                _UUID(id_part)  # Validates UUID format
            else:
                datetime.fromisoformat(cursor.replace("Z", "+00:00"))
        except (ValueError, AttributeError) as e:
            raise AssertionError(
                f"Feed cursor is not valid (expected 'ISO_TIMESTAMP~UUID'): {cursor} — {e}"
            )
