import datetime

from .. import db

# Serbian Wikipedia's mass-edit policy (passed 2026-08-14, see the vote at
# Википедија:Гласање/Ограничавање_масовних_измена_за_не-бот_кориснике):
# a non-bot, non-"user-bot" registered user making this many edits or more
# within any 24-hour window is expected to have requested a temporary
# "user-bot" flag first.
EDIT_THRESHOLD = 300
WINDOW_HOURS = 24

# Groups exempt from the policy: a standing bot flag, or the policy's own
# temporary "user-bot" flag (doesn't exist as a granted group yet -- the
# vote is only a couple of weeks old at time of writing -- but excluding it
# is harmless and future-proof; confirmed live that filtering by a group
# with zero current holders just contributes nothing to the NOT IN list).
EXEMPT_GROUPS = ("bot", "user-bot")


def parse_start(value: str) -> datetime.datetime:
    """Parses an HTML <input type="datetime-local"> value
    ("YYYY-MM-DDTHH:MM")."""
    return datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M")


def _mw_timestamp(dt: datetime.datetime) -> str:
    return dt.strftime("%Y%m%d%H%M%S")


def mass_editors(start: datetime.datetime, db_host: str):
    """(username, edit_count) for every non-exempt registered user whose
    edit count in [start, start + 24h) meets EDIT_THRESHOLD, ordered by
    edit count descending.

    Counts from recentchanges rather than revision, because that's the only
    table carrying a per-edit bot flag (rc_bot): edits a user marked as bot
    edits themselves (e.g. via the bot=1 API parameter or markbotedits)
    don't count toward the threshold, even if the user isn't in a bot group.
    Only real edits and page creations count (rc_source mw.edit/mw.new) --
    logged actions (moves, uploads, protections...) and their null
    revisions are ignored, as are categorization and Wikidata entries.

    On top of that, users currently in EXEMPT_GROUPS are excluded
    entirely, regardless of how their individual edits were flagged.

    recentchanges only covers the last RC_MAX_AGE (~30 days on Wikimedia
    wikis); see oldest_available() for detecting windows older than that.
    """
    end = start + datetime.timedelta(hours=WINDOW_HOURS)
    exempt_placeholders = ", ".join(["%s"] * len(EXEMPT_GROUPS))
    with db.connect(db_host, db="srwiki_p") as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT actor_name, COUNT(*) AS edit_count
                FROM recentchanges rc
                JOIN actor a ON rc.rc_actor = a.actor_id
                WHERE rc.rc_timestamp >= %s AND rc.rc_timestamp < %s
                AND rc.rc_source IN ('mw.edit', 'mw.new')
                AND rc.rc_bot = 0
                AND a.actor_user IS NOT NULL
                AND a.actor_user NOT IN (
                    SELECT ug_user FROM user_groups WHERE ug_group IN ({exempt_placeholders})
                )
                GROUP BY a.actor_name
                HAVING edit_count >= %s
                ORDER BY edit_count DESC
                """,
                (_mw_timestamp(start), _mw_timestamp(end), *EXEMPT_GROUPS, EDIT_THRESHOLD),
            )
            return [db.decode_row(row) for row in cur.fetchall()]


def oldest_available(db_host: str):
    """Timestamp of the oldest row still in recentchanges -- windows
    starting before this can't be counted (fully) anymore."""
    with db.connect(db_host, db="srwiki_p") as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT MIN(rc_timestamp) FROM recentchanges")
            (oldest,) = db.decode_row(cur.fetchone())
    if not oldest:
        return None
    return datetime.datetime.strptime(oldest, "%Y%m%d%H%M%S")
