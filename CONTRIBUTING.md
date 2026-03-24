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
4. CI picks it up automatically — both workflows discover templates dynamically

Remember: every file in the template directory gets copied to the user's project
via `func create`. Only include files the user would want.

## CI Workflows

| Workflow | What It Does | Triggers |
|---|---|---|
| `invoke-all.yaml` | Builds and invokes every template end-to-end | push to main, PRs, manual |
| `test-templates.yaml` | Runs unit tests via `make test` | push to main, PRs |

Both workflows discover templates dynamically from the directory structure.

## Key Constraints

- **No git submodules** — `func create` does not fetch them. Use vendored deps or
  language-native module systems (e.g. Hugo modules for go/blog).
- **`manifest.yaml`** — Optional per-template config for build settings (builder images,
  buildpacks, envs, health endpoints). Not copied to the user's project. Can be defined
  at repo, language, or template level with inheritance.
