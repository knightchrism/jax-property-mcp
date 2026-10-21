# Known data-quality exceptions

## Sales without matching address records

Status: Open. Warning severity; does not block the build.

### Observed baseline

The investigated build contained 6 unmatched sales out of 75,878 sales (approximately 0.008%), across these 4 property IDs:

- `0029380050R`
- `0038380005R`
- `0195850130R`
- `0195850120R`

All six sales have a price of $100 and `qualified = false`. The `nominal_price` flag is derived from `price < 1000`; it is not an independent source classification.

### Investigation

Exact matches against `raw.property_addresses` returned no records for the four IDs. Matching with `upper(trim(strap))` also returned no records, ruling out ordinary leading/trailing spaces and capitalization differences. The inspected address staging model does not filter out or transform these IDs.

The cause remains unconfirmed. Source extraction dates, parcel changes, and address-source coverage require investigation. Missing addresses do not establish that the sales are invalid.

### Handling and impact

- Preserve the sales records.
- Keep the sales-to-address relationship test at `severity: warn` in `models/stg_sales.yml`.
- Use left joins for address enrichment so unmatched sales remain visible with missing address fields.
- These records cannot currently be assigned addresses or mapped using this address dataset alone.
- Apply explicit business eligibility rules for market analysis; do not silently delete unmatched records.

### Follow-up and monitoring

Compare source extraction dates and investigate the four IDs in an authoritative parcel/property source. Review unmatched records on future builds. Six unmatched sales is the observed baseline, not an approved tolerance or a permanent whitelist.
