from database.mysqlconnection import get_connection

def get_databases():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("SHOW DATABASES")

    databases = cursor.fetchall()

    conn.close()

    system_dbs = [
        "information_schema",
        "mysql",
        "performance_schema",
        "sys",
        "replication_tool"
    ]

    filtered_databases = [
        db
        for db in databases
        if db[0] not in system_dbs
    ]

    return filtered_databases


def get_tables(database_name):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(f"USE {database_name}")

    cursor.execute("SHOW TABLES")

    tables = cursor.fetchall()

    conn.close()

    return tables