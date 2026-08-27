import datetime

from .. import db

MIN_EDITS = 100

_MESECI = {
    "cir": {
        1: "јануар", 2: "фебруар", 3: "март", 4: "април", 5: "мај", 6: "јун",
        7: "јул", 8: "август", 9: "септембар", 10: "октобар", 11: "новембар", 12: "децембар",
    },
    "lat": {
        1: "januar", 2: "februar", 3: "mart", 4: "april", 5: "maj", 6: "jun",
        7: "jul", 8: "avgust", 9: "septembar", 10: "oktobar", 11: "novembar", 12: "decembar",
    },
}


def edit_count_and_bot_flag(korisnik: str, mainspace_only: bool, db_host: str):
    """Returns (edit_count, is_bot) for a user, or (0, False) if they don't exist."""
    with db.connect(db_host, db="srwiki_p") as conn:
        with conn.cursor() as cur:
            namespace_clause = "AND page_namespace = 0" if mainspace_only else ""
            cur.execute(
                f"""
                SELECT COUNT(*) FROM revision, page, actor_revision
                WHERE rev_actor = actor_id AND actor_name = %s AND rev_page = page_id {namespace_clause}
                """,
                (korisnik,),
            )
            broj = cur.fetchone()[0]

            bot = False
            if broj >= MIN_EDITS:
                cur.execute(
                    "SELECT ug_group FROM user, user_groups WHERE ug_user = user_id AND user_name = %s",
                    (korisnik,),
                )
                bot = "bot" in [db.decode(row[0]) for row in cur.fetchall()]
            return broj, bot


def render_svg(template: str, korisnik: str, broj: int, mainspace_only: bool, rod: str, pismo: str, izgovor: str, bot: bool) -> str:
    """Fills in srwiki's award-plaque SVG template (10 %-placeholders, in the
    fixed order below) congratulating an editor for reaching MIN_EDITS+ edits.
    """
    danas = datetime.datetime.now()
    if pismo == "cir":
        if bot:
            kor = "роботском налогу"
        else:
            kor = "корисници" if rod == "zenski" else "кориснику"
        izm = "измјена" if izgovor == "ijek" else "измена"
        lab = [
            "Википедија на српском језику се захваљује " + kor, "на", izm, "у чланцима",
            "и укупном великом доприносу пројекту ширења слободног знања.",
            "Викимедија Србије", "ВИКИМЕДИЈА", "СРБИЈЕ",
        ]
    else:
        if bot:
            kor = "robotskom nalogu"
        else:
            kor = "korisnici" if rod == "zenski" else "korisniku"
        izm = "izmjena" if izgovor == "ijek" else "izmena"
        lab = [
            "Vikipedija na srpskom jeziku se zahvaljuje " + kor, "na", izm, "u člancima",
            "i ukupnom velikom doprinosu projektu širenja slobodnog znanja.",
            "Vikimedija Srbije", "VIKIMEDIJA", "SRBIJE",
        ]

    gde = " " + lab[3] if mainspace_only else ""
    meseci = _MESECI[pismo]

    return template % (
        lab[0], korisnik, lab[1], broj, lab[2] + gde, lab[4], lab[5],
        "%d. %s %d." % (danas.day, meseci[danas.month], danas.year),
        lab[6], lab[7],
    )
