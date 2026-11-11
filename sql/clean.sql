DROP TABLE IF EXISTS clean_sales;

CREATE TABLE clean_sales AS
SELECT s.*, ROUND(s.price / s.surface) AS price_m2
FROM sales AS s
JOIN (
    SELECT year, sale_date, price, insee_code
    FROM sales
    GROUP BY year, sale_date, price, insee_code
    HAVING COUNT(*) = 1
) AS single
USING (year, sale_date, price, insee_code)
WHERE s.surface >= 9
  AND s.price / s.surface BETWEEN 500 AND 25000;

SELECT COUNT(*) FROM clean_sales;