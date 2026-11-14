# France Housing Prices
In which French cities has the price per m² risen the most between 2022 and 2025?

## Author
Nicolas Grimaldi, individual project (non-attending student)

## How to run
1. Install Docker Desktop
2. Get the code by doing: `git clone https://github.com/Nicolasgrimaldi2011/france-housing-prices.git`
3. Go into the folder by doing: `cd france-housing-prices`
4. Create the .env file by using the .env example from Github:
    - if you are on Windows it's: `copy .env.example .env`
    - if you are on Mac or Linux it's: `cp .env.example .env`
5. Run: `docker compose up`
    - This is to start the whole system (Docker Desktop must be running)
    - The command creates the images and starts the three containers in the right order
    - The first start downloads the 4 DVF files from data.gouv.fr (about 300 MB) and loads them into the database. It takes about 5 to 7 minutes.
6. Once the containers are running, open your web browser and go to http://localhost:8501 to see the dashboard. 

## Data
**Source:** "Demandes de valeurs foncières" (DVF), published by the French tax administration (DGFiP) on the official French open data portal data.gouv.fr: https://www.data.gouv.fr/datasets/demandes-de-valeurs-foncieres/
(last update used: October 2026)

**Content:** It lists all the property sales in France. Each row is one part of a sale (for example a flat, or the cellar sold with it), with the date, the price, the town, the type of property and the surface. I use 4 years, from 2022 to 2025. There is one zip file per year, around 60-85 MB each (about 450-600 MB each once unzipped). In total, there are almost 16 million rows.

**Licence:** The data is under the Licence Ouverte 2.0: it can be used, modified and shared freely, as long as the source and the date of the last update are mentioned. Because the sales could be linked to real people, it is forbidden to try to identify them. This project only shows results per town (median prices), never single sales.

**Format:** text files separated by `|`. Prices use a comma as decimal separator (`468000,00`) and dates are written `DD/MM/YYYY`.

**Download:** the data files are not in this repository. The loader downloads them automatically from the stable URLs of data.gouv.fr when it starts, unzips them into the `data/` folder, and skips this step if the files are already there.

## Processing
After loading, the loader runs `sql/clean.sql` and keeps only clean sales in a new table, `clean_sales`:
- sales of a single dwelling (when several flats are sold together, each row shows the total price),
- a price per m² between 500 and 25,000 € (to remove symbolic sales like 1 €),
- a surface of at least 9 m².

This keeps 2,959,106 sales out of 4,607,751. The analysis queries are in `sql/queries.sql`.

## Dashboard
Once everything is loaded, the dashboard opens at http://localhost:8501. It shows:
- the median price per m² in France for each year, with a chart,
- the 20 cities where the price per m² rose the most between 2022 and 2025, and the 20 where it fell the most (only cities with at least 100 sales in both years),
- a search box to choose one city and see its median price per m² year by year.

## Architecture
![Architecture](docs/FranceHousingProjectArchitectureGRIMALDI.drawio.png)
- **db**: PostgreSQL database, stores the sales
- **loader**: downloads the DVF files, cleans them and puts them in the database, then stops
- **app**: Streamlit dashboard, reads the database and shows the results

**Why PostgreSQL:** every DVF sale has the same columns (date, price, town, type of property, surface), so the data fits well in a SQL table with a fixed structure. The main questions of the project are groupings and averages, such as the median price per m² by town and by year, which SQL does very well. PostgreSQL also runs as its own container, so the loader and the dashboard can both connect to the same database over the Docker network.

## Measurements

Measured with `measure/benchmark.py`, the loader output and `docker stats`.
Laptop: Intel i5-1335U, 16 GB RAM (7.6 GB available to Docker), plugged in, other programs closed.
Load and cleaning times: average of 3 runs. Memory: peak seen in one run with `docker stats`.
To run the benchmark: set `YEARS` in `.env` (e.g. `YEARS=2025` for 25%), run `docker compose down -v` and `docker compose up`, then `docker compose run --rm --no-deps loader python /measure/benchmark.py`.

| | 25% (2025) | 50% (2024-2025) | 100% (2022-2025) |
|---|---|---|---|
| Rows in `sales` | 1,130,632 | 2,121,699 | 4,607,751 |
| Rows in `clean_sales` | 731,396 | 1,368,462 | 2,959,106 |
| **Time**: load | 52.2 s | 94.9 s | 247.3 s |
| **Time**: create `clean_sales` | 3.3 s | 6.8 s | 20.7 s |
| **Disk**: original text files | 507 MB | 975 MB | 2,114 MB |
| **Disk**: database | 178 MB | 327 MB | 697 MB |
| **Memory**: `db` (peak) | 207 MiB | 348 MiB | 711 MiB |
| **Memory**: `loader` (peak) | 25 MiB | 24 MiB | 24 MiB |

One-city query (Marseille 1er), average of 3 runs:

| | 25% | 50% | 100% |
|---|---|---|---|
| Without index | 31.7 ms | 39.3 ms | 74.7 ms |
| With index on `insee_code` | 1.1 ms | 1.2 ms | 4.0 ms |
| Speed-up | x28 | x32 | x19 |

What I learned:
- Load time and disk grow about linearly with the data.
- Creating `clean_sales` grows faster than the data (x2, then x3), probably because the duplicate check has to sort all rows.
- The loader memory stays the same at every size, because it streams the file row by row with `COPY`.
- The database is about 3 times smaller than the text files: only houses and flats, and only 9 columns.
- The index makes the dashboard query 19 to 32 times faster.

## What went wrong

**1. Downloading costs more disk time than network time.**
A first run with download took 282.5 s instead of about 195 s. At 85 Mbps, downloading the 295 MB of zip files takes only about 28 s; the rest is unzipping, which writes about 2 GB of text to the disk.
Lesson: the bottleneck here is the disk, not the network.

**2. Ctrl+C stops every service, including the database.**
Ctrl+C on `docker compose up` stops all containers. `docker compose run --no-deps` then failed with `Name or service not known`, because `db` was not running.
Fix: `docker compose up -d db` before running the benchmark.

**3. The table grew after each reload.**
Reloading many times with `DELETE` + `COPY` left dead rows: `sales` took 534 MB, but only 392 MB after a fresh start (`down -v`).
Lesson: compare disk sizes on a fresh database.

**4. Noisy measurements.**
My first 50% loads were done with the laptop on battery and busy: the same 2025 file took about 110 s instead of about 50 s.
Fix: all measurements done again with the laptop plugged in and other programs closed, 3 runs each, and the first (cold) benchmark run ignored.

**5. Cleaning does not scale linearly.**
Creating `clean_sales` takes 3.3 s, 6.8 s, then 20.7 s (x2, then x3), probably because the one-dwelling rule needs a `GROUP BY` that sorts all rows.
Lesson: this step would be the first problem with more data.

**6. Full table scan without an index.**
Without an index, the one-city query reads the whole `clean_sales` table (74.7 ms at 100%).
Fix: an index on `insee_code`, which makes it 19 to 32 times faster.