# Automatic dynamic CI reporting

Calling `dyn-actions` now always records the full source SHA. Automatic mode
uploads a source-owned artifact containing the dispatch identity and forwarded
workflow manifest. Explicit policy mode instead binds the dispatch through a
source-owned commit status and injects the receiver sentinel. Existing callers
following `@main` pick this up on their next Trigger run. No per-project status
token, status permission, observer, or workflow list is needed for automatic
reporting. A caller pinned to an older action commit must update its pin before
receiving the new behavior.

The central receiver routes source owners to the existing credential groups in
`credential_groups`. Projects under those owners are discovered automatically.
Another execution repository needs this receiver installed once; changing the
shared action alone cannot install a receiver in a different repository.

Auto mode reports each actually scheduled workflow under
`dynamic / <declared workflow name>`, linking directly to its execution run.
The name is read from the exact forwarded workflow bytes, not the mutable workflow
registry or run payload. A missing or unsupported static name falls back to the
filename; duplicate names append the filename; long contexts use deterministic
hash truncation. Queued/running is pending; success is success; failed, cancelled,
timed-out or skipped is failure. The same named detail statuses are emitted beside
an explicit aggregate policy, while the existing aggregate and dispatch contexts
remain unchanged. Workflows that do not trigger do not create detail statuses.

The source artifact binds source repository ID, full SHA, Trigger run/attempt,
execution SHA, and a SHA-256 manifest of the forwarded workflow files. The receiver
validates that evidence using GitHub API data and reads only its trusted default
branch code. It never executes forwarded code. Generation guards prevent old
source attempts from overwriting newer observed results; scheduled reconciliation
repairs event/upload races. A failed forward remains visible as a failing native
Trigger and creates no automatic result that could remain pending.

Absent an explicit checkout ref, `clone-dyn` uses the full source SHA. Auto mode
preserves a caller's explicit branch/tag ref for compatibility; its status observes
that workflow and does not claim the workflow tested an immutable checkout.
Explicit aggregate policies retain their strict exact-SHA checkout contract.

The receiver listens to all execution workflow names while excluding its own
default branch. Scheduled repair scans 48 hours every ten minutes; manual repair with an
explicit SHA handles older retained receipts. The wide repair window also covers
long-running jobs whose completion events were missed.
Artifacts are retained seven days. Event processing handles only the event SHA.
API/scheduler delays can defer reporting, and expired artifacts cannot be verified.
The existing tag-forwarding naming convention is unchanged.

Run the manual `Dynamic CI automatic integration` workflow in Kangumi to validate
the no-policy/no-source-status-permission path end to end. The forwarded smoke
workflow permits pending/cancellation/rerun checks without running product builds.

## Explicit aggregate policy compatibility

# Dynamic CI source status protocol

Existing callers remain opt-in compatible. Set `status_policy: checks-v1` and
`status_token: ${{ github.token }}` on dyn-actions, grant the source Trigger
`contents: read` and `statuses: write`, and serialize Trigger runs per source SHA
with `cancel-in-progress: false`.

The forwarding action has a staged metadata format. `metadata-format` defaults
to `legacy`, which preserves the text files and schema 1 `.github/source.json`
for existing branches. Migrated callers set `metadata-format: source-yml`; those
batches write only schema 2 `.github/source.yml`. Schema 2 carries the existing
source repository/ID, full SHA, ref type/name, Trigger workflow/run/attempt,
execution repository and policy plus the commit message/authors and dispatch time.
Its YAML is a versioned strict subset emitted and parsed inside this Action, so
callers install no parser dependency. If source.yml exists but is invalid, readers
fail closed rather than falling back to legacy data.

`dyn-source`, `clone-dyn`, `gitops-deploy`, and both receiver modes read schema
2 and schema 1. The first two locate metadata before or after clone-dyn restores it
under `__origin__/.github`. `clone-dyn` keeps explicit auxiliary repository refs
and strict exact-SHA policy behavior.

## Source ref matching

Projects should use `dyn-source` instead of reading metadata files directly:

```yaml
- uses: repotea-workspace/kangumi/github-actions/dyn-source@main
  id: source
  with:
    repository: owner/project
    branches: |
      main
      release/*

- name: Deploy
  if: steps.source.outputs.matches == 'true'
  run: ./deploy.sh
```

`branches` and `tags` are optional newline-separated, case-sensitive exact
names or `*`/`?` glob patterns. Blank lines are ignored. Branch filters never
match tags and tag filters never match branches. With neither input, `matches`
is true. Invalid patterns or metadata fail the Action. Outputs are `repository`,
`sha`, `ref_type`, `ref_name`, `branch`, `tag`, and `matches`.

## Status lifecycle

