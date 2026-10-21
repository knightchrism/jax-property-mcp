import os
import psycopg
from dotenv import load_dotenv
from mcp.server.mcpserver import MCPServer

load_dotenv(r"C:\Users\knigh\OneDrive\SNHU_Classes\jax-property-intelligence\.env")
DSN = (
    f"postgresql://{os.environ['DB_USER']}:{os.environ['DB_PASSWORD']}"
    f"@{os.environ['DB_HOST']}:{os.environ['DB_PORT']}/{os.environ['DB_NAME']}"
)

mcp = MCPServer("jax-property")


def run(sql: str, params: tuple) -> list[dict]:
    with psycopg.connect(DSN) as c:
        cur = c.execute(sql, params)
        cols = [d.name for d in cur.description]
        return [
            dict(zip(cols, (str(v) if v is not None else None for v in r)))
            for r in cur.fetchall()
        ]


@mcp.tool()
def search_properties(
    zip_code: str,
    min_value: int = 0,
    max_value: int = 100_000_000,
    home_type: str = "",
    exclude_high_flood_risk: bool = False,
    limit: int = 20,
) -> list[dict]:
    """Find properties in a ZIP code by assessed value.
    home_type filters by type, e.g. 'Single Family', 'Condominium', 'Mobile Home' (partial match OK).
    exclude_high_flood_risk=True skips parcels touching a FEMA high-risk zone (SFHA)."""
    return run(
        """
        SELECT p.strap,
               concat_ws(' ', a.site_number, a.site_prefix, a.site_street, a.site_type, a.site_unit) AS address,
               a.zip5, t.home_type, p.total_just_value
        FROM properties p
        JOIN (SELECT DISTINCT ON (strap) * FROM addresses_clean ORDER BY strap, address_id) a USING (strap)
        LEFT JOIN property_use_types t ON t.prefix = left(p.property_use_code, 2)
        WHERE a.zip5 = left(%s, 5)
          AND p.total_just_value BETWEEN %s AND %s
          AND (%s = '' OR t.home_type ILIKE '%%' || %s || '%%')
          AND (NOT %s OR NOT EXISTS (
                SELECT 1 FROM parcels pc JOIN flood_zones f ON ST_Intersects(pc.geometry, f.geom)
                WHERE pc.strap = p.strap AND f.sfha = 'True'))
        ORDER BY p.total_just_value DESC
        LIMIT %s""",
        (
            zip_code,
            min_value,
            max_value,
            home_type,
            home_type,
            exclude_high_flood_risk,
            min(limit, 50),
        ),
    )


@mcp.tool()
def property_details(strap: str) -> list[dict]:
    """Full assessor details for one property by its strap (parcel ID from search_properties).

    Returns parcel info and VALUES: assessed_value (taxable), total_just_value (market value).
    This tool has NO sale history. Never describe these values as a sale price.
    For sales, call recent_sales.
    """
    return run("SELECT * FROM properties WHERE strap = %s", (strap,))


@mcp.tool()
def sale_history(strap: str) -> list[dict]:
    """All recorded sales for one property by its strap (parcel ID).

    Use this for 'what did X sell for' or 'last sale' questions.
    Returns an empty list if the property has no recorded sales.
    """
    return run(
        "SELECT sale_month, price, qualified, qual_cd FROM sales "
        "WHERE strap = %s ORDER BY sale_month DESC",
        (strap,),
    )


@mcp.tool()
def zip_stats(zip_code: str) -> list[dict]:
    """Summary statistics (property count, median, average and max just value) for all properties in a Jacksonville ZIP code, e.g. '32207'. Use this to compare areas."""
    return run(
        """
        SELECT count(*) AS properties,
               percentile_cont(0.5) WITHIN GROUP (ORDER BY p.total_just_value) AS median_value,
               avg(p.total_just_value)::bigint AS avg_value,
               max(p.total_just_value) AS max_value
        FROM properties p
        JOIN (SELECT DISTINCT ON (strap) * FROM property_addresses ORDER BY strap, address_id) a USING (strap)
        WHERE a.site_zip LIKE %s""",
        (zip_code + "%",),
    )


@mcp.tool()
def flood_risk(strap: str) -> list[dict]:
    """FEMA flood zones touching a parcel, given its strap (property ID).
    Returns each zone, whether it's a high-risk Special Flood Hazard Area (sfha = 'True'),
    and what percent of the parcel it covers. No rows means the parcel is outside the mapped zones."""
    sql = """
        SELECT f.fld_zone, f.zone_subty, f.sfha, f.static_bfe,
               ROUND((100 * SUM(ST_Area(ST_Intersection(p.geometry, f.geom)))
                     / NULLIF(ST_Area(ST_Union(p.geometry)), 0))::numeric, 1) AS pct_of_parcel
        FROM parcels p
        JOIN flood_zones f ON ST_Intersects(p.geometry, f.geom)
        WHERE p.strap = %s
        GROUP BY f.fld_zone, f.zone_subty, f.sfha, f.static_bfe
        ORDER BY pct_of_parcel DESC
    """
    return run(sql, (strap,))


@mcp.tool()
def recent_sales(
    zip_code: str, qualified_only: bool = True, limit: int = 20
) -> list[dict]:
    """Recent property sales (Jan 2025 onward) in a ZIP code, newest first.
    qualified_only=True keeps only real market (arm's-length) sales and skips $100 family transfers.
    sale_month is the first day of the month the sale happened in."""
    return run(
        """
        SELECT s.strap,
               concat_ws(' ', a.site_number, a.site_prefix, a.site_street, a.site_type, a.site_unit) AS address,
               s.sale_month, s.price, s.qualified
        FROM sales s
        JOIN (SELECT DISTINCT ON (strap) * FROM property_addresses ORDER BY strap, address_id) a USING (strap)
        WHERE a.site_zip LIKE %s AND (s.qualified OR NOT %s)
        ORDER BY s.sale_month DESC, s.price DESC
        LIMIT %s""",
        (zip_code + "%", qualified_only, min(limit, 50)),
    )


if __name__ == "__main__":
    mcp.run()
