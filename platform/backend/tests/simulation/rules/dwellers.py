"""Dweller rules mixin — create, claim, release, act, memory."""

from hypothesis.stateful import rule

from tests.simulation.state_mirror import DwellerState, ActionRef
from tests.simulation import strategies as strat


def _act_with_context_sync(client, dweller_id: str, headers: dict, action_data: dict):
    """Two-phase action flow for sync TestClient: get context token, then act."""
    target = action_data.get("target")
    ctx_body = {"target": target} if target else None
    ctx_resp = client.post(
        f"/api/dwellers/{dweller_id}/act/context",
        headers=headers,
        json=ctx_body,
    )
    if ctx_resp.status_code != 200:
        return ctx_resp
    token = ctx_resp.json()["context_token"]
    body = {**action_data, "context_token": token}
    return client.post(
        f"/api/dwellers/{dweller_id}/act",
        headers=headers,
        json=body,
    )


class DwellerRulesMixin:
    """Rules for dweller lifecycle and actions."""

    @rule()
    def add_region(self):
        """Any agent adds a region to a world."""
        if not self.state.worlds:
            return
        world_id = list(self.state.worlds.keys())[0]
        world = self.state.worlds[world_id]
        agent = self._random_agent()
        data = strat.region_data()
        resp = self.client.post(
            f"/api/dwellers/worlds/{world_id}/regions",
            headers=self._headers(agent),
            json=data,
        )
        self._track_response(resp, f"add region to {world_id}")
        if resp.status_code == 200:
            world.regions.append(data["name"])

    @rule()
    def create_dweller(self):
        """Any agent creates a dweller in a world with regions."""
        world = self._first_world_with_regions()
        if not world:
            return
        agent = self._random_agent()
        region_name = world.regions[0]
        data = strat.dweller_data(region_name)
        resp = self.client.post(
            f"/api/dwellers/worlds/{world.world_id}/dwellers",
            headers=self._headers(agent),
            json=data,
        )
        self._track_response(resp, f"create dweller in {world.world_id}")
        if resp.status_code == 200:
            body = resp.json()
            dweller_data = body.get("dweller", {})
            did = dweller_data.get("id")
            if did:
                self.state.dwellers[did] = DwellerState(
                    dweller_id=did,
                    world_id=world.world_id,
                    origin_region=region_name,
                )

    @rule()
    def claim_dweller(self):
        """Random agent claims an available dweller."""
        if not self.state.dwellers:
            return
        for did, ds in list(self.state.dwellers.items()):
            if ds.claimed_by is not None:
                continue
            agent = self._random_agent()
            resp = self.client.post(
                f"/api/dwellers/{did}/claim",
                headers=self._headers(agent),
            )
            self._track_response(resp, f"claim dweller {did}")
            if resp.status_code == 200:
                ds.claimed_by = agent.agent_id
            return

    @rule()
    def release_dweller(self):
        """Agent releases a claimed dweller."""
        if not self.state.dwellers:
            return
        for did, ds in list(self.state.dwellers.items()):
            if ds.claimed_by is None:
                continue
            agent = self.state.agents.get(ds.claimed_by)
            if not agent:
                continue
            resp = self.client.post(
                f"/api/dwellers/{did}/release",
                headers=self._headers(agent),
            )
            self._track_response(resp, f"release dweller {did}")
            if resp.status_code == 200:
                ds.claimed_by = None
            return

    @rule()
    def take_action(self):
        """Agent takes action with a claimed dweller."""
        if not self.state.dwellers:
            return
        for did, ds in list(self.state.dwellers.items()):
            if ds.claimed_by is None:
                continue
            agent = self.state.agents.get(ds.claimed_by)
            if not agent:
                continue
            data = strat.action_data()
            resp = _act_with_context_sync(
                self.client, did, self._headers(agent), data,
            )
            self._track_response(resp, f"action on dweller {did}")
            if resp.status_code == 200:
                body = resp.json()
                action_info = body.get("action", {})
                aid = action_info.get("id")
                if aid:
                    self.state.actions[aid] = ActionRef(
                        action_id=aid,
                        dweller_id=did,
                        actor_id=agent.agent_id,
                        importance=data["importance"],
                    )
            return

    @rule()
    def take_high_importance_action(self):
        """Agent takes a high-importance action (escalation-eligible)."""
        if not self.state.dwellers:
            return
        for did, ds in list(self.state.dwellers.items()):
            if ds.claimed_by is None:
                continue
            agent = self.state.agents.get(ds.claimed_by)
            if not agent:
                continue
            data = strat.high_importance_action_data()
            resp = _act_with_context_sync(
                self.client, did, self._headers(agent), data,
            )
            self._track_response(resp, f"high-importance action on dweller {did}")
            if resp.status_code == 200:
                body = resp.json()
                action_info = body.get("action", {})
                aid = action_info.get("id")
                if aid:
                    self.state.actions[aid] = ActionRef(
                        action_id=aid,
                        dweller_id=did,
                        actor_id=agent.agent_id,
                        importance=data["importance"],
                    )
            return
