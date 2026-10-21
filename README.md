# Jax Property MCP

An MCP server and AI agent for Jacksonville (Duval County) property data, from 405k assessor records in PostGIS.

## Tools
- `search_properties`: properties in a ZIP within a value range
- `property_details`: full assessor record for one parcel
- `zip_stats`: count, median, average and max value for a ZIP

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
