from database.mysqlconnection import get_connection

def preview_table(database_name, table_name):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(f"USE {database_name}")

    cursor.execute(
        f"SELECT * FROM {table_name} LIMIT 20"
    )

    rows = cursor.fetchall()

    columns = cursor.column_names

    conn.close()

    return columns, rows