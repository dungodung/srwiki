import datetime
import itertools
import os

from flask import Blueprint, Response, current_app, redirect, render_template, request, url_for

from ...tools import catuse as catuse_tool
from ...tools import masovne_izmene as masovne_izmene_tool
from ...tools import plakete as plakete_tool
from ...tools import portali as portali_tool
from ...tools import takmicenja as takmicenja_tool

main_bp = Blueprint("main", __name__)


@main_bp.get("/")
def home():
    return render_template("index.html")


# --- Portali -----------------------------------------------------------

@main_bp.get("/portali")
def portali():
    portal = request.args.get("portal", "")
    if len(portal) > 1:
        portal = portal[0].upper() + portal[1:]

    poruka = ""
    if portal:
        db_host = current_app.config["SRWIKI_DB_HOST"]
        broj = portali_tool.article_count(portal, db_host)
        poruka = (
            f'Broj članaka u portalu <a href="https://sr.wikipedia.org/wiki/Portal:{portal}">{portal}</a> '
            f"je <b>{broj}</b>."
        )

    return render_template("portali.html", portal=portal, poruka=poruka)


# --- Plakete -------------------------------------------------------------

def _load_plakete_svg_template() -> str:
    path = os.path.join(current_app.static_folder, "template.svg")
    with open(path, encoding="utf-8") as f:
        return f.read()


@main_bp.get("/plakete")
def plakete():
    korisnik = request.args.get("korisnik", "")
    if len(korisnik) > 1:
        korisnik = korisnik[0].upper() + korisnik[1:]
    impr = request.args.get("impr", "clanci")
    rod = request.args.get("rod", "muski")
    pismo = request.args.get("pismo", "cir")
    izgovor = request.args.get("izgovor", "ek")

    poruka = ""
    broj = 0
    fail = False
    if korisnik:
        db_host = current_app.config["SRWIKI_DB_HOST"]
        mainspace_only = impr != "svi"
        broj, bot = plakete_tool.edit_count_and_bot_flag(korisnik, mainspace_only, db_host)
        if broj < plakete_tool.MIN_EDITS:
            fail = True
            poruka = (
                "Nema korisnika sa zadatim imenom."
                if broj == 0
                else f"Korisnik ima manje od {plakete_tool.MIN_EDITS} izmena."
            )

    if not korisnik or fail:
        return render_template(
            "plakete.html", korisnik=korisnik, impr=impr, rod=rod, pismo=pismo, izgovor=izgovor, poruka=poruka
        )

    svg = plakete_tool.render_svg(
        _load_plakete_svg_template(), korisnik, broj, impr != "svi", rod, pismo, izgovor, bot
    )
    return Response(svg, mimetype="image/svg+xml")


# --- Catuse (file usage from a Commons category) --------------------------

@main_bp.get("/upotreba-slika")
@main_bp.get("/catuse")
def catuse():
    category = request.args.get("category", "")
    if len(category) > 1:
        category = category[0].upper() + category[1:]

    groups = []
    if category:
        db_host = current_app.config["COMMONSWIKI_DB_HOST"]
        rows = catuse_tool.file_usages(category, db_host)
        for file_title, file_rows in itertools.groupby(rows, key=lambda r: r[0]):
            uses = []
            for _title, gil_wiki, site_data, gil_ns, gil_title in file_rows:
                page = f"{gil_ns}:{gil_title}" if gil_ns else gil_title
                use_title = f"{gil_wiki}:{page}"
                use_url = f"{catuse_tool.article_path(site_data)}{page}"
                uses.append((use_url, use_title))
            groups.append((
                file_title.replace("_", " "),
                f"https://commons.wikimedia.org/wiki/File:{file_title}",
                uses,
            ))

    return render_template("catuse.html", category=category, groups=groups)


# --- Takmičenja (competition byte-diff leaderboard) ------------------------

@main_bp.get("/takmicenja")
def takmicenja():
    takmicenje = request.args.get("takmicenje", "")
    pocetak = request.args.get("pocetak", "")
    kraj = request.args.get("kraj", "")

    groups = []
    if takmicenje and pocetak and kraj:
        db_host = current_app.config["SRWIKI_DB_HOST"]
        rows = takmicenja_tool.leaderboard(
            takmicenje.strip(),
            takmicenja_tool.parse_date(pocetak.strip()),
            takmicenja_tool.parse_date(kraj.strip()),
            db_host,
        )
        for user_name, user_rows in itertools.groupby(rows, key=lambda r: r[0]):
            entries = [
                (f"https://sr.wikipedia.org/wiki/{art}", art, num_bytes)
                for _user, art, num_bytes in user_rows
            ]
            groups.append((f"https://sr.wikipedia.org/wiki/Корисник:{user_name}", user_name, entries))

    return render_template(
        "takmicenja.html", takmicenje=takmicenje, pocetak=pocetak, kraj=kraj, groups=groups
    )


# --- Masovne izmene (mass non-bot edit detector) ---------------------------

@main_bp.get("/masovne-izmene")
def masovne_izmene():
    start = request.args.get("start", "")

    results = None
    error = None
    window_start = window_end = ""
    if start:
        try:
            start_dt = masovne_izmene_tool.parse_start(start)
        except ValueError:
            error = "Neispravan format datuma/vremena."
        else:
            db_host = current_app.config["SRWIKI_DB_HOST"]
            results = masovne_izmene_tool.mass_editors(start_dt, db_host)
            window_end_dt = start_dt + datetime.timedelta(hours=masovne_izmene_tool.WINDOW_HOURS)
            window_start = start_dt.strftime("%d.%m.%Y. %H:%M")
            window_end = window_end_dt.strftime("%d.%m.%Y. %H:%M")

    # An empty field defaults to today at midnight rather than a blank
    # "--:--" placeholder -- the field is pre-filled for convenience only,
    # not treated as if the user had actually submitted it (the query
    # above only runs when `start` was genuinely present in the request).
    displayed_start = start or datetime.datetime.now().strftime("%Y-%m-%dT00:00")

    return render_template(
        "masovne_izmene.html",
        start=displayed_start,
        results=results,
        error=error,
        window_start=window_start,
        window_end=window_end,
        threshold=masovne_izmene_tool.EDIT_THRESHOLD,
    )


# --- Daily article-count file (written by the unrelated `brcl` cron job) --

@main_bp.get("/brojclanaka")
def brojclanaka():
    path = current_app.config["BROJCLANAKA_PATH"]
    try:
        with open(path, encoding="utf-8") as f:
            content = f.read()
    except OSError:
        return Response("brojclanaka is not available in this environment.\n", mimetype="text/plain", status=404)
    return Response(content, mimetype="text/plain")


# --- Old /cgi-bin/<name> URLs: redirect to the new routes, keep the query --

_CGI_BIN_REDIRECTS = {
    "portali": "main.portali",
    "plakete": "main.plakete",
    "catuse": "main.catuse",
    "takmicenja": "main.takmicenja",
}


@main_bp.get("/cgi-bin/<name>")
def cgi_bin_redirect(name):
    endpoint = _CGI_BIN_REDIRECTS.get(name)
    if endpoint is None:
        return render_template("404.html"), 404
    target = url_for(endpoint)
    query = request.query_string.decode("utf-8")
    if query:
        target = f"{target}?{query}"
    return redirect(target, code=301)
