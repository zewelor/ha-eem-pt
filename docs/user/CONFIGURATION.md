# Configuration

EEM Online is configured only through the Home Assistant UI. Credentials and the
contract number are stored in the config entry. The contract number is the stable
identity used for entities and the Energy statistic.

The integration polls every 12 hours. There is no poll-interval option in the MVP. Each
update fetches the rolling weekly summary and the last 30 complete days of cumulative
meter readings. The known seven-day consumption window is rewritten with absolute
values, so delayed days and operator corrections are applied without double counting.
After a break longer than the weekly summary range, unavailable older days remain gaps
instead of being filled with estimated or zero consumption.

The meter-reading sensor keeps only the latest successful value in memory. If EEM
temporarily rejects the readings request after a Home Assistant restart, that sensor
remains unavailable until the first successful fetch. This does not stop a successful
daily consumption import.

Use **Reconfigure** to replace credentials while keeping the contract and Energy
history. An authentication failure also starts Home Assistant's reauthentication flow.
