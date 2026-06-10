import mysql.connector
from datetime import datetime

def replicate_database(
    host,
    user,
    password,
    source_db,
    destination_db
):

    source_conn = mysql.connector.connect(
        host=host,
        user=user,
        password=password,
        database=source_db
    )

    destination_conn = mysql.connector.connect(
        host=host,
        user=user,
        password=password,
        database=destination_db
    )

    source_cursor = source_conn.cursor()
    destination_cursor = destination_conn.cursor()

    source_cursor.execute("SHOW TABLES")

    tables = source_cursor.fetchall()

    if not tables:

        destination_cursor.execute("SHOW TABLES")

        destination_tables = destination_cursor.fetchall()

        dropped = 0

        for table in destination_tables:

            table_name = table[0]

            destination_cursor.execute(
                f"DROP TABLE `{table_name}`"
            )

            dropped += 1

        destination_conn.commit()

        source_conn.close()
        destination_conn.close()

        return {
            "results": [
                f"Source database empty. Removed {dropped} tables from destination."
            ],
            "objects_synced": 0,
            "rows_inserted": 0,
            "rows_updated": 0
        }

    results = []

    total_inserted = 0
    total_updated = 0

    for table in tables:

        table_name = table[0]

        source_cursor.execute(
            f"SHOW CREATE TABLE `{table_name}`"
        )

        create_sql = source_cursor.fetchone()[1]

        create_sql = create_sql.replace(
            f"CREATE TABLE `{table_name}`",
            f"CREATE TABLE IF NOT EXISTS `{table_name}`"
        )

        destination_cursor.execute(create_sql)

        source_cursor.execute(
            f"SELECT * FROM `{table_name}`"
        )

        rows = source_cursor.fetchall()

        if not rows:

            results.append(
                f"{table_name}: no data"
            )

            continue

        columns = [
            column[0]
            for column in source_cursor.description
        ]

        placeholders = ", ".join(
            ["%s"] * len(columns)
        )

        update_clause = ", ".join(
            [
                f"{col}=VALUES({col})"
                for col in columns[1:]
            ]
        )

        insert_sql = f"""
        INSERT INTO `{table_name}`
        ({','.join(columns)})
        VALUES ({placeholders})
        ON DUPLICATE KEY UPDATE
        {update_clause}
        """

        inserted = 0
        updated = 0

        for row in rows:

            destination_cursor.execute(
                insert_sql,
                row
            )

            if destination_cursor.rowcount == 1:
                inserted += 1

            elif destination_cursor.rowcount == 2:
                updated += 1

        destination_conn.commit()

        total_inserted += inserted
        total_updated += updated

        results.append(
            f"{table_name}: Inserted={inserted}, Updated={updated}"
        )

    source_conn.close()
    destination_conn.close()

    return {
        "results": results,
        "objects_synced": len(tables),
        "rows_inserted": total_inserted,
        "rows_updated": total_updated
    }