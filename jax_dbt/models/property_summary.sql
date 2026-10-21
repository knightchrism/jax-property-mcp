{{ config(materialized='table') }}

with addr as (
    select distinct on (strap)
        strap,
        concat_ws(' ', site_number, site_prefix, site_street, site_type, site_unit) as address,
        zip5
    from {{ ref('stg_addresses') }}
    order by strap, address_id
),

last_sale as (
    select distinct on (strap)
        strap, sale_month as last_sale_month, price as last_sale_price
    from {{ ref('stg_sales') }}
    where qualified and not nominal_price
    order by strap, sale_month desc
)

select
    p.strap,
    a.address,
    a.zip5,
    t.home_type,
    t.category,
    p.total_just_value::numeric  as market_value,
    p.assessed_value::numeric    as assessed_value,
    p.documented_acres::numeric  as acres,
    s.last_sale_month,
    s.last_sale_price
from {{ source('raw', 'properties') }} p
left join addr a       on a.strap = p.strap
left join {{ source('raw', 'property_use_types') }} t on t.prefix = left(p.property_use_code, 2)
left join last_sale s  on s.strap = p.strap
