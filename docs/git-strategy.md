# Git Strategy for TranscribeNode

## Core Approach: Trunk-Based Development

Single `main` branch. Short-lived branches (hours, not days). Everything merges fast or gets scrapped.

---

## Branch Naming

```
main
task/add-login-flow
experiment/rewrite-parser
fix/null-check-user
```

---

## Merging

- **Fast-forward only** -- no merge commits, keeps history linear
- **Rebase onto `main`** before merging, never merge `main` into your branch
- **No squashing** -- each atomic commit is a meaningful unit; squashing destroys the audit trail

---

## Commits

One commit = one AI task or prompt session. Keep commits atomic and scoped.

AI-generated code has no inherent intent -- the commit message is the only record of *why* this code
exists. Use [Conventional Commits](https://www.conventionalcommits.org):

```
feat(auth): add JWT refresh logic
fix(parser): handle null input on line split
chore(deps): update dependency lockfile
```

Annotate AI-assisted commits in the body, not the subject, to keep the subject readable:

```
feat(auth): add JWT refresh logic

ai-assisted: <model>
```

---

## Feature Flags

Use feature flags to manage incomplete work on `main`. Without them, trunk-based development forces a
choice between blocking merges until a feature is done or shipping incomplete code. Feature flags
remove that tradeoff: merge when the code is safe, release when the feature is ready.

---

## Generated Sources

Do not commit generated source files. They create noisy diffs and painful merge conflicts. Commit
lockfiles for reproducibility; regenerate everything else from source.

---

## Code Review

Review diffs skeptically -- AI code looks clean but can be subtly wrong.

High-blast-radius files always get manual review:

- `.gitignore`
- Anything touching secrets, auth, or permissions
- CI/CD config

---

## CI

CI is load-bearing for trunk-based development -- slow or weak pipelines break the entire strategy.

Before anything merges to `main`:

- All existing tests must pass
- New code must be covered by tests -- AI optimizes for code that *looks* correct, not code that *is* correct
- Build must succeed

---

## Branch Protection

Enforce the strategy at the repo level on GitHub:

- No direct push to `main`, with two exceptions (below)
- Require fast-forward / rebase-based merges
- Require CI to pass before merge

### Direct commits to `main`

Direct commits to `main` are permitted only when:

- The change is non-functional (e.g. documentation, comments, roadmap/ADR updates) and touches no
  application code or tests, or
- The maintainer gives express permission for that specific commit.

Everything else goes through a short-lived branch. Even for allowed direct commits, the commit
conventions (Conventional Commits, AI annotation) still apply.

---

## Versioning

Semantic Versioning (`MAJOR.MINOR.PATCH`), bare numeric tags with no `v` prefix (e.g. `1.0.0`,
`1.1.0`). This keeps tags identical to PyPI/package versions, which don't use a `v` prefix.
