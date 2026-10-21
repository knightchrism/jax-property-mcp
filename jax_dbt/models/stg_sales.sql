{{ config(materialized='table') }}

select
    strap,
    sale_month,
    price,
    qual_cd,
    qualified,
    vi_cd,
    or_book,
    or_page,
    multi_par_sal,
    (price < 1000) as nominal_price
from {{ source('raw', 'sales') }}
where strap is not null
