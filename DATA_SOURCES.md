
# Data Sources

This project's code is MIT licensed (see LICENSE). No data is stored in this repo;
loader scripts download public records directly from the sources below.

| Data                           | Source                                                                           | Loader                         |
| ------------------------------ | -------------------------------------------------------------------------------- | ------------------------------ |
| Flood hazard zones             | FEMA National Flood Hazard Layer (NFHL), public domain (U.S. federal government) | `load_flood.py`              |
| Property sales (2025–2026)    | Florida Department of Revenue, Sales Data File (SDF), Duval County (26)          | `load_sales.py`              |
| Parcels, properties, addresses | Duval County Property Appraiser / City of Jacksonville public records            | jax-property-intelligence repo |
| Property use codes             | Florida DOR standard land use codes (first two digits)                           | `home_types.py`              |

## Disclaimer

This is a portfolio and research project, not an official source.
Flood zones are not an official FEMA flood determination, values are not appraisals,
and data may be out of date. Verify with the original agencies before making
financial, insurance, or legal decisions.
