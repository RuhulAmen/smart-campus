"""Database index definitions.

Call ensure_indexes(mongo) once at startup (after a successful DB ping)
to create indexes that are missing. MongoDB's create_index is idempotent:
if the index already exists with the same spec, the call is a no-op.
"""
import logging

logger = logging.getLogger(__name__)


def ensure_indexes(mongo):
    """Create performance and uniqueness indexes for all collections."""
    db = mongo.db
    try:
        # ── users ──
        db.users.create_index("email", unique=True, name="idx_users_email")
        db.users.create_index("student_id", unique=True, name="idx_users_student_id")

        # ── issues ──
        db.issues.create_index("reporter_email", name="idx_issues_reporter_email")
        db.issues.create_index("status", name="idx_issues_status")
        db.issues.create_index(
            [("created_at", -1)], name="idx_issues_created_at_desc"
        )
        db.issues.create_index("facility", name="idx_issues_facility")

        # ── announcements ──
        db.announcements.create_index(
            [("status", 1), ("created_at", -1)],
            name="idx_announcements_status_created",
        )
        db.announcements.create_index("priority", name="idx_announcements_priority")

        # ── facilities ──
        db.facilities.create_index("is_active", name="idx_facilities_is_active")

        logger.info("✅ Database indexes ensured")
    except Exception as e:
        logger.warning("⚠️ Could not create indexes (will retry next startup): %s", e)

