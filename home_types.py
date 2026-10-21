import psycopg
from server import DSN

# Florida DOR standard land use codes (first 2 digits)
TYPES = {
    "00": ("Vacant Residential", "Vacant"),
    "01": ("Single Family", "Residential"),
    "02": ("Mobile Home", "Residential"),
    "03": ("Multifamily 10+ Units", "Residential"),
    "04": ("Condominium", "Residential"),
    "05": ("Co-op", "Residential"),
    "06": ("Retirement Home", "Residential"),
    "07": ("Misc Residential", "Residential"),
    "08": ("Multifamily 2-9 Units", "Residential"),
    "09": ("Residential Common Area", "Residential"),
    "10": ("Vacant Commercial", "Vacant"),
    "11": ("Store", "Commercial"),
    "12": ("Mixed Use Store/Office", "Commercial"),
    "16": ("Shopping Center", "Commercial"),
    "17": ("Office, 1 Story", "Commercial"),
    "18": ("Office, Multi-Story", "Commercial"),
    "19": ("Professional Building", "Commercial"),
    "21": ("Restaurant", "Commercial"),
    "27": ("Auto Sales/Service", "Commercial"),
    "28": ("Parking Lot/Mobile Home Park", "Commercial"),
    "39": ("Hotel/Motel", "Commercial"),
    "40": ("Vacant Industrial", "Vacant"),
    "41": ("Light Manufacturing", "Industrial"),
    "48": ("Warehouse/Distribution", "Industrial"),
    "49": ("Open Storage", "Industrial"),
    "56": ("Timberland", "Agricultural"),
    "70": ("Vacant Institutional", "Vacant"),
    "71": ("Church", "Institutional"),
    "72": ("Private School", "Institutional"),
    "80": ("Vacant Government", "Vacant"),
    "83": ("Public School", "Government"),
    "86": ("County Owned", "Government"),
    "94": ("Right-of-Way", "Other"),
    "95": ("Submerged Land", "Other"),
    "96": ("Waste Land/Drainage", "Other"),
}

TYPES.update(
    {
        "13": ("Department Store", "Commercial"),
        "14": ("Supermarket", "Commercial"),
        "15": ("Regional Shopping Center", "Commercial"),
        "20": ("Airport/Marina", "Commercial"),
        "22": ("Drive-In Restaurant", "Commercial"),
        "23": ("Bank", "Commercial"),
        "25": ("Repair Service Shop", "Commercial"),
        "26": ("Service Station", "Commercial"),
        "30": ("Florist/Greenhouse", "Commercial"),
        "31": ("Drive-In Theater", "Commercial"),
        "32": ("Theater/Auditorium", "Commercial"),
        "33": ("Nightclub/Bar", "Commercial"),
        "34": ("Bowling/Arena", "Commercial"),
        "35": ("Tourist Attraction", "Commercial"),
        "36": ("Camp", "Commercial"),
        "37": ("Race Track", "Commercial"),
        "38": ("Golf Course", "Commercial"),
        "42": ("Heavy Industrial", "Industrial"),
        "43": ("Lumber Yard", "Industrial"),
        "45": ("Cannery/Brewery", "Industrial"),
        "46": ("Food Processing", "Industrial"),
        "47": ("Mineral Processing", "Industrial"),
        "51": ("Cropland", "Agricultural"),
        "52": ("Cropland", "Agricultural"),
        "53": ("Cropland", "Agricultural"),
        "54": ("Timberland", "Agricultural"),
        "55": ("Timberland", "Agricultural"),
        "57": ("Timberland", "Agricultural"),
        "59": ("Timberland", "Agricultural"),
        "61": ("Grazing Land", "Agricultural"),
        "63": ("Grazing Land", "Agricultural"),
        "66": ("Orchard/Groves", "Agricultural"),
        "67": ("Poultry/Fish Farm", "Agricultural"),
        "69": ("Ornamentals/Misc Ag", "Agricultural"),
        "73": ("Private Hospital", "Institutional"),
        "74": ("Home for the Aged", "Institutional"),
        "75": ("Nonprofit/Orphanage", "Institutional"),
        "76": ("Mortuary/Cemetery", "Institutional"),
        "77": ("Club/Lodge", "Institutional"),
        "78": ("Sanitarium", "Institutional"),
        "79": ("Cultural Organization", "Institutional"),
        "81": ("Military", "Government"),
        "82": ("Forest/Park/Recreation", "Government"),
        "84": ("College", "Government"),
        "85": ("Public Hospital", "Government"),
        "87": ("State Owned", "Government"),
        "88": ("Federal Owned", "Government"),
        "89": ("Municipal Owned", "Government"),
        "90": ("Leasehold Interest", "Other"),
        "91": ("Utility", "Other"),
        "93": ("Subsurface Rights", "Other"),
        "97": ("Outdoor Recreation", "Other"),
        "98": ("Centrally Assessed", "Other"),
        "99": ("Acreage, Non-Agricultural", "Other"),
    }
)

with psycopg.connect(DSN) as c:
    c.execute("DROP TABLE IF EXISTS property_use_types")
    c.execute(
        "CREATE TABLE property_use_types (prefix char(2) PRIMARY KEY, home_type text, category text)"
    )
    with c.cursor().copy("COPY property_use_types FROM STDIN") as cp:
        for k, (t, cat) in TYPES.items():
            cp.write_row([k, t, cat])

    q = lambda s: c.execute(s).fetchall()
    unmatched = q("""SELECT left(property_use_code, 2), count(*) FROM properties p
                     WHERE NOT EXISTS (SELECT 1 FROM property_use_types t WHERE t.prefix = left(p.property_use_code, 2))
                     GROUP BY 1 ORDER BY 2 DESC""")
    print("Unmatched prefixes:", unmatched)
    for r in q("""SELECT t.category, t.home_type, count(*) FROM properties p
                  JOIN property_use_types t ON t.prefix = left(p.property_use_code, 2)
                  GROUP BY 1, 2 ORDER BY 3 DESC LIMIT 15"""):
        print(r)
