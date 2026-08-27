# GitHub → Toolforge deployment runbook

srwiki deploys to Wikimedia Toolforge via **Build Service**, replacing the
tool's previous `python2` webservice type (deprecated, and the direct cause
of `portali`/`catuse` being broken -- see `README.md`).

`wikiwhiz`/`duga` mirror GitHub to a GitLab repo and build from that --
mainly because they have a separate frontend build step that has to run
*before* the Build Service build (see their docs). This app has no such
step, and `toolforge build start` accepts any git URL directly (confirmed
live: `toolforge build start https://github.com/dungodung/srwiki --ref main`
built successfully), so there's no GitLab mirror here at all -- Build
Service pulls straight from GitHub.

This app needs the webservice's **NFS mount kept on** (`--mount=all`, not
`--mount=none`): it reads `/data/project/srwiki/replica.my.cnf` for
wikireplica credentials, and it serves
`/data/project/srwiki/public_html/brojclanaka` live at `/brojclanaka` -- a
file the unrelated, still-running `brcl` Toolforge job appends to every
night. Never copy that file into the repo; it must stay read live off NFS
or `/brojclanaka` goes stale the day after every deploy.

The srwiki Toolforge tool already exists (this is a rewrite, not a new
tool), so skip `toolforge tools create`.

## Deploying / redeploying

```
become srwiki

# build & start (first time)
toolforge build start https://github.com/dungodung/srwiki --ref main
toolforge build show   # wait for "ok"
toolforge webservice buildservice start --mount=all

# stop the old python2 webservice first if it's still running
toolforge webservice python2 stop
```

Redeploy after a code change: push `main` on GitHub, then re-run
`toolforge build start` + `toolforge webservice buildservice restart`.

## Verify

- `https://srwiki.toolforge.org/` loads the tool list.
- `https://srwiki.toolforge.org/portali?portal=Film` returns a real count
  (was a 500 before this rewrite).
- `https://srwiki.toolforge.org/catuse?category=Belgrade` (or any populated
  category) returns real cross-wiki usage rows (was a 500 before).
- `https://srwiki.toolforge.org/brojclanaka` returns the live count file,
  and its last line still updates the morning after `brcl` runs.
- `https://srwiki.toolforge.org/cgi-bin/portali` (and the other three old
  names) 301-redirects to the new route.
- FelixBot (`reports` job) and the `brcl` job are both untouched:
  `toolforge jobs list` shows the same two jobs, same schedules, as before
  this deploy.
