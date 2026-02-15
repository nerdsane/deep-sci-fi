"""One-shot: graduate proposals that meet all critical review criteria.

Proposals with 2+ reviewers and all feedback items resolved should have
auto-graduated but the trigger didn't exist until commit 6307d2e.
This migration retroactively graduates them.

Revision ID: 0016
Revises: 0015
"""
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
    # - zero open or addressed feedback items
    ready = conn.execute(text("""
        SELECT p.id, p.name, p.premise, p.year_setting, p.causal_chain,
               p.scientific_basis, p.agent_id, p.image_prompt
        FROM platform_proposals p
        WHERE p.status = 'VALIDATING'
          AND (
            SELECT COUNT(DISTINCT rf.reviewer_id)
            FROM review_feedback rf
            WHERE rf.content_type = 'proposal' AND rf.content_id = p.id
          ) >= 2
          AND NOT EXISTS (
            SELECT 1
            FROM feedback_items fi
            JOIN review_feedback rf ON fi.review_id = rf.id
            WHERE rf.content_type = 'proposal' AND rf.content_id = p.id
              AND fi.status IN ('OPEN', 'ADDRESSED')
          )
    """)).fetchall()

    for row in ready:
        pid, name = row[0], row[1]
        premise, year_setting = row[2], row[3]
        causal_chain, scientific_basis = row[4], row[5]
        agent_id, image_prompt = row[6], row[7]

        # Create world
        result = conn.execute(text("""
            INSERT INTO platform_worlds (name, premise, year_setting, causal_chain,
                                         scientific_basis, created_by, proposal_id)
            VALUES (:name, :premise, :year_setting, :causal_chain,
                    :scientific_basis, :created_by, :proposal_id)
            RETURNING id
        """), {
            "name": name, "premise": premise, "year_setting": year_setting,
            "causal_chain": causal_chain, "scientific_basis": scientific_basis,
            "created_by": agent_id, "proposal_id": pid,
        })
        world_id = result.fetchone()[0]

        # Update proposal
        conn.execute(text("""
            UPDATE platform_proposals
            SET status = 'APPROVED', resulting_world_id = :wid, approved_at = NOW()
            WHERE id = :pid
        """), {"wid": world_id, "pid": pid})

        # Queue cover image if prompt exists
        if image_prompt:
            conn.execute(text("""
                INSERT INTO media_generations (requested_by, target_type, target_id,
                                               media_type, prompt, provider)
                VALUES (:agent_id, 'world', :world_id, 'COVER_IMAGE', :prompt, 'grok_imagine_image')
            """), {"agent_id": agent_id, "world_id": world_id, "prompt": image_prompt})

        print(f"  GRADUATED: {name} -> World {world_id}")

    if not ready:
        print("  No proposals ready to graduate.")


def downgrade() -> None:
    # Can't cleanly undo world creation; leave as-is
    pass
