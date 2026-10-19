# Feature Specification: AlphaESS Home Assistant Integration

**Feature Branch**: `001-alphaess-ha-integration`

**Created**: 2026-10-18

**Status**: Draft (clarified)

**Input**: User description: "I have created a python package to get data from my alphaess inverter. I already started some years ago with a home assistant integration. But a lot of changes happened to the home assistant repository so I think it's best to start again with your help."

## Context

The owner of an AlphaESS home energy storage system (inverter, battery, optional PV strings and EV charger) wants to see and use its data inside Home Assistant. The AlphaESS cloud ("AlphaESS Open API") exposes this data to registered developers through an AppID and AppSecret. A client library for this cloud already exists and is maintained by the same author (`alphaess-aio`). An earlier attempt at the integration only reached the setup dialog and is outdated against current Home Assistant conventions; this feature starts the integration again from scratch.

## Clarifications

### Session 2026-10-18

- Q: Should controlling the system be part of the first version? → A: No. Version 1 only shows data (Stories 1–3). Battery charge/discharge settings and EV charger monitoring/control are deferred to a later feature.
- Q: Core integration or HACS? → A: HACS first, built to core standards so it can be submitted to Home Assistant core later.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Connect the AlphaESS account and see live power flows (Priority: P1)

A Home Assistant user adds the AlphaESS integration from the integrations page, enters the AppID and AppSecret they received from the AlphaESS developer portal, and every AlphaESS system bound to that account appears as a device. Each device shows the current PV power, house load, grid power (import/export), battery power and battery state of charge, refreshed automatically.

**Why this priority**: Without a working connection and live values there is no integration at all. This alone already replaces checking the AlphaESS app and enables dashboards and automations based on surplus power or battery level.

**Independent Test**: Add the integration with valid credentials for an account with at least one bound system; verify a device per system appears with live power and state-of-charge values that match the AlphaESS app within one refresh cycle.

**Acceptance Scenarios**:

1. **Given** a user with valid AppID/AppSecret and one bound system, **When** they complete the setup dialog, **Then** one device for that system is created, named after its serial number and showing inverter and battery model, and live power sensors show current values.
2. **Given** an account with two bound systems, **When** setup completes, **Then** two separate devices exist, each with its own set of sensors.
3. **Given** the setup dialog, **When** the user enters credentials that AlphaESS rejects, **Then** the dialog shows an "invalid credentials" error and nothing is created.
4. **Given** the setup dialog, **When** the AlphaESS cloud cannot be reached, **Then** the dialog shows a "cannot connect" error and the user can retry.
5. **Given** an account that is already configured, **When** the user tries to add the same AppID again, **Then** setup is aborted with an "already configured" message.
6. **Given** a configured integration, **When** the grid meter reports per-phase values or the system has several PV strings, **Then** per-phase grid power and per-string PV power are available as additional sensors (disabled by default if not commonly needed).

---

### User Story 2 - Track energy in the Energy dashboard (Priority: P2)

The user opens the Home Assistant Energy dashboard and selects AlphaESS sensors for solar production, grid consumption, grid feed-in, battery charge and battery discharge. Daily energy figures accumulate correctly and reset at midnight, so the dashboard shows correct daily, weekly and monthly totals.

**Why this priority**: Energy tracking is the most common reason to integrate a PV/battery system with Home Assistant; it builds directly on the connection from Story 1.

**Independent Test**: After setup, configure the Energy dashboard with the AlphaESS energy sensors only; after one full day the dashboard totals match the daily totals in the AlphaESS app within rounding.

**Acceptance Scenarios**:

1. **Given** a configured system, **When** the user opens the Energy dashboard configuration, **Then** AlphaESS sensors for PV generation, grid import, grid export, battery charge and battery discharge are offered as selectable sources.
2. **Given** energy sensors running through midnight, **When** the AlphaESS daily counters reset, **Then** long-term statistics record no negative or doubled energy for the new day.
3. **Given** a configured system, **When** the user views the device, **Then** summary values such as today's load consumption, total PV generation, self-consumption rate and self-sufficiency rate (as percentages) are also shown.
4. **Given** a system with an EV charger, **When** the user views the device, **Then** EV charging energy of the day is available as a sensor.

