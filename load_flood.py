"""Download FEMA flood zones for Duval County, load them into PostGIS, and check nothing was lost."""
import json
import time
import requests
import psycopg
from server import DSN

URL = "https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer/28/query"
DUVAL_BOX = "-82.05,30.10,-81.39,30.59"   # lon/lat rectangle around Duval County
PAGE = 250                                # small pages: FEMA drops big responses


def fetch(params, tries=3):
    """Try one page a few times. Returns features, or None if FEMA keeps failing."""
    for i in range(tries):
        try:
            return requests.get(URL, params=params, timeout=120).json().get("features", [])
        except (requests.RequestException, ValueError) as e:
            wait = 5 * (i + 1)
            print(f"  page failed ({e.__class__.__name__}), retrying in {wait}s...")
            time.sleep(wait)
    return None

with psycopg.connect(DSN) as c:
    # 1. RAW table: exactly what FEMA sent, untouched (any geometry type allowed)
    c.execute("""
        DROP TABLE IF EXISTS flood_zones_raw;
        CREATE TABLE flood_zones_raw (
            raw_id serial PRIMARY KEY,
            fld_zone text, zone_subty text, sfha_tf text, static_bfe double precision,
            geom geometry(Geometry, 2236)
        );""")

    # 2. Download page by page into RAW
    offset, total, no_geom = 0, 0, 0
    page = PAGE   # current page size; shrinks when FEMA struggles, grows back after
    while True:
        feats = fetch({
            "where": "1=1", "geometry": DUVAL_BOX, "geometryType": "esriGeometryEnvelope",
            "inSR": 4326, "spatialRel": "esriSpatialRelIntersects",
            "outFields": "FLD_ZONE,ZONE_SUBTY,SFHA_TF,STATIC_BFE", "outSR": 2236,
            "resultOffset": offset, "resultRecordCount": page, "orderByFields": "OBJECTID",
            "f": "geojson", "geometryPrecision": 1,
        })
        if feats is None:                      # this page keeps failing
            if page == 1:
                raise RuntimeError(f"FEMA cannot return the single feature at offset {offset}; run again later")
            page = max(1, page // 2)
            print(f"  shrinking page size to {page}")
            continue
        if not feats:
            break
        no_geom += sum(1 for f in feats if not f.get("geometry"))
        with c.cursor() as cur:
            cur.executemany(
                """INSERT INTO flood_zones_raw (fld_zone, zone_subty, sfha_tf, static_bfe, geom)
                   VALUES (%s, %s, %s, %s, ST_SetSRID(ST_GeomFromGeoJSON(%s), 2236))""",
                [(f["properties"]["FLD_ZONE"], f["properties"]["ZONE_SUBTY"], f["properties"]["SFHA_TF"],
                  None if f["properties"]["STATIC_BFE"] in (None, -9999) else f["properties"]["STATIC_BFE"],
                  json.dumps(f["geometry"])) for f in feats if f.get("geometry")])
        total += len(feats)
        offset += len(feats)
        page = min(PAGE, page * 2)            # success: grow back toward full size
        print(f"downloaded {total} flood polygons (page size {page})...")

    expected = None
    for i in range(6):   # the count request gets retries too
        try:
            expected = requests.get(URL, params={"where": "1=1", "geometry": DUVAL_BOX, "geometryType": "esriGeometryEnvelope", "inSR": 4326, "spatialRel": "esriSpatialRelIntersects", "returnCountOnly": "true", "f": "json"}, timeout=60).json()["count"]
            break
        except (requests.RequestException, ValueError, KeyError) as e:
            print(f"  count check failed ({e.__class__.__name__}), retrying in {5 * (i + 1)}s...")
            time.sleep(5 * (i + 1))
    if expected is None:
        raise RuntimeError("Could not get FEMA's feature count to verify the download; run again later")
    print(f"FEMA says {expected} features; downloaded {total}")
    if total != expected:
        raise RuntimeError(f"Incomplete download: {total} of {expected}. Not building clean table.")

    # 3. CLEAN table: repaired copy, linked back to RAW by raw_id
    c.execute("""
        DROP TABLE IF EXISTS flood_zones;
        CREATE TABLE flood_zones AS
        SELECT raw_id, fld_zone, zone_subty, (sfha_tf = 'T') AS sfha, static_bfe,
               ST_IsValid(geom) AS was_valid,
               ST_Multi(ST_CollectionExtract(ST_MakeValid(geom), 3))::geometry(MultiPolygon, 2236) AS geom
        FROM flood_zones_raw;
        CREATE INDEX flood_zones_geom_idx ON flood_zones USING gist (geom);
        CREATE INDEX IF NOT EXISTS parcels_geom_idx ON parcels USING gist (geometry);""")

    # 4. QUALITY CHECKS: compare every clean shape to its raw original
    c.execute("""
        DROP TABLE IF EXISTS flood_zones_qc;
        CREATE TABLE flood_zones_qc AS
        SELECT r.raw_id, r.fld_zone, ST_GeometryType(r.geom) AS raw_type, z.was_valid,
               ST_Area(ST_MakeValid(r.geom)) AS raw_area_sqft, ST_Area(z.geom) AS clean_area_sqft,
               ST_IsEmpty(z.geom) AS became_empty
        FROM flood_zones_raw r JOIN flood_zones z USING (raw_id)
        WHERE NOT z.was_valid OR ST_IsEmpty(z.geom)
           OR abs(ST_Area(ST_MakeValid(r.geom)) - ST_Area(z.geom)) > 1;""")
    q = c.execute("""
        SELECT (SELECT count(*) FROM flood_zones_raw),
               (SELECT count(*) FROM flood_zones),
               (SELECT count(*) FROM flood_zones WHERE NOT was_valid),
               (SELECT count(*) FROM flood_zones WHERE ST_IsEmpty(geom)),
               (SELECT coalesce(sum(raw_area_sqft - clean_area_sqft), 0) FROM flood_zones_qc),
               (SELECT sum(ST_Area(geom)) FROM flood_zones)""").fetchone()
    print("\n=== QUALITY REPORT ===")
    print(f"features from FEMA:      {total}  (missing geometry: {no_geom})")
    print(f"raw rows loaded:         {q[0]}")
    print(f"clean rows:              {q[1]}  (row loss: {q[0] - q[1]})")
    print(f"shapes needing repair:   {q[2]}")
    print(f"shapes that became empty:{q[3]}")
    print(f"area lost in repair:     {q[4]:,.0f} sq ft of {q[5]:,.0f} total ({100 * q[4] / q[5]:.5f}%)")
    print("details: SELECT * FROM flood_zones_qc ORDER BY raw_area_sqft - clean_area_sqft DESC;")
    print("zones:", c.execute("SELECT fld_zone, count(*) FROM flood_zones GROUP BY 1 ORDER BY 2 DESC").fetchall())
