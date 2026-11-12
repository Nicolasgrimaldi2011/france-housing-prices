import os
import pandas as pd
import streamlit as st
import psycopg
import altair as alt


# Connection to the database: code from the slide "How services talk".
# st.cache_resource opens it once, instead of at every click on the page.
@st.cache_resource
def get_connection():
    return psycopg.connect(
        host="db",
        port=5432,
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )


# Run a SQL query and return the result as a table (DataFrame).
# st.cache_data keeps the result, so the same query is not computed again.
@st.cache_data
def run_query(sql, params=None):
    cursor = get_connection().execute(sql, params)
    rows = cursor.fetchall()
    columns = [col.name for col in cursor.description]
    return pd.DataFrame(rows, columns=columns)


# Line chart of the median price per m², one point per year, with the values written on it.
def price_chart(df):
    base = alt.Chart(df).encode(
        x=alt.X("year:O", title="Year", axis=alt.Axis(labelAngle=0)),
        y=alt.Y("median_m2:Q", title="Median price (€/m²)", scale=alt.Scale(zero=False)),
    )
    line = base.mark_line(point=True)
    labels = base.mark_text(dy=-12).encode(text="median_m2:Q")
    return (line + labels).properties(height=300)


YEARS_QUERY = """
    SELECT year,
           COUNT(*) AS sales,
           ROUND(percentile_cont(0.5) WITHIN GROUP (ORDER BY price_m2)) AS median_m2
    FROM clean_sales
    GROUP BY year
    ORDER BY year
"""

CITY_QUERY = """
    WITH city AS (
        SELECT insee_code,
               MAX(commune) AS commune,
               COUNT(*) FILTER (WHERE year = 2022) AS sales_2022,
               COUNT(*) FILTER (WHERE year = 2025) AS sales_2025,
               percentile_cont(0.5) WITHIN GROUP (ORDER BY price_m2) FILTER (WHERE year = 2022) AS median_2022,
               percentile_cont(0.5) WITHIN GROUP (ORDER BY price_m2) FILTER (WHERE year = 2025) AS median_2025
        FROM clean_sales
        GROUP BY insee_code
    )
    SELECT commune, insee_code, sales_2022, sales_2025,
           ROUND(median_2022) AS median_2022,
           ROUND(median_2025) AS median_2025,
           ROUND((median_2025 / median_2022 - 1) * 100) AS change_pct
    FROM city
    WHERE sales_2022 >= 100 AND sales_2025 >= 100
"""

ONE_CITY_QUERY = """
    SELECT year,
           COUNT(*) AS sales,
           ROUND(percentile_cont(0.5) WITHIN GROUP (ORDER BY price_m2)) AS median_m2
    FROM clean_sales
    WHERE insee_code = %s
    GROUP BY year
    ORDER BY year
"""


# ---------- Title ----------
st.title("France Housing Prices")
st.write("In which French cities has the price per m² risen the most between 2022 and 2025?")

# ---------- 1. France, by year ----------
df_years = run_query(YEARS_QUERY)
df_years["year"] = df_years["year"].astype(str)

st.subheader("Median price per m² in France, by year")
st.dataframe(df_years, hide_index=True)
st.altair_chart(price_chart(df_years), use_container_width=True)
st.caption(
    "The vertical axis does not start at 0, to make the change visible. "
    "From 2022 to 2025, the median price changed by about -1.4%."
)

# ---------- 2. The answer: biggest rises and falls ----------
df_cities = run_query(CITY_QUERY)

st.subheader("The 20 cities where the price per m² rose the most (2022 → 2025)")
st.dataframe(df_cities.sort_values("change_pct", ascending=False).head(20), hide_index=True)

st.subheader("The 20 cities where the price per m² fell the most (2022 → 2025)")
st.dataframe(df_cities.sort_values("change_pct").head(20), hide_index=True)

st.caption("Only cities with at least 100 sales in 2022 and in 2025. Median price per m² of houses and flats.")

# ---------- 3. Search one city ----------
st.subheader("Look at one city")

df_choices = df_cities.sort_values("commune")
labels = (df_choices["commune"] + " (" + df_choices["insee_code"] + ")").tolist()
codes = df_choices["insee_code"].tolist()

default = codes.index("31555") if "31555" in codes else 0   # Toulouse
choice = st.selectbox("Choose a city", labels, index=default)
code = codes[labels.index(choice)]

city_row = df_cities[df_cities["insee_code"] == code].iloc[0]
st.metric(
    label="Median price per m² in 2025",
    value=f"{int(city_row['median_2025']):,} €",
    delta=f"{int(city_row['change_pct'])} % since 2022",
)

df_city = run_query(ONE_CITY_QUERY, (code,))
df_city["year"] = df_city["year"].astype(str)
st.dataframe(df_city, hide_index=True)
st.altair_chart(price_chart(df_city), use_container_width=True)