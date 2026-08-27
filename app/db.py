import os

import pymysql
import pymysql.cursors

# Wikimedia Cloud VPS convention: every Toolforge tool gets its own
# read-only wikireplica credentials at ~/replica.my.cnf (see
# wikitech.wikimedia.org/wiki/Help:Toolforge/Database#Access_from_Toolforge).
# Local dev has no such file, so REPLICA_MY_CNF can point at a throwaway one.
_DEFAULT_CNF_PATH = os.path.expanduser("~/replica.my.cnf")


def _replica_credentials():
    path = os.environ.get("REPLICA_MY_CNF", _DEFAULT_CNF_PATH)
    with open(path) as f:
        lines = [line.strip("\n") for line in f.readlines()[1:]]
    user = lines[0].split("=", 1)[1].strip("'")
    password = lines[1].split("=", 1)[1].strip("'")
    return user, password


def decode(value):
    """MediaWiki's schema stores most "text" columns (titles, usernames,
    comments, log params, and even the 14-digit timestamps) as
    varbinary/blob rather than a text type with a real charset -- MySQL
    treats those as raw binary regardless of the connection charset, so
    pymysql hands them back as `bytes`, confirmed live against real query
    results. This decodes the ones this app treats as text.
    """
    return value.decode("utf-8", "replace") if isinstance(value, bytes) else value


def decode_row(row):
    return tuple(decode(v) for v in row)


def connect(host, db=None):
    """A fresh connection to one wikireplica host/database.

    Callers are expected to use it as a short-lived context manager (`with
    connect(...) as conn:`) -- these are read-only analytical queries, not a
    pooled app database, so there's no long-lived connection to manage.
    """
    user, password = _replica_credentials()
    return pymysql.connect(
        host=host,
        user=user,
        password=password,
        db=db,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.Cursor,
        connect_timeout=10,
        # plakete's edit-count query joins revision to page to filter by
        # namespace, and for a heavy editor MySQL pays that per-row (a
        # nested-loop page lookup per matching revision, not a bulk scan) --
        # confirmed live: 44s+ for a ~120k-edit account on srwiki_p, well
        # past a short timeout, which is what was actually behind plakete's
        # 500s (a `Lost connection ... (timed out)` from pymysql, not a
        # logic bug). Unlike rightstool's all-wikis sweeps, srwiki only ever
        # queries one wiki per request, so a longer timeout here just makes
        # this one request take longer, it doesn't compound.
        read_timeout=60,
        write_timeout=60,
    )
