import os
import psycopg2
import configparser
import platform

CONNECTION_URLS = {
    "west": "",
    "east": "",
    "central": ""
}

SCHEMA_FILES = {
    "west": "data/schemas/schema_west.sql",
    "east": "data/schemas/schema_east.sql",
    "central": "data/schemas/schema_central.sql"
}


CERTS_COMMANDS_MAC_OR_LINUX = [
    "curl --create-dirs -o $HOME/.postgresql/root.crt https://cockroachlabs.cloud/clusters/0fa9e1ef-c4a6-4fab-9073-947413d38e6b/cert", # west
    "curl --create-dirs -o $HOME/.postgresql/root.crt https://cockroachlabs.cloud/clusters/fa15bf40-4264-454b-a7f8-d067cbd289e9/cert", # central
    "curl --create-dirs -o $HOME/.postgresql/root.crt https://cockroachlabs.cloud/clusters/0b7cee76-dc84-441d-9417-b7274fb36cdc/cert" # east
]

CERTS_COMMANDS_WINDOWS = [
    "mkdir -p $env:appdata\\postgresql\\; Invoke-WebRequest -Uri https://cockroachlabs.cloud/clusters/0fa9e1ef-c4a6-4fab-9073-947413d38e6b/cert -OutFile $env:appdata\\postgresql\\root_west.crt",
    "mkdir -p $env:appdata\\postgresql\\; Invoke-WebRequest -Uri https://cockroachlabs.cloud/clusters/fa15bf40-4264-454b-a7f8-d067cbd289e9/cert -OutFile $env:appdata\\postgresql\\root_central.crt",
    "mkdir -p $env:appdata\\postgresql\\; Invoke-WebRequest -Uri https://cockroachlabs.cloud/clusters/0b7cee76-dc84-441d-9417-b7274fb36cdc/cert -OutFile $env:appdata\\postgresql\\root_east.crt"
]

def getFormattedURL(raw_url, useSecure = True):
    if useSecure:
        return f"{raw_url}?sslmode=verify-full"
    else:
        return f"{raw_url}?sslmode=disable"

def readUrls():
    config = configparser.ConfigParser()
    config.read('database.conf')
    useSecure = config.getint('DEFAULT', 'useSecureMode') == 1
    CONNECTION_URLS["west"] = getFormattedURL(config.get('DEFAULT', 'westURL'), useSecure)
    CONNECTION_URLS["east"] = getFormattedURL(config.get('DEFAULT', 'eastURL'), useSecure)
    CONNECTION_URLS["central"] = getFormattedURL(config.get('DEFAULT', 'centralURL'), useSecure)

def setupDatabase(connection_url, region, sql_file=None):
    """
    Create/connect to the database and run setup SQL.

    If `sql_file` is provided and exists, its contents will be executed.
    The function first attempts to execute the full file as a single statement;
    if that fails (some drivers reject multiple statements), it falls back to
    splitting on `;` and executing statements one-by-one (naive split).

    Note: For complex SQL files (with PL/pgSQL blocks) the naive splitter may
    not be sufficient; in that case prefer running the SQL file with the
    `psql`/cockroach CLI or using a server-side migration tool.
    """

    conn = psycopg2.connect(connection_url)
    cursor = conn.cursor()

    print("Connected to database. Running setup SQL...")

    try:
        if sql_file and os.path.exists(sql_file):
            with open(sql_file, 'r', encoding='utf-8') as fh:
                sql = fh.read()
            print(f"Executing SQL : {sql}")

            # Try executing the whole file at once first (works for many simple SQL files)
            try:
                cursor.execute(sql)
            except Exception as e:
                # Try a smarter SQL splitter (sqlparse) before falling back to naive split
                print("Top-level execute failed, attempting statement-level execution; error:", e)
                # try:
                #     import sqlparse
                #     statements = [s.strip() for s in sqlparse.split(sql) if s.strip()]
                # except Exception:
                #     # Last-resort naive splitter (may break on dollar-quoted functions)
                #     statements = [s.strip() for s in sql.split(';') if s.strip()]

                # for stmt in statements:
                #     if stmt:
                #         try:
                #             cursor.execute(stmt)
                #         except Exception as e2:
                #             print(f"Failed executing statement (skipping): {e2}\nStatement:\n{stmt[:200]}...")
        else:
            # Example setup commands; replace with actual setup logic as needed
            print(f"Unable to read SQL setup file. Please check your system again.")

        conn.commit()
        print(f"Database setup completed for region: {region}")
    finally:
        cursor.close()
        conn.close()

def setup_func():
    readUrls()
    # Optional: look for an SQL file named `schema.sql` in the same folder by default

    for i in CONNECTION_URLS:
        try:
            print(f"Setting up database for region: {i} , URL: {CONNECTION_URLS[i]}, SQL File: {SCHEMA_FILES.get(i)}")
            setupDatabase(CONNECTION_URLS[i], i, sql_file=SCHEMA_FILES.get(i))
        except Exception as e:
            print(f"Error occurred while setting up database for region {i}: {e}")

if __name__ == "__main__":

    #GET Platform WIndows/Mac/Linux 

    current_platform = platform.system()
    if current_platform == "Windows":
        for cmd in CERTS_COMMANDS_WINDOWS:
            os.system(cmd)
    else:
        for cmd in CERTS_COMMANDS_MAC_OR_LINUX:
            os.system(cmd)
            print(cmd)

    #setup_func()
    