import re

from .. import db

# The wikireplica `sites` table stores each wiki's config as a PHP
# serialized blob; the only field this tool needs out of it is the site's
# article path template (e.g. '/wiki/$1'), which this pattern pulls out
# without a full PHP-serialization parser.
_PAGE_PATH_RE = re.compile(r's:9:"page_path";s:[0-9]+:"(.+?)\$1"')


def file_usages(category: str, db_host: str):
    """Every use, across all Wikimedia wikis, of a file in the given Commons
    category. Returns raw DB rows; grouping/rendering happens in the route.

    The original query joined on `categorylinks.cl_to` directly -- that
    column no longer exists on commonswiki_p (confirmed live via `DESCRIBE
    categorylinks`): category links were normalized the same way pagelinks
    was, into a shared `linktarget` table referenced by `cl_target_id`. This
    joins through `linktarget` instead, matching the fix already applied to
    srwiki's portali tool for the equivalent pagelinks migration.
    """
    with db.connect(db_host, db="commonswiki_p") as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT page_title, gil_wiki, site_data, gil_page_namespace, gil_page_title
                FROM categorylinks cl
                JOIN linktarget lt ON cl.cl_target_id = lt.lt_id
                JOIN page ON cl.cl_from = page_id
                JOIN globalimagelinks ON gil_to = page_title
                JOIN sites ON gil_wiki = site_global_key
                WHERE lt.lt_namespace = 14 AND lt.lt_title = %s AND page_namespace = 6
                ORDER BY 1, 2, 3
                """,
                (category.replace(" ", "_"),),
            )
            return [db.decode_row(row) for row in cur.fetchall()]


def article_path(site_data: str) -> str:
    match = _PAGE_PATH_RE.search(site_data)
    return match.group(1) if match else ""
