# srwiki

Filip's public-facing Serbian Wikipedia tools, rebuilt as a Flask app for
Toolforge Build Service -- replacing the original hand-rolled Python-2 CGI
scripts, two of which (`portali`, `catuse`) no longer actually worked (see
below).

This repo covers **only** the public tools served at
[srwiki.toolforge.org](https://srwiki.toolforge.org/). Two other things live
in the same Toolforge tool's home directory and are untouched by this
project:

- **FelixBot** (`reports.sh`, the `reports` Toolforge job) -- a pywikibot
  setup that generates Serbian Wikipedia statistics pages and posts them
  on-wiki. Still running fine; nothing here changes it.
- **The daily article-count cron** (`brcl.sh`, the `brcl` Toolforge job) --
  appends a line to `brojclanaka` in the tool's `public_html/` every night
  at 00:01. Still running fine and untouched; this app only *reads* that
  file to serve it at `/brojclanaka` (see `docs/deployment-toolforge.md` for
  why the webservice needs `--mount=all` for that to work).

## Tools

- **Portali** (`/portali`) -- counts mainspace articles linking to a given
  Portal:. Was 500ing on every request: its query used
  `pagelinks.pl_title`/`pl_namespace` directly, which no longer exist --
  MediaWiki moved link targets into a shared `linktarget` table. Fixed by
  joining through `linktarget`, confirmed against live data.
- **Plakete** (`/plakete`) -- generates an SVG "plaque" congratulating an
  editor who has passed 100 edits.
- **Upotreba slika iz kategorije** (`/upotreba-slika`, also `/catuse`) --
  lists cross-wiki usage of files in a given Commons category. Was 500ing on
  any real query: it connected to `commonswiki.labsdb`, a wikireplica
  hostname retired years ago, *and* joined `categorylinks.cl_to`, which was
  also since normalized into `linktarget`. Both fixed, confirmed against
  live data (e.g. `?category=Belgrade`).
- **Takmičenja** (`/takmicenja`) -- a per-editor, per-article byte-diff
  leaderboard for a wiki-writing competition.

Old `/cgi-bin/<name>` URLs still work -- they 301-redirect to the new routes
(see requirements gathered during planning; not preserving the literal path
was an explicit choice to move to cleaner URLs going forward).

## Local development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
```

The tools query the Wikimedia wikireplicas directly (no local database of
this app's own). Point `REPLICA_MY_CNF` at a `replica.my.cnf`-formatted file
with real Toolforge wikireplica credentials to exercise them locally; without
one, only the blank-form pages and `/brojclanaka` (point `BROJCLANAKA_PATH`
at a local file) work.

```bash
make test    # or: pytest tests -v
flask --app wsgi run
```

## Deployment

See `docs/deployment-toolforge.md`.

## Licence

MIT, see `LICENSE`.
