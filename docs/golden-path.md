# Golden path

This is the recommended day-to-day workflow for contributors.

## Toolchain

- `uv` for dependency and environment management
- `just` as task runner
- `tox` for reproducible env-specific checks
- `ruff`, `ty`, `pytest`, and `semgrep` for quality checks
- `mkdocs` + `mkdocstrings` for docs

## First-time setup

```bash
git clone https://gitea.lyapunov.local/Swarm-Systems-Lab/ssl_simulator_vista
cd ssl_vista
just setup
just test
```

## Daily development loop

```bash
git pull
just setup

# make code changes
just test-fast
just lint
just typecheck

# before push
just check-all
just docs-build
```

## Command reference

## Environment and setup

- `just setup`: lock + install dev/lint/tests/type-checking/pre-commit extras
- `just sync`: sync frozen lockfile
- `just clean`: remove build/test/cache artifacts

## Quality and tests

- `just lint`: run formatter + lint auto-fixes
- `just typecheck`: run static type checks
- `just security`: run semgrep scan
- `just test`: run tox `tests` env
- `just test-fast`: run tox `tests-fast` env
- `just test-multi-py`: run tests on `py310,py311,py312,py313`
- `just list`: list tox environments

## Packaging and release

- `just build`: build package artifacts
- `just publish`: publish using uv-based script
- `just publish-ci`: publish using twine-based CI script

## Documentation

- `just docs`: start MkDocs live server
- `just docs-build`: build docs via tox
- `just validate-docs`: run docs validation script
- `just clean-docs`: remove built site directory

## CI simulation

Use this before opening or updating a PR:

```bash
just check-all
just docs-build
just validate-docs
```

## Notes

- Source package lives under `src/ssl_vista`.
- Current project test coverage is minimal; prioritize adding tests around modified behavior.
- For simulator data contracts and plotter contracts, see [Data schema](data-schema.md) and [Plotter development](plotter-development.md).
