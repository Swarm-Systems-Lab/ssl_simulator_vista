# Contributing

Thanks for contributing to `ssl_vista`.

## Development setup

```bash
git clone https://gitea.lyapunov.local/Swarm-Systems-Lab/ssl_simulator_vista
cd ssl_vista
just setup
just test
```

## Branch and commit workflow

1. Create a branch from main:

```bash
git checkout -b feature/my-change
```

2. Make focused changes in code/docs.
3. Run local checks.
4. Commit with a clear message.
5. Open a PR.

## Required checks before PR

```bash
just lint
just test
just typecheck
just security
just docs-build
just validate-docs
```

Or run the aggregate check and docs checks:

```bash
just check-all
just docs-build
just validate-docs
```

## Code guidelines

- Keep changes minimal and scoped.
- Preserve existing style and architecture.
- Add or update tests when behavior changes.
- Update documentation when public behavior changes.
- Prefer explicit errors over silent failures.

## Docs guidelines

- Keep docs aligned with real commands and current code paths.
- Use layout and data examples from `src/ssl_vista/data/grid_layouts` and `src/ssl_vista/data/samples`.
- If you add a new user-visible feature, update:
  - `docs/usage.md`
  - one of `docs/layout-schema.md`, `docs/data-schema.md`, or `docs/plotter-development.md`
  - `README.md` (if onboarding flow changes)

## Test guidance

Current automated tests are limited. If you modify runtime behavior:

- add focused tests where possible
- run the relevant app/doc commands locally
- include manual verification steps in your PR description

## Reporting issues

For bug reports, include:

- exact command used
- traceback/error output
- layout JSON used
- sample data details
- OS, Python version, and package versions
