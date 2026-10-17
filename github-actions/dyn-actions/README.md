# Automatic dynamic CI reporting

Calling `dyn-actions` now always records the full source SHA. Automatic mode
uploads a source-owned artifact containing the dispatch identity and forwarded
workflow manifest. Explicit policy mode instead binds the dispatch through a
source-owned commit status and injects the receiver sentinel. Existing callers
following `@main` pick this up on their next Trigger run. Deployed Triggers pass
`status_token: ${{ github.token }}` and grant `contents: read` plus
`statuses: write`. This initializes the source-owned `<repo>/dynamic-dispatch`
context before forwarding; success means the batch was forwarded, not that tests
passed. A rerun of the same source Trigger resets previously observed detail
statuses to pending. A different Trigger run on the same SHA does not reset those
details, because branch/tag/path filtering may select a different workflow set.
Tokenless callers remain compatible with artifact-based final reporting.

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
source attempts from overwriting newer observed results. The event job retries a
not-yet-uploaded receipt for up to two minutes and fails visibly if evidence is
still unavailable. A failed forward or receipt upload closes this source attempt's
dispatch/reset statuses when its cleanup step can run. Forced cancellation or
runner loss can prevent cleanup; the native Trigger remains the authoritative
forwarding result, and a failed receiver can be rerun or repaired manually.

Absent an explicit checkout ref, `clone-dyn` uses the full source SHA. Auto mode
preserves a caller's explicit branch/tag ref for compatibility; its status observes
that workflow and does not claim the workflow tested an immutable checkout.
Explicit aggregate policies retain their strict exact-SHA checkout contract.

The receiver listens to `in_progress` and `completed` events for all execution
workflow names while excluding its own default branch. First-start events create
a skipped workflow record but allocate no runner; rerun starts restore pending.
Completion events, including the injected receipt's completion, reconcile only
their immutable execution SHA. There is no scheduled scan or `requested` hook.
A manual invocation requires a full execution SHA. Artifacts are retained seven
days; expired artifacts cannot be verified. Missed events or API outages require
rerunning the receiver or manual SHA reconciliation. The existing tag-forwarding
naming convention is unchanged.

Run the manual `Dynamic CI automatic integration` workflow in Kangumi to validate
the automatic source pending and final status path end to end on either receiver. The forwarded smoke
workflow permits pending/cancellation/rerun checks without running product builds.

## GitHub Actions status identity

Status icons follow the authenticated status creator; the statuses API has no
icon override. To retain the GitHub Actions icon through completion and reruns,
add an installed source to the receiver config's `source_reporting` repository
list. Non-enrolled repositories keep the existing central reporter during rollout.

Enrolled receivers dispatch the source default branch's
`.github/workflows/dynamic-dispatch-status.yml`, passing only the execution
repository/SHA and optional triggering run ID/attempt/status. The source job calls
`dyn-status` with `mode: source`, a trusted `execution-repository`, and its own
`github.token` as `source-token`. It recomputes results from the existing source
receipt and execution evidence; notification inputs never assert success or
failure. The source workflow requires `contents: read`, `actions: read`, and
`statuses: write`. It must not check out or execute the forwarded project.

For the current public execution repositories, the source token also serves as
`execution-token` to read public contents and run metadata. Private execution
repositories require a separately authorized read credential; the notification
must never contain tokens. The central source credential needs Actions write to
dispatch callbacks (classic PAT: `repo`); source status writes no longer use it.
No new secret is needed for the public execution routes.

Workflow dispatch uses API version `2026-03-10` to obtain the exact callback run ID.
The receiver waits for that run and its `Report dynamic CI status` job to succeed;
missing/failed/skipped callbacks fail visibly. Callback timeout is 65 minutes,
receiver acknowledgment timeout 70 minutes, and receiver job timeout 75 minutes.
This adds a source workflow run per processed notification and keeps the receiver
runner allocated while waiting. Same-execution reporting is serialized. Install
and validate the source handler on its default branch before enrolling it.
Historical statuses change creator only when successfully reconciled again;
expired source artifacts still cannot be reconstructed.

## Explicit aggregate policy compatibility

# Dynamic CI source status protocol

Declare explicit checks on dyn-actions and its failure observer:

```yaml
with:
  checks: |
    version: 1
```

Grant dyn-actions `status_token: ${{ github.token }}` and the source Trigger
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
Check out only the default branch with `persist-credentials: false`; never check
out or execute the triggering execution revision. All Kangumi actions track
`@main` so shared fixes take effect without per-project pin updates.

Use `.github/dynamic-status.yml` with `schema_version: 1`,
`execution_repository`, `credential_groups`, and optional explicit `sources`.
Each credential group declares an owner allowlist and a `secret_name` referencing
an existing receiver repository secret, not its value. Duplicate keys, duplicate
owners, invalid secret names and unsafe YAML objects/aliases are rejected.
Legacy JSON remains readable while existing default branches migrate.

