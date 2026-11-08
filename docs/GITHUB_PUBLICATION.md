# GitHub publication and verification record

The project was published to **https://github.com/SamarthRamesha/trustdesc-reproduction** on 8 November 2026. Authenticated GitHub API confirms **private** visibility and default branch **main**. The repository was created new after the exact name returned 404 through the authenticated CLI; no existing repository was reused or modified. Existing Git history was preserved.

## Verified publication snapshot

The first pushed audit snapshot is `1a27c96c65aa38d548b3092c4a679c75d6556047` (six commits). Authenticated GitHub API head matched local HEAD, and its complete **123-file blob tree matched local Git exactly**, with no truncated tree response. The original three commits were independently retrieved through GitHub API and remained ancestors in a fresh GitHub clone:

- `5f23a49fb52bbc2d260fddad1d808cc73b7f2aca`
- `87c733b95b7005cc2690b4b22de8ef5a09f04209`
- `e3de3bcd0084a25fedc03c2429e8b2df3700d48c`

See [remote API verification](../reports/publication_audit/github_remote_verification.json). This record and post-push evidence are added in a subsequent documentation commit; the **current latest hash** is always `git rev-parse HEAD` / the [main commit history](https://github.com/SamarthRamesha/trustdesc-reproduction/commits/main), not the earlier verified anchor. A document cannot embed its own containing commit ID. Final delivery rechecks the latest remote/local head and file tree after this record is pushed.

## Fresh GitHub clone checks

From an authenticated clone of that exact GitHub snapshot:

```sh
python3 -I -S scripts/run_tests.py
/opt/homebrew/bin/python3.11 -I -S scripts/run_tests.py
python3 -I -S scripts/validate_notebook.py --execute-portable
python3 -I -S scripts/audit_repository.py
```

Results: **92/92 tests pass on Python 3.13.9 and 3.11.14**, zero failures/errors/skips; notebook's ten code cells compile and five portable cells execute; repository syntax/JSON/local-link/ignore/history-pattern checks pass. Actual Colab/GPU/upload/export and original-model/MCP experiments remain unrun. Commands execute trusted project code, not third-party tools or a sandbox.

Logs: [post-push check summary](../reports/publication_audit/postpush_local_checks.json), [Python 3.13](../reports/publication_audit/postpush-python313.txt), [Python 3.11](../reports/publication_audit/postpush-python311.txt), [notebook](../reports/publication_audit/postpush-notebook.txt), [repository audit](../reports/publication_audit/postpush-repo_audit.txt). The initial 91-test evidence and all earlier research outputs remain unchanged in their original locations.

Fresh venv/wheel install and console demo were validated separately; the only implementation fix was packaged synthetic fixture availability outside a checkout. Dependencies report no broken requirements. Full-history high-signal secret scanning found no matches; it complements manual inventory review and does not mathematically prove absence of all possible secrets. `.env.example` is retained with empty placeholders. External data, credentials, caches, environments, private PDF, models, raw runs and generated archives are excluded.

## Portable artifacts

The original `e3de3bc` ZIP is preserved with its original checksum/98-file manifest. The audited archive is generated separately as `trustdesc-audited-phase1.zip` after final commit, with per-file hashes and current commit ID. It is excluded from Git; a researcher can regenerate it from a clean clone using:

```sh
python scripts/package_project.py --output ../trustdesc-audited-phase1.zip
python scripts/validate_package.py ../trustdesc-audited-phase1.zip
```

Archive verification and extracted-source smoke tests check consistency with its own manifest/commit. Older and newer archives are not expected to have equal hashes. GitHub remains the source of truth for history and documentation, so continuation does not depend on collecting scattered local files.

No public visibility, open-source licensing grant, CI-billing change or paid inference was introduced. LICENSE reserves rights pending an explicit rights-holder decision. A future assistant needs authorized access to this private repository; providing a URL alone may not grant it. Start with README, PROJECT_HANDOVER and PHASE1_COMPLETION_AUDIT.
