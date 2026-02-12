# Codex Project Rules

## Core Principles
- Prefer small, focused files; split large components and utilities.
- Use immutable data patterns; avoid in-place mutation.
- Handle errors explicitly and return user-safe messages.
- Validate all external input (user, API, env, DB).
- Avoid `console.log` in production code.
- For Cloud Run storage minimization: keep only 1 revision and 1 image for each deployed service (use cleanup policies + post-deploy pruning).

## Development Mode
Use when implementing features or fixing bugs.
- Write code first, explain after.
- Favor working solutions over perfect solutions.
- Run relevant tests after changes.
- Keep commits atomic.

## Default Agent Behavior
- Default to using the `planning-with-files` skill for task execution unless the user explicitly asks for a different flow.
- When documentation lookup is needed, use Context7 first and prioritize official vendor/library documentation as primary sources.

## Review Mode
Use when the user asks for a review.
- Read thoroughly before commenting.
- Prioritize issues by severity (critical > high > medium > low).
- Suggest fixes, not just problems.
- Check security, performance, edge cases, and test coverage.
- Group findings by file and severity.

## Research Mode
Use when asked to investigate or explore.
- Read broadly before concluding.
- Ask clarifying questions.
- Document findings as you go.
- Do not write code until understanding is clear.
- Provide findings first, recommendations second.

## Testing Requirements
- Follow TDD: RED -> GREEN -> IMPROVE.
- Target 80%+ coverage when test tooling is available.
- Use unit, integration, and E2E tests for critical flows.

## Security Requirements
Before any commit:
- No hardcoded secrets.
- Validate all inputs.
- Use parameterized queries; prevent injection.
- Prevent XSS/CSRF where applicable.
- Verify authz/authn and rate limiting.
- Avoid sensitive data in error messages.

## Git Workflow
- Commit message format: `<type>: <description>` (feat, fix, refactor, docs, test, chore, perf, ci).
- For PRs: review full diff, write clear summary, include test plan.

## Deployment Workflow
- After every Cloud Run deploy, run post-deploy pruning immediately.
- Target state per service: keep exactly 1 Cloud Run revision and 1 Artifact Registry image.
- Use `scripts/prune_cloud_run_artifacts.py --service <service> --region <region> --image <artifact_package> --keep 1`.
- Verify cleanup result after pruning (`gcloud run revisions list` and `gcloud artifacts docker images list`).

## Issue Workflow
- Pick a backlog item from the Project board.
- If an issue has the `to_plan` label, write a plan first and update the issue before implementation.
- Move the item to In progress when work starts.
- Open a PR and move the item to In review.
- Merge the PR and move the item to Done.
- For a completed issue, push branch, open PR, review (note: cannot approve own PR), merge, then move item to Done.
- Do not start the next issue until the current issue has finished the full flow (push, PR, review/merge, move to Done).
- If interrupted, stop and confirm the current issue's status before proceeding.
- After finishing an issue, return to `main` and ensure local `main` is up to date with `origin/main` before starting the next issue.

## GitHub Project Info
- Project board: https://github.com/users/edwardyangxin/projects/1/
- use skill to get issues info to work on
- Auth: use `gh auth login` to authenticate (required for Project GraphQL updates)
- Kanban: use `github-project-collab` skill to view Project items
- Issues repo(s): Gatchan

## Patterns to Prefer
- Service layer + repository pattern for data access.
- API response wrappers with `success`, `data`, `error`, `meta`.
- Use proven skeletons when starting new features.