- `<repo>/dynamic-dispatch` is written by the source GITHUB_TOKEN. Pending means
  forwarding started; success binds the source run and attempt to the immutable
  execution commit; error means forwarding failed.
- `<repo>/dynamic-checks` is reset to pending before dispatch. The trusted receiver
  reports pending until all required workflows finish, success only if each
  workflow succeeds, failure for other terminal conclusions, and error if a
  required workflow is absent after its grace period (default ten minutes).
- Details links point to the downstream run, or to the receiver summary when
  multiple required workflows contribute.
- Install a source `workflow_run: completed` observer using `dyn-dispatch` for
  unsuccessful Triggers, including failures before the forwarding step.
  This observer must exist on the source default branch.
- Configure both contexts as required checks if merge protection is desired.
  This integration does not modify repository protection settings.

A required workflow must make every mandatory job affect its workflow
conclusion. GitHub can conclude success when a job is deliberately skipped:
the receiver cannot infer whether such a job was required. Use an explicit
always-running final gate inside that workflow if conditional jobs are mandatory.

## Trusted receiver

Install dyn-status in the execution repository's default-branch workflow.
Check out only the default branch (with persist-credentials false), and use an
explicit source key for each job. Never check out or execute the triggering
execution revision in the receiver. Pin the shared actions to a reviewed
Kangumi commit when deploying.

The JSON config has `schema_version: 1`, `execution_repository`, and `sources`.
Each source declares repository name and numeric ID, the two standard contexts,
allowed Trigger paths, and versioned policies. Each policy contains required
workflow filenames and names and optionally `missing_after_seconds` (60–3600).
Policy versions are immutable; add a new version when changing required checks
and retain old versions while batches may still be active.

Listen for requested/in_progress/completed workflow_run events on the registered
source execution branches (for example, `owner/repository`), accepting all workflow
names on those branches. GitHub shares workflow IDs and current names by file path
across branches: another project using `check.yml` can overwrite the registered
name and cause a name-filtered receiver to miss completion events. Before reporting,
the policy verifies the full source and execution workflow sets and their exact
bytes at the attested commits. Required workflow names are read from those bytes;
the mutable run-name payload is not trusted.

Exclude the receiver's default branch at the event-filter level so its own runs
cannot recursively trigger it. Each source job should also ignore events from
other source execution branches; this avoids unrelated events replacing queued
reconciliation jobs. For tag forwarding, explicitly register the execution tag
patterns and source job routing as well, without admitting the default branch.

Run scheduled reconciliation every ten
minutes, plus workflow_dispatch with an optional full execution SHA. Serialize
receiver jobs per source/context with cancel-in-progress false. GitHub may replace
a pending concurrency job; each invocation scans 48 hours of injected receipt
runs, so later invocations recover missed events. Manual SHA reconciliation
covers older executions. Scheduling and API outages can delay reporting.

The receiver verifies a source-owned bot receipt, numeric repository ID,
Trigger run SHA/path/attempt, the complete forwarded workflow set, and byte
equality of every forwarded workflow against the source commit. It reports each
started authenticated workflow; only the policy's required subset contributes to
the aggregate result. It queries current execution runs (latest run and attempt),
then checks the receipt again before writing. Older generations are ignored.
Pending results are reset on reruns when an event or reconciliation observes them.

## Permissions and trust

The receiver's execution token requires contents/actions read. Each source token
requires source contents/actions/statuses read and statuses write. Use separate
least-privilege source credentials; a protected environment or GitHub App can
further restrict access. Do not put a source status token in business test jobs.

This protocol assumes the execution repository, its default branch, shared action
revision, and source Trigger authors are trusted. A writer able to modify workflows
that receive repository-wide secrets can already access those secrets; receipt
validation is not isolation against a compromised execution repository. Existing
repository-wide PATs are a migration option, not a new security boundary.

The source Trigger and receiver are different workflows in different repositories.
Commit Status writes offer no compare-and-swap transaction across them; the
receipt recheck reduces stale-result races but does not make writes atomic.
Reconciliation repairs transient stale writes. Do not treat this as cryptographic
attestation or an adversarial merge authorization system.

## Deployment and validation

1. Publish reviewed Kangumi actions.
2. Install the receiver and versioned source registrations on execution default.
3. Land each source failure observer on its default branch before enabling opt-in.
   A first opt-in PR cannot rely on an observer that exists only on its branch.
4. Migrate each source Trigger and dyn-workflow to the reviewed action revision;
   remove its previous status-writing job to avoid competing writers.
5. Run a source change and verify pending, a real downstream result, and its Details
   link on the exact source SHA. Verify a cancelled rerun and a missing-workflow
   fixture in a disposable registered source before relying on protection.

Offline tests: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s github-actions/dyn-common -v`.
