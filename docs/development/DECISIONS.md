# Decisions

## Daily summary is the only MVP consumption source

The integration fetches `resumo/ultimasemana` every 12 hours. Fifteen-minute samples
would add pagination, completeness rules, DST interval handling, and more requests
without being needed for daily Energy reporting.

## Meter readings are display-only

The same 12-hour coordinator fetches the last 30 complete Madeira days from `leituras`
and exposes only the newest valid `totalRegistadores`. The sensor has no `state_class`:
its delayed operator date cannot be represented by the current entity-state timestamp,
so it must not create a second Energy history. The integration retains no local reading
history and does not calculate consumption deltas.

Summary and meter-reading failures are tracked separately. Either source may update on
its own; only failure of both makes the coordinator update fail. Authentication failure
from either source starts reauthentication.

## Energy uses an external statistic

Historical daily values are imported as
`eem_online:<contract>_consumption`, with `state` equal to the day's consumption and
`sum` equal to cumulative known consumption. Writing old days as the current state of a
sensor would give recorder the wrong timestamps and would not backfill Energy history.

## Corrections use a seven-day overlapping window

Every update merges the weekly EEM values with the recorder's existing window,
preserves days omitted from an incomplete response, recalculates all sums after a
changed day, and upserts the complete window. Absolute rows make an identical retry
idempotent. There is no additional Store or history cache; an interrupted import is
retried by the next synchronization.

## The API client stays inside the integration

The reverse-engineered API is small and uses one login plus two read endpoints. A
separately published client library would add release and compatibility work without
reducing the MVP implementation.
