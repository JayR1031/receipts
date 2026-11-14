# Tracker conventions (github)

- Branch: `<user>/<ticket-key>-<slug>`; the ticket key is the tracker's own (for GitHub Issues, `gh-<number>`).
- PR title starts with the ticket key. One ticket per PR; one PR per ticket unless stacked.
- Statuses: Backlog → Todo → In Progress → In Review → Done. Nothing is Done without a merged PR.
- Labels: `type:bug`, `type:task`, `type:decision`, `blocked`, `security`.
- Decisions are recorded as ADRs in `docs/adr/`, then linked from the ticket. A chat message is not a decision record.