---

### User Story 3 - Stay informed when the connection breaks and fix it in place (Priority: P3)

When the AlphaESS cloud is temporarily unreachable, the sensors show as unavailable instead of keeping stale values, and recover by themselves. When the AppSecret is revoked or changed, Home Assistant prompts the user to re-enter credentials without having to delete and re-add the integration. Support data can be downloaded with secrets removed.

**Why this priority**: A cloud-polling integration will inevitably hit outages and credential changes; graceful handling keeps history intact and avoids support effort, but the integration is already usable without it.

**Independent Test**: With a running integration, block network access to the AlphaESS cloud, observe sensors become unavailable and recover after access is restored; then change the AppSecret and verify a re-authentication prompt appears and accepting new valid credentials restores all sensors.

**Acceptance Scenarios**:

1. **Given** a running integration, **When** the cloud fails to respond, **Then** all affected sensors become unavailable and become available again automatically after the next successful refresh.
2. **Given** a running integration, **When** AlphaESS rejects the stored credentials, **Then** a re-authentication notification appears and the integration stops polling until new credentials are entered.
3. **Given** a re-authentication prompt, **When** the user enters valid credentials for the same account, **Then** the integration resumes with all existing devices, sensors and history unchanged.
4. **Given** a running integration, **When** the user downloads diagnostics, **Then** AppID, AppSecret and serial numbers are redacted.
5. **Given** a system that is unbound from the AlphaESS account, **When** the integration is reloaded, **Then** the corresponding device is removed or can be removed by the user.

---

### Edge Cases

- The account has no bound systems: setup completes with a clear message that no systems were found, or aborts explaining that a system must be bound in the AlphaESS portal first.
- AlphaESS returns no value for a field (e.g. no PV detail, no EV charger, single-phase meter): the related sensor is not created or shows as unknown, never as 0.
- AlphaESS returns the self-consumption and self-sufficiency rates as fractions (0–1) although documented as percent: the integration shows them as percentages (0–100).
- A daily counter is reported with a slight delay after midnight or temporarily reports yesterday's total: statistics must not count the day twice.
- Requests are rate-limited or slow: one refresh cycle must not overlap with the next, and a slow response must not block Home Assistant.
- A new system is bound to the account after setup: it appears after the integration is reloaded.
- The same AlphaESS account is added twice: prevented by the "already configured" check.

## Requirements *(mandatory)*

### Functional Requirements

**Setup and account**

- **FR-001**: Users MUST be able to add the integration through the Home Assistant user interface by entering an AppID and AppSecret; no file editing is required.
- **FR-002**: The setup MUST validate the credentials against the AlphaESS cloud before saving and report "invalid credentials", "cannot connect" or "unknown error" distinctly.
- **FR-003**: The integration MUST prevent the same AppID from being configured more than once.
- **FR-004**: Users MUST be able to re-enter credentials when they are rejected (re-authentication) and to change them on purpose (reconfiguration) without losing devices, entities or history.
- **FR-005**: The integration MUST create one device per AlphaESS system bound to the account, identified by its serial number and showing manufacturer, inverter model and battery model where available.

**Data**

- **FR-006**: The integration MUST provide live sensors for PV power, load power, grid power, battery power and battery state of charge for each system, plus EV charging power where an EV charger is present.
- **FR-007**: Grid power MUST follow a single, documented sign convention (positive = import from grid, negative = export to grid), and separate non-negative "grid import power" and "grid export power" values SHOULD be offered for users who need them.
- **FR-008**: The integration MUST provide per-string PV power, per-phase grid power and per-phase inverter output where the system reports them; these MAY be disabled by default.
- **FR-009**: The integration MUST provide daily energy sensors for PV generation, grid import, grid export, battery charge, battery discharge, battery charge from grid and (where present) EV charging, suitable for selection in the Home Assistant Energy dashboard.
- **FR-010**: The integration MUST provide summary sensors for today's load consumption, total PV generation, self-consumption rate and self-sufficiency rate (as 0–100 %).
- **FR-011**: The integration MUST provide static system information (battery capacity, usable capacity, nominal inverter power, nominal PV power) as diagnostic values.
- **FR-012**: All values MUST carry correct units (W, kWh, %, kW, kWp) and Home Assistant device/state classes so they work in history, statistics and the Energy dashboard without extra configuration.
- **FR-013**: Live power data MUST refresh at a fixed interval of 60 seconds; daily energy and summary data MAY refresh less often (at most every 5 minutes) to respect AlphaESS rate limits.
- **FR-014**: When a refresh fails, affected entities MUST become unavailable; they MUST become available again automatically after the next successful refresh.
- **FR-015**: When AlphaESS rejects the credentials during operation, the integration MUST start the re-authentication flow and stop polling until resolved.

