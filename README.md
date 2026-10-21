# Jax Property MCP

An MCP server and AI agent for Jacksonville (Duval County) property data, from 405k assessor records in PostGIS.

## Tools
- `search_properties`: properties in a ZIP within a value range
- `property_details`: full assessor record for one parcel
- `zip_stats`: count, median, average and max value for a ZIP
- `flood_risk(strap)`: FEMA flood zones touching a parcel, whether each one is high-risk (SFHA), and what percent of the lot it covers. Data comes from FEMA's National Flood Hazard Layer, loaded by `load_flood.py` with completeness and geometry-repair checks (12,288 of 12,288 zones loaded, 0 lost).

## Agent
`agent.py` connects to the server over stdio and runs a tool-calling loop with a local model (qwen3:30b on Ollama), at no API cost. The same server also works in VS Code Copilot through `.vscode/mcp.json`.

## Lesson learned
Without `zip_stats`, the agent compared ZIPs by sampling 100 high-end listings and wrongly said 32210 was pricier than 32207. With the right tool, it used medians ($231k vs $184k) and got it right in half the time. Tool design matters more than model choice.

## Run it
```
python -m venv .venv; .venv\Scripts\activate
pip install -r requirements.txt
python agent.py "Rank 32207, 32210 and 32205 by median value"
```
## Data Quality

Every loader keeps the raw data, builds a cleaned table, and logs exactly what changed, so no row is silently lost.

| Dataset | Result |
|---|---|
| FEMA flood zones | 12,288 of 12,288 loaded; 48 invalid shapes repaired with 0 sq ft area lost |
| FL DOR sales | 75,878 of 75,878 loaded; 99.8% matched to a parcel; 28,800 qualified market sales |
| Addresses | 10,552 exact duplicates removed (each traced in `addresses_qc`); ZIPs normalized from 413 values to 37 |
| Home types | 100% of 405k properties mapped to a type via Florida DOR land use codes |

See [DATA_SOURCES.md](DATA_SOURCES.md) for sources, licensing, and disclaimers.

## Data Pipeline (dbt)

![dbt lineage](docs/dbt_lineage.png)

Raw Duval County and Florida DOR data is cleaned in tested dbt staging models (`stg_addresses`, `stg_sales`) and joined into one row per parcel (`property_summary`, 405,722 parcels). 13 data tests run on every `dbt build`. The project lives in `jax_dbt/`.
