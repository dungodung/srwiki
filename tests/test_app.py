import os

import pytest

from app import create_app


@pytest.fixture
def client(tmp_path):
    brojclanaka = tmp_path / "brojclanaka"
    brojclanaka.write_text("26.08.2026. 707957\n27.08.2026. 707988\n")
    os.environ["BROJCLANAKA_PATH"] = str(brojclanaka)

    app = create_app("testing")
    app.config["BROJCLANAKA_PATH"] = str(brojclanaka)
    return app.test_client()


def test_home_lists_all_tools(client):
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    for path in ("/portali", "/plakete", "/catuse", "/takmicenja", "/masovne-izmene"):
        assert path in body


def test_portali_blank_form_does_not_touch_db(client):
    resp = client.get("/portali")
    assert resp.status_code == 200
    assert "Portal" in resp.get_data(as_text=True)


def test_plakete_blank_form_does_not_touch_db(client):
    resp = client.get("/plakete")
    assert resp.status_code == 200
    assert "Korisničko ime" in resp.get_data(as_text=True)


def test_catuse_blank_form_does_not_touch_db(client):
    resp = client.get("/catuse")
    assert resp.status_code == 200
    assert "Kategorija" in resp.get_data(as_text=True)


def test_takmicenja_blank_form_does_not_touch_db(client):
    resp = client.get("/takmicenja")
    assert resp.status_code == 200
    assert "Takmičenje" in resp.get_data(as_text=True)


def test_masovne_izmene_blank_form_does_not_touch_db(client):
    resp = client.get("/masovne-izmene")
    assert resp.status_code == 200
    assert "Početak" in resp.get_data(as_text=True)


def test_masovne_izmene_rejects_bad_datetime(client):
    resp = client.get("/masovne-izmene?start=not-a-date")
    assert resp.status_code == 200
    assert "Neispravan format" in resp.get_data(as_text=True)


def test_brojclanaka_serves_live_file_content(client):
    resp = client.get("/brojclanaka")
    assert resp.status_code == 200
    assert resp.mimetype == "text/plain"
    assert "27.08.2026. 707988" in resp.get_data(as_text=True)


@pytest.mark.parametrize(
    "old,new",
    [
        ("/cgi-bin/portali", "/portali"),
        ("/cgi-bin/plakete", "/plakete"),
        ("/cgi-bin/catuse", "/catuse"),
        ("/cgi-bin/takmicenja", "/takmicenja"),
    ],
)
def test_cgi_bin_redirects_to_new_route(client, old, new):
    resp = client.get(old + "?foo=bar", follow_redirects=False)
    assert resp.status_code == 301
    assert resp.headers["Location"].endswith(new + "?foo=bar")


def test_cgi_bin_unknown_tool_404s(client):
    resp = client.get("/cgi-bin/srplakete")
    assert resp.status_code == 404


def test_masovne_izmene_warns_when_window_predates_recentchanges(client, monkeypatch):
    import datetime

    from app.tools import masovne_izmene

    monkeypatch.setattr(masovne_izmene, "mass_editors", lambda start, host: [("Primer", 312)])
    monkeypatch.setattr(
        masovne_izmene, "oldest_available", lambda host: datetime.datetime(2026, 9, 10, 20, 14)
    )

    body = client.get("/masovne-izmene?start=2026-09-01T00:00").get_data(as_text=True)
    assert "Primer" in body and "312" in body
    assert "10.09.2026. 20:14" in body

    body = client.get("/masovne-izmene?start=2026-10-01T00:00").get_data(as_text=True)
    assert "više nisu dostupni" not in body
