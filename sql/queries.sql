-- Median price per m² in France, by year
SELECT year,
       COUNT(*) AS sales,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY price_m2) AS median_m2
FROM clean_sales
GROUP BY year
ORDER BY year;

-- Top 20 cities where the median price per m² rose the most (2022 -> 2025)
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
SELECT insee_code, commune, sales_2022, sales_2025,
       ROUND(median_2022) AS median_2022,
       ROUND(median_2025) AS median_2025,
       ROUND((median_2025 / median_2022 - 1) * 100) AS change_pct
FROM city
WHERE sales_2022 >= 100 AND sales_2025 >= 100
ORDER BY change_pct DESC
LIMIT 20;

-- Top 20 cities where the median price per m² fell the most (2022 -> 2025)
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
SELECT insee_code, commune, sales_2022, sales_2025,
       ROUND(median_2022) AS median_2022,
       ROUND(median_2025) AS median_2025,
       ROUND((median_2025 / median_2022 - 1) * 100) AS change_pct
FROM city
WHERE sales_2022 >= 100 AND sales_2025 >= 100
ORDER BY change_pct ASC
LIMIT 20;