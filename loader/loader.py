import os
import psycopg
import csv

def clean_price(text):
    return text.replace(",", ".")

def clean_date(text):
    day, month, year = text.split("/")
    return year + "-" + month + "-" + day

def make_insee(department, commune):
    if len(department) == 3:
        return department + commune.zfill(2)
    return department.zfill(2) + commune.zfill(3)

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

for year in years:
    file_path = f"/data/ValeursFoncieres-{year}.txt"
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
    print(year, ": rows inserted:", count)

connection.close()