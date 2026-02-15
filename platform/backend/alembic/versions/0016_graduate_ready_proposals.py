"""One-shot: graduate proposals that meet all critical review criteria.

Proposals with 2+ reviewers and all feedback items resolved should have
auto-graduated but the trigger didn't exist yet. This migration
retroactively graduates them.

Revision ID: 0016
Revises: 0015
"""
import json

from alembic import op
from sqlalchemy import text

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Find validating proposals that meet graduation criteria:
    # - 2+ distinct reviewers
    # - zero open or addressed feedback items (all resolved)
    ready = conn.execute(text("""
        SELECT p.id, p.name, p.premise, p.year_setting, p.causal_chain,
               p.scientific_basis, p.agent_id, p.image_prompt
        FROM platform_proposals p
        WHERE p.status = 'VALIDATING'
          AND (
            SELECT COUNT(DISTINCT rf.reviewer_id)
            FROM platform_review_feedback rf
            WHERE rf.content_type = 'proposal' AND rf.content_id = p.id
          ) >= 2
          AND NOT EXISTS (
            SELECT 1
            FROM platform_feedback_items fi
            JOIN platform_review_feedback rf ON fi.review_feedback_id = rf.id
            WHERE rf.content_type = 'proposal' AND rf.content_id = p.id
              AND fi.status IN ('OPEN', 'ADDRESSED')
          )
    """)).fetchall()

    for row in ready:
        pid, name = row[0], row[1]
        premise, year_setting = row[2], row[3]
        causal_chain, scientific_basis = row[4], row[5]
        agent_id, image_prompt = row[6], row[7]

        # Serialize causal_chain — it's JSONB, asyncpg needs a JSON string
        cc_json = json.dumps(causal_chain) if isinstance(causal_chain, (list, dict)) else causal_chain

        # Create world
        result = conn.execute(text("""
            INSERT INTO platform_worlds (name, premise, year_setting, causal_chain,
                                         scientific_basis, created_by, proposal_id)
            VALUES (:name, :premise, :year_setting, CAST(:causal_chain AS jsonb),
                    :scientific_basis, :created_by, :proposal_id)
            RETURNING id
        """), {
            "name": name,
            "premise": premise,
            "year_setting": year_setting,
            "causal_chain": cc_json,
            "scientific_basis": scientific_basis,
            "created_by": agent_id,
            "proposal_id": pid,
        })
        world_id = result.fetchone()[0]

        # Update proposal status
        conn.execute(text("""
            UPDATE platform_proposals
            SET status = 'APPROVED', resulting_world_id = :wid
            WHERE id = :pid
        """), {"wid": world_id, "pid": pid})

        # Queue cover image generation if image_prompt exists
        if image_prompt:
            conn.execute(text("""
                INSERT INTO platform_media_generations
                    (requested_by, target_type, target_id, media_type, prompt, provider)
                VALUES (:agent_id, 'world', :world_id, 'COVER_IMAGE', :prompt, 'grok_imagine_image')
            """), {"agent_id": agent_id, "world_id": world_id, "prompt": image_prompt})

        print(f"  GRADUATED: {name} -> World {world_id}")

    if not ready:
        print("  No proposals ready to graduate.")


def downgrade() -> None:
    pass
