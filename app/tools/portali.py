from .. import db


def article_count(portal: str, db_host: str) -> int:
    """Number of mainspace articles that link to Portal:<portal>.

    The original CGI-era query (`pagelinks.pl_title`/`pl_namespace`) predates
    MediaWiki's link-target normalization schema change, which moved the
    namespace/title of a link's target out of `pagelinks` and into a shared
    `linktarget` table -- that's the actual, concrete reason this tool always
    500'd: `pl_title`/`pl_namespace` no longer exist on `pagelinks`. This
    joins through `linktarget` the same way srwiki's takmicenja tool already
    correctly does.
    """
    with db.connect(db_host, db="srwiki_p") as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*)
                FROM pagelinks pl
                JOIN linktarget lt ON pl.pl_target_id = lt.lt_id
                JOIN page p ON pl.pl_from = p.page_id
                WHERE lt.lt_namespace = 100 AND p.page_namespace = 0 AND lt.lt_title = %s
                """,
                (portal,),
            )
            return cur.fetchone()[0]