**Operations**

- **FR-016**: The integration MUST offer downloadable diagnostics with AppID, AppSecret and serial numbers redacted.
- **FR-017**: All user-facing texts (setup dialog, errors, entity names) MUST be translatable, with English provided; German SHOULD be provided.
- **FR-018**: The integration MUST be installable as a custom integration via HACS, and MUST be built so that it can later be submitted to Home Assistant core without functional rework (core conventions, quality-scale rules and test structure apply from the start).
- **FR-019**: Credentials MUST be stored only in Home Assistant's configuration storage and MUST NOT appear in logs.

### Key Entities

- **AlphaESS account**: The developer access identified by AppID and AppSecret; one integration entry per account; owns one or more systems.
- **System**: One AlphaESS installation identified by serial number; has inverter model, battery model, battery capacity, nominal PV and inverter power; represented as a device.
- **Live power snapshot**: Current PV, load, grid, battery and EV power plus battery state of charge of a system, with optional per-string and per-phase detail.
- **Daily energy record**: Energy totals of the current day per system (PV, grid import/export, battery charge/discharge, grid charge, EV charging).
- **System summary**: Aggregated figures such as today's load, total PV generation, self-consumption and self-sufficiency rates, income.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user with valid credentials can go from "Add integration" to seeing live values for all their systems in under 2 minutes, without reading external documentation.
- **SC-002**: Live power values shown in Home Assistant differ from the AlphaESS app by no more than one refresh interval (≤ 60 seconds of staleness).
- **SC-003**: After one full day of operation, daily totals in the Energy dashboard match the AlphaESS app's daily totals within 1 % or 0.1 kWh, whichever is larger.
- **SC-004**: After a cloud outage of any length, all entities recover without user action within one refresh interval after the cloud is reachable again.
- **SC-005**: After a credential change, the user can restore full operation through the re-authentication prompt in under 1 minute, with 100 % of entity history preserved.
- **SC-006**: Every setup error path (invalid credentials, no connection, already configured, unknown error) shows a specific message, verified by automated tests.
- **SC-007**: Automated tests cover the setup flow, data refresh, error handling and every entity type, running entirely without access to the real AlphaESS cloud.

## Assumptions

- Users already registered at the AlphaESS developer portal (open.alphaess.com), bound their system(s) there and have an AppID and AppSecret.
- The integration uses the existing `alphaess-aio` client library for all communication with the AlphaESS cloud; missing capabilities are added to that library, not worked around in the integration.
- Only the AlphaESS cloud is used; local (on-network) communication with the inverter is out of scope.
- One integration entry represents one AlphaESS account; multiple accounts can be added as separate entries.
- The intraday power curve (sample history) and system binding/unbinding via verification code are not exposed in Home Assistant, as they are better handled by Home Assistant's own history and the AlphaESS portal.
- Income and CO2/tree figures are optional extras and may be included as disabled-by-default sensors.
- Out of scope for this feature (deferred to a later feature): changing battery charge/discharge settings, the EV charger device with its status and current limit, and starting/stopping EV charging. EV charging power and daily EV charging energy are still shown as part of the system's data.
- The previous integration attempt is not migrated; existing users (if any) re-add the integration.
- The refresh interval is not user-configurable, following current Home Assistant guidance for polling integrations.
