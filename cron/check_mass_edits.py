#!/usr/bin/env python3
"""Hourly Toolforge job: checks the rolling last-24h window on srwiki for
registered, non-bot/non-user-bot users who crossed the mass-edit policy's
300-edit threshold (see Википедија:Гласање/Ограничавање_масовних_измена_
за_не-бот_кориснике, passed 2026-08-14), and emails the maintainer in
Serbian if any are found.

Deliberately standalone (its own tiny venv, not the webservice's app
package) so this cron job doesn't depend on how/whether the webservice is
currently deployed -- matches the existing brcl.sh/reports.sh jobs' own
independence from each other and from the webservice. The query itself is
a copy of app/tools/masovne_izmene.py's -- keep the two in sync if the
detection logic ever changes; see docs/deployment-toolforge.md for how
this job is scheduled and deployed (this file lives in the repo, but the
job runs a copy of it from ~/cron/ on the tool account).

Because the window is a rolling "last 24h as of whenever this runs" rather
than a tracked "new violations since last check", a sustained mass-edit
spree that spans several runs will be re-reported each hour it's still
within the trailing 24h window, not just once -- deliberate, since this is
a monitoring alert, not a one-shot notification log.
"""
import datetime
import os
import smtplib
from email.mime.text import MIMEText

import pymysql

EDIT_THRESHOLD = 300
WINDOW_HOURS = 24
EXEMPT_GROUPS = ("bot", "user-bot")

DB_HOST = "srwiki.analytics.db.svc.wikimedia.cloud"
REPLICA_CNF = os.path.expanduser("~/replica.my.cnf")

MAIL_TO = "dungodung@gmail.com"
MAIL_FROM = "srwiki@toolforge.org"
SMTP_HOST = "mail.tools.wmcloud.org"

TOOL_URL = "https://srwiki.toolforge.org/masovne-izmene"


def _replica_credentials():
    with open(REPLICA_CNF) as f:
        lines = [line.strip("\n") for line in f.readlines()[1:]]
    user = lines[0].split("=", 1)[1].strip("'")
    password = lines[1].split("=", 1)[1].strip("'")
    return user, password


def _decode(value):
    return value.decode("utf-8", "replace") if isinstance(value, bytes) else value


def mass_editors(start: datetime.datetime, end: datetime.datetime):
    """(username, edit_count) for every non-exempt registered user whose
    edit count in [start, end) meets EDIT_THRESHOLD, ordered by edit count
    descending. Mirrors app/tools/masovne_izmene.py's mass_editors() --
    see its docstring for why this counts recentchanges (per-edit rc_bot
    flag; only mw.edit/mw.new) rather than revision.
    """
    user, password = _replica_credentials()
    conn = pymysql.connect(
        host=DB_HOST, user=user, password=password, db="srwiki_p",
        charset="utf8mb4", connect_timeout=10, read_timeout=60, write_timeout=60,
    )
    try:
        with conn.cursor() as cur:
            exempt_placeholders = ", ".join(["%s"] * len(EXEMPT_GROUPS))
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
                (
                    start.strftime("%Y%m%d%H%M%S"),
                    end.strftime("%Y%m%d%H%M%S"),
                    *EXEMPT_GROUPS,
                    EDIT_THRESHOLD,
                ),
            )
            return [(_decode(name), count) for name, count in cur.fetchall()]
    finally:
        conn.close()


def send_violator_email(violators, window_start: datetime.datetime, window_end: datetime.datetime):
    period = f"{window_start.strftime('%d.%m.%Y. %H:%M')} – {window_end.strftime('%d.%m.%Y. %H:%M')}"
    lines = [
        "Аутоматска провера правила о ограничавању масовних измена за не-бот "
        f"кориснике (најмање {EDIT_THRESHOLD} измена у 24 часа) пронашла је следеће "
        f"кориснике који су прекршили праг у периоду {period}:",
        "",
    ]
    for username, count in violators:
        lines.append(f"• {username} — {count} измена")
        lines.append(f"  Доприноси: https://sr.wikipedia.org/wiki/Посебно:Доприноси/{username}")
    lines.append("")
    lines.append(f"Пун преглед за овај период: {TOOL_URL}?start={window_start.strftime('%Y-%m-%dT%H:%M')}")

    msg = MIMEText("\n".join(lines), _charset="utf-8")
    msg["Subject"] = f"[srwiki] {len(violators)} корисник(а) премашило праг масовних измена"
    msg["From"] = MAIL_FROM
    msg["To"] = MAIL_TO

    with smtplib.SMTP(SMTP_HOST) as smtp:
        smtp.send_message(msg)


def main():
    now = datetime.datetime.utcnow()
    window_start = now - datetime.timedelta(hours=WINDOW_HOURS)

    violators = mass_editors(window_start, now)
    if violators:
        send_violator_email(violators, window_start, now)


if __name__ == "__main__":
    main()
