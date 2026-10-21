import csv, io, zipfile, requests, psycopg
from server import DSN

URL = (
    "https://floridarevenue.com/property/dataportal/Documents/PTO%20Data%20Portal/"
    "Tax%20Roll%20Data%20Files/SDF/2026F/Duval%2026%20Final%20SDF%202026.zip"
)

# 1. Download and unzip (in memory, no files left behind)
r = requests.get(URL, timeout=120)
r.raise_for_status()
z = zipfile.ZipFile(io.BytesIO(r.content))
name = [n for n in z.namelist() if n.lower().endswith(".csv")][0]
rows = list(csv.reader(io.TextIOWrapper(z.open(name), encoding="latin-1")))
header, data = [h.strip().lower() for h in rows[0]], rows[1:]
print(f"Downloaded {name}: {len(data):,} sales, {len(header)} columns")

with psycopg.connect(DSN) as c:
    # 2. Raw table: every column as text, untouched
    c.execute("DROP TABLE IF EXISTS sales_raw CASCADE")
    c.execute(
        "CREATE TABLE sales_raw (" + ", ".join(f'"{h}" text' for h in header) + ")"
    )
    with c.cursor().copy(
        f"COPY sales_raw ({', '.join(chr(34) + h + chr(34) for h in header)}) FROM STDIN"
    ) as cp:
        for row in data:
            cp.write_row([v.strip() or None for v in row])

    # 3. Clean table: typed columns, one row per sale
    c.execute("DROP TABLE IF EXISTS sales")
    c.execute("""
        CREATE TABLE sales AS
        SELECT parcel_id AS strap,
               make_date(sale_yr::int, sale_mo::int, 1) AS sale_month,
               sale_prc::bigint AS price,
               qual_cd,
               qual_cd IN ('01','02','03') AS qualified,
               vi_cd, or_book, or_page, multi_par_sal
        FROM sales_raw
        WHERE sale_yr ~ '^\\d+$' AND sale_mo ~ '^\\d+$' AND sale_prc ~ '^\\d+$'
    """)
    c.execute("CREATE INDEX ON sales (strap)")

    # 4. QC report: prove nothing was silently lost
    q = lambda s: c.execute(s).fetchone()[0]
    raw, clean = q("SELECT count(*) FROM sales_raw"), q("SELECT count(*) FROM sales")
    print(f"Source rows:  {len(data):,}")
    print(f"Raw loaded:   {raw:,}")
    print(f"Clean loaded: {clean:,}  (dropped {raw - clean:,} with bad date/price)")
    print(f"Qualified:    {q('SELECT count(*) FROM sales WHERE qualified'):,}")
    print(
        f"Match a parcel: {q('SELECT count(*) FROM sales s WHERE EXISTS (SELECT 1 FROM parcels p WHERE p.strap = s.strap)'):,}"
    )
    print(
        f"Median qualified price: ${q('SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY price) FROM sales WHERE qualified'):,.0f}"
    )
    assert raw == len(data), "Raw row count doesn't match the source!"
