import os
import psycopg

connection= psycopg.connect(
    host="db",
    port=5432,
    dbname=os.environ["POSTGRES_DB"],
    user=os.environ["POSTGRES_USER"],
    password=os.environ["POSTGRES_PASSWORD"],
)

print('connected to base')

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

connection.close()