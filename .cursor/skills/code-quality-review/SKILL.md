---
name: Code Quality Review
description: Conduct a comprehensive code quality review focused on clean code, architecture, and project standards.
disable-model-invocation: false
---

# Code Quality Review

You are an expert code quality reviewer.

## Pre-requisites

Read before reviewing:

1. **Clean code (required):** `.cursor/rules/agent-clean-code.mdc`
2. **Product layout:** `.cursor/rules/architecture-principles.mdc`
3. **Backend:** `.cursor/rules/python-best-practices.mdc` (when reviewing `src/asap/` or `tests/`)
4. **Frontend:** `.cursor/rules/frontend-best-practices.mdc` (when reviewing `apps/web/` or `packages/ui/`)
5. **Tests:** `.cursor/rules/testing-standards.mdc` (when the diff adds or changes tests)
6. **Security (ingress/auth changes):** `.cursor/rules/security-standards.mdc`
7. **Git hygiene:** `.cursor/rules/git-commits.mdc`
8. **Agent index:** `.cursor/README.md`

## Review process

### 1. Structure and architecture

- Check separation of concerns; code in the right layer per `architecture-principles.mdc`.
- Identify logic that belongs in services, handlers, or components.
- Flag functions longer than **40 lines** (split per `agent-clean-code.mdc`).

### 2. Standards compliance

- **Types:** Are all public functions and methods typed?
- **Docs:** Do public APIs have docstrings (intent + example)?
- **Tests:** Per `agent-clean-code.mdc` test policy — regression tests for bugs, tests for new public APIs in `src/asap/`.

### 3. Error handling

- Are exceptions caught specifically (not bare `except`)?
- Do error messages include the offending value and expected shape?
- Is there structured logging for failures?

## Output format

Provide analysis with:

- **Severity:** Critical / Major / Minor
- **Location:** File and line
- **Recommendation:** Code snippet of the fix
