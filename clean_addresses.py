import psycopg
from server import DSN

with psycopg.connect(DSN) as c:
    # Clean copy: 5-digit ZIP, one row per unique address
    c.execute("DROP TABLE IF EXISTS addresses_clean")
    c.execute("""
        CREATE TABLE addresses_clean AS
        SELECT DISTINCT ON (strap, site_number, site_prefix, site_street, site_type, site_unit)
               address_id, strap, site_number, site_prefix, site_street, site_type, site_unit,
               site_city, left(site_zip, 5) AS zip5, site_zip AS zip_original
        FROM property_addresses
        ORDER BY strap, site_number, site_prefix, site_street, site_type, site_unit, address_id
    """)
    c.execute("CREATE INDEX ON addresses_clean (strap)")
    c.execute("CREATE INDEX ON addresses_clean (zip5)")

    # QC table: every dropped row, and which kept row it duplicated
    c.execute("DROP TABLE IF EXISTS addresses_qc")
    c.execute("""
        CREATE TABLE addresses_qc AS
        SELECT p.*, k.address_id AS kept_address_id, 'exact duplicate' AS reason
        FROM property_addresses p
        JOIN addresses_clean k USING (strap)
        WHERE p.address_id <> k.address_id
          AND p.site_number IS NOT DISTINCT FROM k.site_number
          AND p.site_prefix IS NOT DISTINCT FROM k.site_prefix
          AND p.site_street IS NOT DISTINCT FROM k.site_street
          AND p.site_type   IS NOT DISTINCT FROM k.site_type
          AND p.site_unit   IS NOT DISTINCT FROM k.site_unit
    """)

    q = lambda s: c.execute(s).fetchone()[0]
    orig, clean, qc = (q("SELECT count(*) FROM property_addresses"),
                       q("SELECT count(*) FROM addresses_clean"),
                       q("SELECT count(*) FROM addresses_qc"))
    print(f"Original rows:   {orig:,}")
    print(f"Clean rows:      {clean:,}")
    print(f"Dropped (in QC): {qc:,}")
    print(f"Accounted for:   {clean + qc == orig}")
    print(f"Distinct ZIP5:   {q('SELECT count(DISTINCT zip5) FROM addresses_clean')}")
    print(f"Bad ZIP5:        {q(chr(39).join(['SELECT count(*) FROM addresses_clean WHERE zip5 !~ ', '^[0-9]{5}$', '']))}")
    print(f"Parcels covered: {q('SELECT count(DISTINCT strap) FROM addresses_clean'):,}")