Each explicit source retains its repository name/ID, standard contexts, allowed
Trigger paths and versioned policies. A policy contains required workflow
filenames/names and optionally `missing_after_seconds` (60–3600). Retain old
policy versions while their batches may still be active.

A single receiver job calls `dyn-status` twice: `mode: route` uses only the
execution read token to resolve the immutable batch and an allowlisted group.
Its outputs `matched`, `group`, `secret_name`, and `execution_sha` come from
validated metadata plus the trusted configuration. `mode: report` receives only
`${{ secrets[steps.route.outputs.secret_name] }}` for that group, then performs the
existing source-receipt and workflow evidence checks. Forwarded data cannot choose
a secret name. Unregistered owners skip without receiving source credentials.

Use the following job gate and no `schedule` trigger:

```yaml
if: >-
  github.event_name == 'workflow_dispatch' ||
  github.event.action == 'completed' ||
  (github.event.action == 'in_progress' &&
   github.event.workflow_run.run_attempt > 1)
```

Serialize the reporting job by immutable execution SHA with
`cancel-in-progress: false`. Put concurrency on the job, after the gate, so a
skipped first-start event cannot displace a pending completion job. An event
reconciles the entire batch, so replacing another pending event for the same batch
does not discard a different batch. Do not use a credential-group-wide queue:
without periodic repair, GitHub replacing a queued job could lose another SHA.

GitHub shares workflow IDs and names across execution branches. Accept all names,
then verify the attested paths/bytes instead of filtering on mutable names. The
current triggering run is read directly from the API, so a stale repository run
listing cannot turn its terminal event back into pending. For a missing required
workflow with no active workflow left to produce a later event, the current job
waits out the configured grace and emits an error; normal running batches return
immediately. Allow a 75-minute receiver timeout for the maximum one-hour policy
grace. This exceptional wait replaces periodic repair, not a normal polling lane.

The receiver verifies a source-owned bot receipt, numeric repository ID,
Trigger run SHA/path/attempt, the complete forwarded workflow set, and byte
equality of every forwarded workflow against the source commit. It reports each
started authenticated workflow; only the policy's required subset contributes to
the aggregate result. It queries current execution runs (latest run and attempt),
then checks the receipt again before writing. Older generations are ignored.
Pending results are reset when a rerun-start event observes the new attempt.

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
A later event or manual reconciliation can repair transient stale writes; no
periodic repair is installed. Do not treat this as cryptographic attestation or an
adversarial merge authorization system.

## Deployment and validation

1. Publish reviewed Kangumi actions.
2. Install the receiver and versioned source registrations on execution default.
3. Land each source failure observer on its default branch before enabling opt-in.
   A first opt-in PR cannot rely on an observer that exists only on its branch.
4. Migrate each source Trigger to source status permissions and Kangumi `@main`;
   remove its previous status-writing job to avoid competing writers.
5. Run a source change and verify pending, a real downstream result, and its Details
   link on the exact source SHA. Verify a cancelled rerun and a missing-workflow
   fixture in a disposable registered source before relying on protection.

Offline tests:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s github-actions/dyn-common -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s github-actions/dyn-status -v
```

Automatic sources also install a completed `workflow_run` failure observer using
`dyn-dispatch@main` with `status-policy: ''`. It closes the exact source
run/attempt's pending dispatch and automatic details after forced cancellation;
completed downstream statuses and newer attempts are preserved.

Event reconciliation is serialized per execution SHA. Each report directly
refreshes listed execution runs as well as its triggering run, so coalesced
completion events do not rely on stale run-list state. An otherwise terminal
automatic batch with undiscovered workflows allows up to 30 seconds for list
propagation; workflows still absent remain `not_started` (for example path
filters), without fabricating statuses for workflows that did not run.

Receiver sources declare their required checks directly, without a named policy:

```yaml
checks:
  version: 1
  workflows:
    - path: check.yml
      name: '[aviary] Check'
  missing_after_seconds: 600
```

The source declaration selects checks version 1; the trusted receiver owns the
required workflow list. Unsupported versions and mixed `checks`/`policies`
configuration fail validation. Legacy `status_policy: checks-v1` inputs and
`policies` configuration remain readable during migration. The existing wire
identifier stays stable so in-flight batches and old branches remain compatible.

Removing a source registration disables its explicit aggregate reporting. Late
completion events from older explicit batches are recorded as skipped, without
writing statuses or falling back to automatic mode. Switch the source Trigger
and its failure observer to automatic mode when removing that registration;
new batches then use the normal per-workflow reporter.
