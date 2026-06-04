import pandas as pd
import requests
import sqlite3
from io import StringIO
from datetime import datetime

# Can change according to requirements
TABLE_NAME = "Countries_by_GDP"
conn = sqlite3.connect("World_Economies.db")
LOG_FILE = "etl_project_log.txt"
TARGET_FILE = "Countries_by_GDP.csv"
URL = "https://en.wikipedia.org/wiki/List_of_countries_by_GDP_(nominal)"  # Latest link, prefer archieve to avoid unnecessary crashes


# Connecting and Extracting
def extract(url):
    # headers not required if archive file
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    print(response.status_code)
    print(response.headers["Content-type"])

    # Extracting tables
    tables = pd.read_html(StringIO(response.text))  # converting text to string
    table = tables[2]
    return table  # table is a dataframe itself


# Transform
def transform(table):

    df = table.copy()
    df.columns = range(df.shape[1])  # Converting columns names as index
    df = df[[0, 1]]
    df = df.iloc[1:]  # Removing the first row
    df.columns = ["Country", "GDP(Millions USD)"]

    # Converting to Billions
    print(df["GDP(Millions USD)"].dtype)  # string
    df["GDP(Millions USD)"] = pd.to_numeric(
        df["GDP(Millions USD)"], errors="coerce"
    )  # errors = "coerce" because there are values such as -N/a, so this converts it to NaN
    print(df["GDP(Millions USD)"].dtype)  # now float
    # dropping NaN
    df = df.dropna(subset=["GDP(Millions USD)"])
    df["GDP(Millions USD)"] /= 1000  # converting to Billion

    # rounding off to 2 decimals
    df["GDP(Millions USD)"] = df["GDP(Millions USD)"].round(2)
    df.rename(columns={"GDP(Millions USD)": "GDP_USD_billion"}, inplace=True)

    return df


def loading(df, target_file, conn, table_name):

    # Storing to file and database
    df.to_csv(target_file, index=False)

    df.to_sql(table_name, conn, if_exists="replace", index=False)
    print("table is ready")


# Query
def querying(sql_query, conn):
    # sql_query = f'SELECT * FROM {TABLE_NAME} where "GDP_USD_billion" >=100 '
    query_out = pd.read_sql(sql_query, conn)
    print(query_out)


# logging


def log_progress(message, log_file):
    timestamp_format = "%Y-%m-%d-%H:%M:%S"
    now = datetime.now()  # current date time
    timestamp = now.strftime(timestamp_format)  # Converting to string
    with open(log_file, "a") as f:
        f.write(timestamp + "," + message + "\n")


# Initializing
try:
    log_progress("ETL process initiated", LOG_FILE)

    # Extraction
    log_progress("Starting data extraction from Wikipedia GDP source", LOG_FILE)
    extracted_data = extract(URL)
    log_progress("Data extraction completed successfully", LOG_FILE)

    # Transformation
    log_progress("Starting data transformation", LOG_FILE)
    transformation_data = transform(extracted_data)
    log_progress(
        f"Data transformation completed successfully. {len(transformation_data)} records processed",
        LOG_FILE,
    )

    # Loading
    log_progress("Starting data load to CSV file and SQLite database", LOG_FILE)
    loading(transformation_data, TARGET_FILE, conn, TABLE_NAME)
    log_progress("Data successfully loaded to CSV file and database table", LOG_FILE)

    # Querying
    log_progress(
        "Executing SQL query for countries with GDP >= 100 billion USD",
        LOG_FILE,
    )
    querying(
        f"SELECT * FROM {TABLE_NAME} WHERE GDP_USD_billion >= 100",
        conn,
    )
    log_progress("SQL query executed successfully", LOG_FILE)

except Exception as e:
    print(f"Error: {e}")
    log_progress(f"ETL process failed: {e}", LOG_FILE)

finally:
    conn.close()
    log_progress(
        "Database connection closed. ETL process terminated",
        LOG_FILE,
    )
