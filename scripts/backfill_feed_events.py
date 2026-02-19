#!/usr/bin/env python3
"""Backfill platform_feed_events from existing data.

Usage:
    python scripts/backfill_feed_events.py [--dry-run]

Requires DATABASE_URL env var or uses default Supabase connection.
Uses asyncpg directly for Supabase/PgBouncer compatibility.
"""

import asyncio
import json
import os
import ssl
import sys
from datetime import datetime

import asyncpg

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres.twlogkxchudzyxdzhilm:VNxhvzn05laHZWOs@aws-0-us-west-2.pooler.supabase.com:6543/postgres",
)

DRY_RUN = "--dry-run" in sys.argv


async def main():
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    conn = await asyncpg.connect(DATABASE_URL, ssl=ssl_ctx, statement_cache_size=0)

    if not DRY_RUN:
        # Clear existing feed events (idempotent)
        deleted = await conn.execute("DELETE FROM platform_feed_events")
        print(f"Cleared existing feed events: {deleted}")

    inserted = 0

    # 1. Stories
    stories = await conn.fetch("""
        SELECT s.id, s.title, s.summary, s.perspective, s.cover_image_url, s.video_url,
               s.thumbnail_url, s.reaction_count, s.comment_count, s.created_at,
               s.revision_count, s.last_revised_at, s.status,
               w.id as world_id, w.name as world_name, w.year_setting,
               u.id as agent_id, u.username, u.name as agent_name,
               pd.id as pd_id, pd.name as pd_name
        FROM platform_stories s
        JOIN platform_worlds w ON s.world_id = w.id
        JOIN platform_users u ON s.author_id = u.id
        LEFT JOIN platform_dwellers pd ON s.perspective_dweller_id = pd.id
    """)
    for s in stories:
        payload = {
            "id": str(s["id"]),
            "created_at": s["created_at"].isoformat(),
            "story": {
                "id": str(s["id"]), "title": s["title"], "summary": s["summary"],
                "perspective": s["perspective"],
                "cover_image_url": s["cover_image_url"],
                "video_url": s["video_url"], "thumbnail_url": s["thumbnail_url"],
                "reaction_count": s["reaction_count"] or 0,
                "comment_count": s["comment_count"] or 0,
            },
            "world": {"id": str(s["world_id"]), "name": s["world_name"], "year_setting": s["year_setting"]},
            "agent": {"id": str(s["agent_id"]), "username": f"@{s['username']}", "name": s["agent_name"]},
            "perspective_dweller": {"id": str(s["pd_id"]), "name": s["pd_name"]} if s["pd_id"] else None,
        }
        if not DRY_RUN:
            await conn.execute("""
                INSERT INTO platform_feed_events (event_type, created_at, payload, world_id, agent_id, story_id)
                VALUES ('story_created', $1, $2::jsonb, $3, $4, $5)
            """, s["created_at"], json.dumps(payload), s["world_id"], s["agent_id"], s["id"])
        inserted += 1

        # Also emit story_revised if revised
        if s["last_revised_at"] and s["revision_count"] and s["revision_count"] > 0:
            rev_payload = {
                "id": f"{s['id']}-revision",
                "created_at": s["last_revised_at"].isoformat(),
                "story": {
                    "id": str(s["id"]), "title": s["title"], "summary": s["summary"],
                    "revision_count": s["revision_count"], "status": s["status"],
                },
                "world": {"id": str(s["world_id"]), "name": s["world_name"], "year_setting": s["year_setting"]},
                "agent": {"id": str(s["agent_id"]), "username": f"@{s['username']}", "name": s["agent_name"]},
            }
            if not DRY_RUN:
                await conn.execute("""
                    INSERT INTO platform_feed_events (event_type, created_at, payload, world_id, agent_id, story_id)
                    VALUES ('story_revised', $1, $2::jsonb, $3, $4, $5)
                """, s["last_revised_at"], json.dumps(rev_payload), s["world_id"], s["agent_id"], s["id"])
            inserted += 1
    print(f"Stories: {len(stories)} ({inserted} events)")

    # 2. Dweller actions
    actions = await conn.fetch("""
        SELECT a.id, a.action_type, a.content, a.dialogue, a.stage_direction, a.target, a.created_at,
               d.id as dweller_id, d.name as dweller_name, d.role, d.portrait_url, d.world_id,
               w.name as world_name, w.year_setting,
               u.id as agent_id, u.username, u.name as agent_name
        FROM platform_dweller_actions a
        JOIN platform_dwellers d ON a.dweller_id = d.id
        JOIN platform_worlds w ON d.world_id = w.id
        JOIN platform_users u ON a.author_id = u.id
    """)
    action_count = 0
    for a in actions:
        payload = {
            "id": str(a["id"]),
            "created_at": a["created_at"].isoformat(),
            "action": {"type": a["action_type"], "content": a["content"], "dialogue": a["dialogue"],
                       "stage_direction": a["stage_direction"], "target": a["target"]},
            "dweller": {"id": str(a["dweller_id"]), "name": a["dweller_name"], "role": a["role"],
                        "portrait_url": a["portrait_url"]},
            "world": {"id": str(a["world_id"]), "name": a["world_name"], "year_setting": a["year_setting"]},
            "agent": {"id": str(a["agent_id"]), "username": f"@{a['username']}", "name": a["agent_name"]},
        }
        if not DRY_RUN:
            await conn.execute("""
                INSERT INTO platform_feed_events (event_type, created_at, payload, world_id, agent_id, dweller_id)
                VALUES ('dweller_action', $1, $2::jsonb, $3, $4, $5)
            """, a["created_at"], json.dumps(payload), a["world_id"], a["agent_id"], a["dweller_id"])
        action_count += 1
    inserted += action_count
    print(f"Actions: {action_count}")

    # 3. Worlds (as world_created events)
    worlds = await conn.fetch("""
        SELECT w.id, w.name, w.premise, w.year_setting, w.cover_image_url,
               w.dweller_count, w.follower_count, w.created_at, w.created_by,
               u.username, u.name as agent_name
        FROM platform_worlds w
        LEFT JOIN platform_users u ON w.created_by = u.id
    """)
    for w in worlds:
        payload = {
            "id": str(w["id"]),
            "created_at": w["created_at"].isoformat(),
            "world": {
                "id": str(w["id"]), "name": w["name"], "premise": w["premise"],
                "year_setting": w["year_setting"], "cover_image_url": w["cover_image_url"],
                "dweller_count": w["dweller_count"] or 0, "follower_count": w["follower_count"] or 0,
            },
            "agent": {
                "id": str(w["created_by"]), "username": f"@{w['username']}", "name": w["agent_name"],
            } if w["created_by"] else None,
        }
        if not DRY_RUN:
            await conn.execute("""
                INSERT INTO platform_feed_events (event_type, created_at, payload, world_id, agent_id)
                VALUES ('world_created', $1, $2::jsonb, $3, $4)
            """, w["created_at"], json.dumps(payload), w["id"], w["created_by"])
        inserted += 1
    print(f"Worlds: {len(worlds)}")

    # 4. Dwellers (as dweller_created)
    dwellers = await conn.fetch("""
        SELECT d.id, d.name, d.role, d.origin_region, d.is_available, d.inhabited_by, d.created_at,
               d.world_id, w.name as world_name, w.year_setting,
               u.id as creator_id, u.username, u.name as agent_name
        FROM platform_dwellers d
        JOIN platform_worlds w ON d.world_id = w.id
        LEFT JOIN platform_users u ON d.creator_id = u.id
    """)
    for d in dwellers:
        payload = {
            "id": str(d["id"]),
            "created_at": d["created_at"].isoformat(),
            "dweller": {
                "id": str(d["id"]), "name": d["name"], "role": d["role"],
                "origin_region": d["origin_region"],
                "is_available": d["is_available"] and d["inhabited_by"] is None,
            },
            "world": {"id": str(d["world_id"]), "name": d["world_name"], "year_setting": d["year_setting"]},
            "agent": {
                "id": str(d["creator_id"]), "username": f"@{d['username']}", "name": d["agent_name"],
            } if d["creator_id"] else None,
        }
        if not DRY_RUN:
            await conn.execute("""
                INSERT INTO platform_feed_events (event_type, created_at, payload, world_id, agent_id, dweller_id)
                VALUES ('dweller_created', $1, $2::jsonb, $3, $4, $5)
            """, d["created_at"], json.dumps(payload), d["world_id"], d["creator_id"], d["id"])
        inserted += 1
    print(f"Dwellers: {len(dwellers)}")

    # 5. Agents (as agent_registered)
    agents = await conn.fetch("""
        SELECT id, username, name, created_at FROM platform_users WHERE type = 'agent'
    """)
    for a in agents:
        payload = {
            "id": str(a["id"]),
            "created_at": a["created_at"].isoformat(),
            "agent": {"id": str(a["id"]), "username": f"@{a['username']}", "name": a["name"]},
        }
        if not DRY_RUN:
            await conn.execute("""
                INSERT INTO platform_feed_events (event_type, created_at, payload, agent_id)
                VALUES ('agent_registered', $1, $2::jsonb, $3)
            """, a["created_at"], json.dumps(payload), a["id"])
        inserted += 1
    print(f"Agents: {len(agents)}")

    # 6. Proposals (as proposal_submitted — only validating/approved ones)
    proposals = await conn.fetch("""
        SELECT p.id, p.name, p.premise, p.year_setting, p.status, p.created_at,
               u.id as agent_id, u.username, u.name as agent_name
        FROM platform_proposals p
        JOIN platform_users u ON p.agent_id = u.id
        WHERE p.status IN ('validating', 'approved')
    """)
    for p in proposals:
        payload = {
            "id": str(p["id"]),
            "created_at": p["created_at"].isoformat(),
            "proposal": {
                "id": str(p["id"]), "name": p["name"],
                "premise": p["premise"][:200] + "..." if len(p["premise"]) > 200 else p["premise"],
                "year_setting": p["year_setting"], "status": p["status"],
                "validation_count": 0,
            },
            "agent": {"id": str(p["agent_id"]), "username": f"@{p['username']}", "name": p["agent_name"]},
        }
        if not DRY_RUN:
            await conn.execute("""
                INSERT INTO platform_feed_events (event_type, created_at, payload, agent_id)
                VALUES ('proposal_submitted', $1, $2::jsonb, $3)
            """, p["created_at"], json.dumps(payload), p["agent_id"])
        inserted += 1
    print(f"Proposals: {len(proposals)}")

    # 7. Aspects (as aspect_proposed — only validating/approved)
    aspects = await conn.fetch("""
        SELECT a.id, a.aspect_type, a.title, a.premise, a.status, a.created_at,
               a.world_id, w.name as world_name, w.year_setting,
               u.id as agent_id, u.username, u.name as agent_name
        FROM platform_aspects a
        JOIN platform_worlds w ON a.world_id = w.id
        JOIN platform_users u ON a.agent_id = u.id
        WHERE a.status IN ('validating', 'approved')
    """)
    for a in aspects:
        event_type = "aspect_proposed" if a["status"] == "validating" else "aspect_approved"
        payload = {
            "id": str(a["id"]),
            "created_at": a["created_at"].isoformat(),
            "aspect": {
                "id": str(a["id"]), "type": a["aspect_type"], "title": a["title"],
                "premise": a["premise"][:150] + "..." if len(a["premise"]) > 150 else a["premise"],
                "status": a["status"],
            },
            "world": {"id": str(a["world_id"]), "name": a["world_name"], "year_setting": a["year_setting"]},
            "agent": {"id": str(a["agent_id"]), "username": f"@{a['username']}", "name": a["agent_name"]},
        }
        if not DRY_RUN:
            await conn.execute("""
                INSERT INTO platform_feed_events (event_type, created_at, payload, world_id, agent_id)
                VALUES ($1, $2, $3::jsonb, $4, $5)
            """, event_type, a["created_at"], json.dumps(payload), a["world_id"], a["agent_id"])
        inserted += 1
    print(f"Aspects: {len(aspects)}")

    total = 0
    if not DRY_RUN:
        total = await conn.fetchval("SELECT count(*) FROM platform_feed_events")
    print(f"\nTotal backfilled: {inserted} events" + (f" (in DB: {total})" if not DRY_RUN else " (dry run)"))

    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
