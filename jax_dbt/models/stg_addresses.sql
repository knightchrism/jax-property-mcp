{{ config(materialized='table') }}

with deduped as (
    select distinct on (strap, site_number, site_prefix, site_street, site_type, site_unit)
        address_id, strap, site_number, site_prefix, site_street, site_type, site_unit,
        site_zip as zip_original,
        left(site_zip, 5) as zip5_raw
    from {{ source('raw', 'property_addresses') }}
    order by strap, site_number, site_prefix, site_street, site_type, site_unit, address_id
),

street_zip as (
    -- most common ZIP for each street, used only when a ZIP is missing
    select distinct on (site_prefix, site_street, site_type)
        site_prefix, site_street, site_type, zip5_raw as street_zip5
    from deduped
    where zip5_raw is not null and zip5_raw <> ''
    group by site_prefix, site_street, site_type, zip5_raw
    order by site_prefix, site_street, site_type, count(*) desc
)

select
    d.address_id, d.strap, d.site_number, d.site_prefix, d.site_street, d.site_type, d.site_unit,
    d.zip_original,
    coalesce(nullif(d.zip5_raw, ''), s.street_zip5) as zip5,
    (nullif(d.zip5_raw, '') is null) as zip_inferred
from deduped d
left join street_zip s
  on  coalesce(d.site_prefix, '') = coalesce(s.site_prefix, '')
  and coalesce(d.site_street, '') = coalesce(s.site_street, '')
  and coalesce(d.site_type,   '') = coalesce(s.site_type,   '')
