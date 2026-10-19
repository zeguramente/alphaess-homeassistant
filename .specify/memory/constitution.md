<!--
Sync Impact Report
- Version change: (template, unversioned) → 1.0.0
- Modified principles: placeholders replaced by
  I. Library-First Cloud Access
  II. Current Home Assistant Conventions
  III. Test-First, Offline Tests
  IV. Respect the Device and the Cloud
  V. Simple, Self-Explanatory Code
- Added sections: Technical Constraints, Development Workflow, Governance
- Removed sections: none
- Templates: plan-template.md, spec-template.md, tasks-template.md read the constitution at
  runtime; no changes required.
- Deferred TODOs: none. Distribution target (core vs. HACS) is a feature decision tracked in
  specs/001-alphaess-ha-integration/spec.md (FR-022); Principle II applies to both.
-->

# AlphaESS Home Assistant Integration Constitution

## Core Principles

### I. Library-First Cloud Access

All communication with the AlphaESS cloud MUST go through the `alphaess-aio` library.

- The integration MUST NOT build HTTP requests, sign requests or parse raw API responses itself.
- Missing endpoints, fields, validation or error types MUST be added to `alphaess-aio`, released,
  and then consumed by the integration; workarounds in the integration are not allowed.
- The integration MUST pass Home Assistant's shared HTTP session to the library and depend on a
  pinned, published library version.

Rationale: protocol knowledge lives in one tested place, and the integration stays small enough
to meet Home Assistant review standards.

### II. Current Home Assistant Conventions

The integration MUST follow the current Home Assistant developer documentation and quality scale,
regardless of whether it ships in core or via HACS.

- Setup MUST be UI-only (config flow); YAML configuration is not supported.
- Data MUST be fetched centrally by update coordinator(s) and shared by entities; entities MUST NOT
  call the cloud on their own.
- Entities MUST use entity descriptions, `has_entity_name`, translation keys, unique IDs based on
  serial numbers, and correct device/state classes and units.
- Re-authentication, reconfiguration, diagnostics with redaction, and entity unavailability on
  failed updates MUST be implemented.
- The Bronze quality-scale rules are the minimum for any release; Silver is the target for v1.
- Deviations from Home Assistant conventions MUST be documented with a reason in the plan.

Rationale: Home Assistant internals change often; this restart exists because the previous attempt
fell behind. Tracking the official rules keeps the integration mergeable and maintainable.

### III. Test-First, Offline Tests (NON-NEGOTIABLE)

- Tests MUST be written before or together with the code they cover, and MUST fail before the
  implementation exists.
- Tests MUST run without network access, using the `alphaess-aio` client mocked at its public
  interface and recorded JSON fixtures; the real AlphaESS cloud MUST NOT be contacted in tests.
- The config flow MUST have 100 % test coverage, including every error and abort path.
- Every entity platform MUST have tests; snapshot tests are preferred for entity states and
  attributes.

Rationale: the cloud is rate-limited, changes settings at most about once per day, and is not
available in CI; offline tests are the only reliable feedback loop.

### IV. Respect the Device and the Cloud

- Polling MUST NOT be more frequent than every 60 seconds for live data and every 5 minutes for
  daily energy and summary data, and MUST NOT be user-configurable.
- Write operations (charge/discharge settings, EV charger commands) MUST be explicit user or
  automation actions, MUST validate input before sending, and MUST surface refusals as errors
  instead of failing silently.
- Credentials and serial numbers MUST NOT appear in logs and MUST be redacted in diagnostics.
- Missing values MUST be reported as unknown, never as 0.

Rationale: the integration controls real hardware and shares a rate-limited cloud account; wrong
or silent behavior costs money and trust.

### V. Simple, Self-Explanatory Code

- Code MUST follow the personal Python style: names that explain the code instead of comments,
  comments only for the non-obvious why, Google-style docstrings, a leading underscore for
  module-internal helpers, and small focused modules.
- Features MUST NOT be added speculatively; build only what the current spec requires (YAGNI).
- Fully typed code is required; `Any` needs a reason.

Rationale: a single-maintainer project stays maintainable only if the code is easy to read years
later.

## Technical Constraints

- Language: Python, at the version required by the targeted Home Assistant release.
- Fully async; no blocking I/O in the event loop.
- Tooling: `uv` for environments and dependencies, `ruff` for lint and format, `mypy` for type
  checks, `pytest` for tests.
- Cloud-only (`cloud_polling`); local inverter communication is out of scope unless a future
  amendment adds it.
- User-facing strings MUST be translatable; English is required, German is provided as well.

## Development Workflow

- Work follows the Spec Kit flow: specify → clarify (as needed) → plan → tasks → implement.
- Every plan MUST include a Constitution Check against Principles I–V; violations MUST be
  justified in the plan's complexity tracking or resolved.
- A change is done only when ruff, mypy and the full test suite pass locally.
- Changes that need new library capabilities are split: library change and release first, then
  the integration change.
- Commits use Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`).

## Governance

This constitution takes precedence over other project practices. Amendments are made through
`/speckit-constitution`, recorded with a Sync Impact Report, and versioned semantically:

- MAJOR: a principle is removed or redefined incompatibly.
- MINOR: a principle or section is added or materially expanded.
- PATCH: clarifications and wording without change of meaning.

Plans and reviews MUST verify compliance with the principles above. When Home Assistant changes its
developer rules, Principle II follows the new rules and the constitution is amended if a concrete
rule written here conflicts with them.

**Version**: 1.0.0 | **Ratified**: 2026-10-18 | **Last Amended**: 2026-10-18
