import os
import psycopg
import csv
import time
import urllib.request
import zipfile

DOWNLOAD_URLS = {
    2022: "https://www.data.gouv.fr/api/1/datasets/r/330aead3-b527-4c0f-8c9a-a82a9b928816",
    2023: "https://www.data.gouv.fr/api/1/datasets/r/ddbd3eff-2d18-420c-a1d6-37f14a2fcc2c",
    2024: "https://www.data.gouv.fr/api/1/datasets/r/24d0313f-8f07-4514-bf7d-e1d274e61ecc",
    2025: "https://www.data.gouv.fr/api/1/datasets/r/63c368e8-72b9-4f35-8315-80c21fcc575d",
}

def clean_price(text):
    return text.replace(",", ".")

def clean_date(text):
    day, month, year = text.split("/")
    return year + "-" + month + "-" + day

def make_insee(department, commune):
    if len(department) == 3:
        return department + commune.zfill(2)
    return department.zfill(2) + commune.zfill(3)

def get_file(year):
    txt_path = f"/data/ValeursFoncieres-{year}.txt"

    if os.path.exists(txt_path):
        print(year, ": file already in /data")
        return txt_path

    zip_path = f"/data/valeursfoncieres-{year}.zip"
    print(year, ": downloading from data.gouv.fr")
    urllib.request.urlretrieve(DOWNLOAD_URLS[year], zip_path)

    with zipfile.ZipFile(zip_path) as z:
        name_inside = z.namelist()[0]
        z.extractall("/data")

    os.rename(f"/data/{name_inside}", txt_path)
    os.remove(zip_path)
    return txt_path

connection= psycopg.connect(
    host="db",
    port=5432,
    dbname=os.environ["POSTGRES_DB"],
    user=os.environ["POSTGRES_USER"],
    password=os.environ["POSTGRES_PASSWORD"],
)

print('connected to base')

years_text = os.environ["YEARS"]
years = [int(y) for y in years_text.split(",")]
print("Years to load:", years)

connection.execute("""
    CREATE TABLE IF NOT EXISTS sales (
        year          INTEGER,
        sale_date     DATE,
        price         NUMERIC,
        insee_code    TEXT,
        commune       TEXT,
        department    TEXT,
        property_type TEXT,
        surface       INTEGER,
        rooms         INTEGER
    )
""")
connection.commit()
print('table sales is ready')

start_all = time.perf_counter()
for year in years:
    start = time.perf_counter()
    file_path = get_file(year)
    print("Loading", file_path)

    f = open(file_path, encoding="utf-8")
    reader = csv.DictReader(f, delimiter="|")

    connection.execute("DELETE FROM sales WHERE year = %s", (year,))

    cursor = connection.cursor()
    count = 0

    with cursor.copy("COPY sales (year, sale_date, price, insee_code, commune, department, property_type, surface, rooms) FROM STDIN") as copy:
        for row in reader:
            if row["Nature mutation"] != "Vente":
                continue
            if row["Type local"] not in ("Maison", "Appartement"):
                continue
            if row["Valeur fonciere"] == "" or row["Surface reelle bati"] == "":
                continue

            copy.write_row((
                year,
                clean_date(row["Date mutation"]),
                clean_price(row["Valeur fonciere"]),
                make_insee(row["Code departement"], row["Code commune"]),
                row["Commune"],
                row["Code departement"],
                row["Type local"],
                row["Surface reelle bati"],
                row["Nombre pieces principales"] or None,
            ))
            count = count + 1

    connection.commit()
    f.close()
    duration = time.perf_counter() - start
    print(year, ": rows inserted:", count, "in", round(duration, 1), "s")

total = time.perf_counter() - start_all
print("Total load time:", round(total, 1), "s")
connection.close()