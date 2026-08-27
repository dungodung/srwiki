import datetime

from pymysql.converters import escape_string

from .. import db

# Bytes added per (editor, article) pair during a competition window, for
# articles logged on the competition's "evidencija" (record-keeping) subpage.
# Kept as one hand-written query (rather than built up via the ORM/query
# builder style used elsewhere in this app) because it relies on MySQL
# session variables (@a, @kor_cl) to compute a running per-(user,article)
# byte diff -- rewriting that logic in Python would mean pulling every
# matching revision back to the app instead of letting MySQL do it in one
# pass. `:pocetak`/`:kraj`/`:takmicenje` are substituted via escape_string()
# below rather than driver-level %s placeholders because the query already
# contains literal `%` wildcards (in the page_title LIKE pattern), which
# collide with pymysql's %-style parameter substitution.
_QUERY_TEMPLATE = """
select replace(korisnik, '_', ' '), replace(clanak, '_', ' '), broj_bajtova
from (
	select korisnik, clanak, sum(diff) as broj_bajtova
	from (
		select korisnik, clanak, velicina, urednik, ts, diff
		from (
			select tc.*, case when @kor_cl != concat(korisnik, clanak) then velicina else velicina - @a end as diff, @kor_cl := concat(korisnik, clanak) as i1, case when @kor_cl != concat(korisnik, clanak) then @a := 0 else @a := velicina end as i2
			from (
				select korisnik, clanak, cast(r.rev_len as signed) as velicina, a.actor_name as urednik, r.rev_timestamp as ts, @a := 0 as x1, @kor_cl := '' as x2
				from (
					select concat(ucase(left(cast(korisnik as char), 1)), substr(cast(korisnik as char), 2)) as korisnik, coalesce(lt.lt_title, clanak) as clanak, ns
					from (
						select trim(replace(p.page_title, 'Такмичење_у_писању_чланака/:takmicenje/евиденција/', '')) as korisnik, lt.lt_title as clanak, lt.lt_namespace as ns
						from page p, pagelinks pl, linktarget lt
						where p.page_title like 'Такмичење_у_писању_чланака/:takmicenje/евиденција/%'
						and p.page_namespace = 4
						and p.page_id = pl.pl_from
						and pl.pl_target_id = lt.lt_id
						and pl.pl_from_namespace = 4
					) tc
					left join page p on p.page_title = tc.clanak and p.page_namespace = tc.ns and p.page_is_redirect
					left join pagelinks pl on pl.pl_from = p.page_id
					left join linktarget lt on pl.pl_target_id = lt.lt_id
				) tc, page p, revision r, actor a
				where tc.ns = 0
				and p.page_title = tc.clanak
				and p.page_namespace = 0
				and r.rev_page = p.page_id
				and r.rev_actor = a.actor_id
				order by 1, 2, 5
			) tc
		) x
	) tc
	where korisnik = replace(urednik, ' ', '_')
	and ts between ':pocetak' and ':kraj'
	group by 1, 2
) x
"""


def parse_date(date: str) -> str:
    return datetime.datetime.strptime(date, "%d.%m.%Y.").strftime("%Y%m%d%H%M%S")


def leaderboard(takmicenje: str, pocetak: str, kraj: str, db_host: str):
    """Per-editor, per-article byte contributions during one competition's
    window. Returns raw (user, article, bytes) rows ordered by user, article.
    """
    sql = (
        _QUERY_TEMPLATE
        .replace(":pocetak", escape_string(pocetak))
        .replace(":kraj", escape_string(kraj))
        .replace(":takmicenje", escape_string(takmicenje.replace(" ", "_")))
    )
    with db.connect(db_host, db="srwiki_p") as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            return [db.decode_row(row) for row in cur.fetchall()]
