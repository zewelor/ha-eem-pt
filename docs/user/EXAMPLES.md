# Energy Dashboard example

In **Settings > Dashboards > Energy**, add an electricity grid consumption source and
select **EEM Online `<contract>` consumption**. The imported statistic contains the
daily historical values and cumulative sums needed by the dashboard.

Do not select either sensor as a second source. Latest daily consumption shows only one
operator day, while Meter reading is a delayed cumulative status without a Home
Assistant statistics state class. The external statistic remains the only Energy source.
