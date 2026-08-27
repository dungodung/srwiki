# GitHub → GitLab → Toolforge deployment runbook

srwiki deploys to Wikimedia Toolforge via **Build Service** (a git push,
mirrored to GitLab, triggers an automatic container build) -- the same
pipeline `wikiwhiz`/`duga` use, replacing the tool's previous `python2`
webservice type (deprecated, and the direct cause of `portali`/`catuse`
being broken -- see `README.md`).

Unlike those two, this app needs the webservice's **NFS mount kept on**
(`--mount=all`, not `--mount=none`): it reads
`/data/project/srwiki/replica.my.cnf` for wikireplica credentials, and it
serves `/data/project/srwiki/public_html/brojclanaka` live at
`/brojclanaka` -- a file the unrelated, still-running `brcl` Toolforge job
appends to every night. Never copy that file into the repo; it must stay
read live off NFS or `/brojclanaka` goes stale the day after every deploy.

The srwiki Toolforge tool already exists (this is a rewrite, not a new
tool), so skip `toolforge tools create`.

## One-time setup

1. **Create the GitLab repo** at
   `gitlab.wikimedia.org/toolforge-repos/srwiki` (via the Toolforge tool
   dashboard, which provisions this automatically) and add it as a remote.

## The `deploy` branch

This app has no separate frontend build step (server-rendered Flask/Jinja
only), so `.gitlab-ci.yml` just fast-forwards `main` onto `deploy` on every
push -- that branch is what Toolforge actually builds from. To do this
manually instead of relying on CI:
```
git checkout -B deploy
git push origin deploy -f
```

## Deploying / redeploying

```
become srwiki

# build & start (first time)
toolforge build start https://gitlab.wikimedia.org/toolforge-repos/srwiki --ref deploy
toolforge build show   # wait for "ok (Succeeded)"
toolforge webservice buildservice start --mount=all

# stop the old python2 webservice first if it's still running
toolforge webservice python2 stop
```

Redeploy after a code change: push `main`, let CI (or the manual steps
above) update `deploy`, then re-run `toolforge build start` +
`toolforge webservice buildservice restart`.

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
