# ECS Runner Workflow Examples

This directory contains ready-to-use GitHub Actions workflows demonstrating different ways to use `kangumi/github-actions/ecs-github-runner`.

## Workflows

### `simple.yml`

- **Scenario**: Minimal setup with a single job executed on the temporary ECS runner.
- **Jobs**:
  1. Provision runner via the action (`mode: start`).
  2. Run a simple workload on the runner.
  3. Destroy the ECS instance and remove the GitHub runner registration.
- **When to use**: Basic smoke tests, ad-hoc builds, or as a template to plug your own job in the middle.

### `multi-job.yml`

- **Scenario**: Provision once, run multiple dependent jobs (smoke test + Rust crate build/test), then destroy.
- **Highlights**:
  - Shows how to keep the runner alive (`runner_ephemeral: "false"`) and reuse it across jobs.
  - Demonstrates a password-generation job feeding into the provision step.
  - Ends with the same destroy/cleanup routine as `simple.yml`.
- **When to use**: CI flows where several jobs must run sequentially on the same ECS machine (e.g., test suites, build→deploy pipelines).

### `non-std.yml`

- **Scenario**: Mainland Nonstd/bandwidth-restricted environment where GitHub cannot reach the ECS runner directly.
- **Highlights**:
  - Turns off runner registration (`register_runner: "false"`) and outputs the generated password (`expose_instance_password: "true"`).
  - Provides a job that prints connection info so operators can SSH in manually.
  - Destroy job still tears down the ECS instance, but runner cleanup is skipped because no registration occurred.
- **When to use**: Provision servers inside Nonstd that will be accessed manually (or through another automation layer) rather than through GitHub Actions.

## Required inputs (common to both)

- `ALI_*` secrets (Access Key, Secret Key, Region)
- `GH_RUNNER_PAT` secret with permissions to create/remove self-hosted runners
- Repository variables for VSwitch, Availability Zone, Security Group, and Image ID (or replace with hard-coded values)

## Cleanup

Both workflows finish by:
1. Calling the action with `mode: destroy` to tear down the ECS instance.
2. Invoking `kangumi/github-actions/remove-self-hosted-runner` to delete the runner record from the repository.

Ensure these steps remain even if you customize the workflows, otherwise lingering ECS instances or offline runners may accumulate.
