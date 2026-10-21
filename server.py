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
    zip_code: str, min_value: float = 0, max_value: float = 1e12, limit: int = 10
) -> list[dict]:
    """Find Jacksonville properties in a ZIP code (e.g. '32207') within a just-value range in dollars."""
    return run(
        """
        SELECT p.strap, a.site_number || ' ' || a.site_street || ' ' || coalesce(a.site_type,'') AS address,
               a.site_zip, p.total_just_value, p.property_use_code, p.documented_acres
        FROM properties p JOIN (SELECT DISTINCT ON (strap) * FROM property_addresses ORDER BY strap, address_id) a USING (strap)
        WHERE a.site_zip LIKE %s AND p.total_just_value BETWEEN %s AND %s
        ORDER BY p.total_just_value DESC LIMIT %s""",
        (zip_code + "%", min_value, max_value, min(limit, 50)),
    )


@mcp.tool()
def property_details(strap: str) -> list[dict]:
    """Full assessor details for one property by its strap (parcel ID from search_properties)."""
    return run("SELECT * FROM properties WHERE strap = %s", (strap,))


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


if __name__ == "__main__":
    mcp.run()
