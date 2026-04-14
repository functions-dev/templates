# Contributing to Function Templates

## Running Tests

```bash
make test            # all runtimes
make test-go         # single runtime
make test-python     # etc.
```

Detailed logs go to `test-results.log`. Skipped templates and reasons are listed
at the top of the Makefile.

## Adding a New Template

1. Create `<language>/<template-name>/` with function source files
2. Add tests following existing patterns per language:
   - Go: `*_test.go`
   - Python: `tests/test_func.py`, deps in `pyproject.toml` (under `dependencies` or `[project.optional-dependencies] dev`)
   - Node: `test/unit.js` + `test/integration.js`, `npm test` script in `package.json`
   - TypeScript: `test/unit.ts` + `test/integration.ts`, `npm test` script in `package.json`
   - Rust: `#[cfg(test)]` module in `handler.rs`
   - Quarkus/SpringBoot: `src/test/java/`
3. If it needs external services, add to the skip list in Makefile with a comment
4. If the template needs an e2e test (external services, real integrations), add
   `.testing/<language>/<template>/test.sh` — it will be discovered automatically
5. CI picks it up automatically — all workflows discover templates dynamically

## CI Workflows

CI uses reusable workflows (`_invoke.yaml`, `_e2e.yaml`) called by two runners:

| Workflow | func CLI version | Triggers |
|---|---|---|
| `ci.yaml` | `latest` (stable) | push to main, PRs, manual |
| `nightly.yaml` | `nightly` (tip-of-main) | daily at 10:00 UTC, push to main, PRs, manual |

Manual triggers (`workflow_dispatch`) on `ci.yaml` let you override the func CLI
version and filter to a specific e2e test (e.g. `python/keycloak-auth`).

Both run the same jobs:

| Reusable Workflow | What It Does |
|---|---|
| `_invoke.yaml` | Builds and invokes every template (create → build → run → invoke) |
| `_e2e.yaml` | Runs e2e tests from `.testing/` (all on main/schedule, discovery on PRs) |
| `test-templates.yaml` | Runs unit tests via `make test` (push to main, PRs) |

The **CI** badge shows stability against the latest func release. The **Nightly**
badge catches upstream regressions early.

## Key Constraints

- **No git submodules** — `func create` does not fetch them. Use vendored deps or
  language-native module systems (e.g. Hugo modules for go/blog).
- **`manifest.yaml`** — Optional per-template config for build settings (builder images,
  buildpacks, envs, health endpoints). Not copied to the user's project. Can be defined
  at repo, language, or template level with inheritance.
