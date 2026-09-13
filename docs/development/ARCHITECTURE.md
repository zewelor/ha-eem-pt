# Architecture

The integration keeps the package layout supplied by the blueprint while removing its
demonstration platforms.

```text
custom_components/eem_online/
├── __init__.py
├── api/
│   └── client.py
├── config_flow.py
├── config_flow_handler/
│   ├── config_flow.py
│   ├── schemas/config.py
│   └── validators/credentials.py
├── coordinator/
│   ├── base.py
│   └── statistics.py
├── entity/base.py
├── sensor/
│   ├── __init__.py
│   └── entity.py
├── const.py
├── data.py
├── diagnostics.py
├── icons.json
└── manifest.json
```

```text
config entry
    │
    ▼
API client ── login/token + weekly summary + paginated meter readings
    │
    ▼
one coordinator ── normalize both sources, schedule every 12 hours
    ├──► statistics.py ── merge 7-day window, recalculate sums, recorder
    └──► two sensors ── latest daily use and meter reading with date attributes
```

The client only performs HTTP and translates protocol failures. The coordinator owns
normalization, scheduling, and Home Assistant error mapping. `statistics.py` owns the
recorder-specific merge and import. Entities only read the coordinator payload.

The two HTTP sources fail independently: a meter-reading failure does not stop a valid
Energy import, and a summary failure does not hide a valid meter reading. Both entity
values are read from the same coordinator payload and use source-specific availability.

The config entry holds a no-op coordinator listener so polling and statistics imports
continue when both sensors are disabled. The listener is released automatically
when the entry unloads.
