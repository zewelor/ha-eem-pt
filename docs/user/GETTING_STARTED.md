# Getting started

> **Unofficial project.** This community integration is not affiliated with,
> endorsed by, or supported by Empresa de Electricidade da Madeira, S.A. (EEM).
> The EEM name and logo are used only to identify the service with which this
> integration interoperates.

Install EEM Online through HACS, restart Home Assistant, and add **EEM Online** from
**Settings > Devices & services**. The setup form asks for the EEM Online username,
password, and numeric contract number.

After setup, the integration creates one service device with two sensors:

- **Latest daily consumption**, whose `consumption_date` attribute identifies the
  operator day represented by the value;
- **Meter reading**, whose `reading_date` attribute identifies the date of the latest
  cumulative EEM reading.

It also creates the external statistic `eem_online:<contract>_consumption`. Select that
statistic as grid consumption in the Energy Dashboard. The two sensors are compact
status views and are not additional Energy sources.
