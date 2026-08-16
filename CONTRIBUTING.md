# Contribution guide

This guide defines security expectations, branch naming, commit messages, testing, documentation, and pull-request review standards.

## Creating a branch

Create a branch from an up-to-date main branch.

Use lowercase, hyphen-separated names with one of these prefixes:

| Change | Branch pattern | Example |
|---|---|---|
| Feature | `feature/<name>` | `feature/document-status-polling` |
| Bug fix | `fix/<name>` | `fix/pdf-page-citation` |
| Documentation | `docs/<name>` | `docs/docker-setup` |
| Test | `test/<name>` | `test/retrieval-integration` |
| Refactor | `refactor/<name>` | `refactor/source-extractors` |
| Maintenance | `chore/<name>` | `chore/update-dependencies` |

Keep each branch focused on one logical change.

## Writing commit messages

Use a short imperative subject describing what the commit changes:

```text
<type>: <short description>
```

Recommended types:

- `feat`: new functionality.
- `fix`: bug correction.
- `docs`: documentation only.
- `test`: test additions or corrections.
- `refactor`: internal restructuring without behavior change.
- `chore`: maintenance or tooling.

Examples:

```text
feat: poll uploaded document status
fix: preserve one-based PDF page citations
docs: add Docker deployment guide
test: cover session-history propagation
```

Keep the subject concise. Add a body when the reason, trade-off, migration, or operational impact is not obvious.

## Before opening a pull request

1. Review the diff and remove unrelated or generated files.
2. Confirm `.env`, API keys, uploads, SQLite databases, and private screenshots are not included.
3. Run backend tests:

   ```bash
   uv run pytest tests -q
   ```

4. Run frontend validation when frontend code changes:

   ```bash
   npm --prefix frontend run lint
   npm --prefix frontend run build
   ```

5. Update README, API reference, screenshots, environment examples, or architecture documentation when behavior or configuration changes.

## Pull-request description

Every pull request should include:

- A short description of the work completed.
- The reason for the change.
- Important implementation or architecture decisions.
- Tests performed and their results.
- Documentation updated.
- Configuration, migration, deployment, or compatibility impact.
- Screenshots for visible frontend changes when useful.
- Known limitations or follow-up work.
