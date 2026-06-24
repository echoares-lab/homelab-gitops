# Agent Working-Tree and PR Hygiene

This guide complements the mandatory standards in
[`AGENTS.md`](../AGENTS.md). If there is any conflict, follow `AGENTS.md`.

## Claim and Scope

Before starting work on a GitHub issue, leave a claim comment on that issue so
parallel agents can see ownership. Keep each branch and pull request limited to
one issue or one tightly related task. If unrelated problems are discovered,
note them in the issue or PR instead of folding them into the active change.

## Working Tree Expectations

Start from a clean working tree when possible. If the checkout already contains
unrelated dirty files, do not clean, revert, delete, or stage them. Create an
isolated branch or worktree for the current issue, then verify `git status -sb`
inside that workspace before editing.

Treat ignored local state as disposable runtime state, not source. Examples
include local environment files, caches, coverage reports, rendered inventories,
OpenTofu state, generated Ignition or Butane files, and temporary Ansible output.
Do not add those files to a PR unless the issue explicitly asks to change how
they are tracked.

When generated artifacts are needed for validation, regenerate them locally and
leave them out of the commit unless they are documented source fixtures. If a
generated file appears tracked or ambiguous, compare against the
[Artifact and State Hygiene Inventory](./ARTIFACT_STATE_HYGIENE.md) and call out
the ambiguity in the PR rather than silently removing or rewriting it.

## PR Hygiene

Stage only files that belong to the issue. Before committing, review
`git status -sb` and the diff so the PR does not absorb unrelated agent or user
work.

Pull requests should close the issue they implement, describe the verification
performed, and preserve the one-issue/one-PR boundary. After opening the PR,
enable auto-merge when repository permissions and branch protection allow it, as
required by [`AGENTS.md`](../AGENTS.md#4-pull-request-submission). Never weaken
required reviews or checks to merge faster.
