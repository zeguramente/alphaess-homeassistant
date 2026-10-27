# Open tasks

Open tasks from the spec-kit `tasks.md` files, which were removed on 2026-10-19.
File names in a section refer to that feature's folder in `specs/`.
The complete task lists are in git history: `git show 074cd92:specs/<feature>/tasks.md`.

## [001-alphaess-ha-integration](specs/001-alphaess-ha-integration/)

- [ ] T041 Run the manual end-to-end check in [quickstart.md](specs/001-alphaess-ha-integration/quickstart.md) section 3 with the real system; record the observed battery power sign in `README.md` and in the `battery_power` row of `specs/001-alphaess-ha-integration/contracts/entities.md`; if the sign is opposite to the expectation, adjust nothing in code (values are passed through) but document it.
- [ ] T042 Confirm the domain `alpha_ess` with the maintainer (research R2) before tagging `v0.1.0`; then create the first GitHub release so HACS can install it.
