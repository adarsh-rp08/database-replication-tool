from modules.sync_engine import replicate_database
from modules.preview_engine import preview_table
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    session
)
from database.mysqlconnection import get_connection
from modules.object_browser import get_tables, get_databases
app = Flask(__name__)
app.secret_key = "replicationtool"
@app.route("/", methods=["GET","POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *
            FROM users
            WHERE username=%s
            AND password_hash=%s
            """,
            (
                username,
                password
            )
        )

        user = cursor.fetchone()

        conn.close()

        if user:
            session["username"] = user[1]
            session["role"] = user[3]
            return redirect("/dashboard")

        else:

            return render_template(
                "login.html",
                error="Invalid Username or Password"
            )

    return render_template(
        "login.html",
        error=None
    )


@app.route("/dashboard")
def dashboard():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("SHOW DATABASES")

    databases = cursor.fetchall()

    system_dbs = [
        "information_schema",
        "mysql",
        "performance_schema",
        "sys",
        "replication_tool"
    ]

    connection_count = len(
        [
            db[0]
            for db in databases
            if db[0] not in system_dbs
        ]
    )

    cursor.execute(
        "SELECT COUNT(*) FROM sync_jobs"
    )
    sync_count = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM audit_logs"
    )
    log_count = cursor.fetchone()[0]

    conn.close()

    return render_template(
        "dashboard.html",
        connection_count=connection_count,
        sync_count=sync_count,
        log_count=log_count
    )

@app.route("/settings")
def settings():

    if session.get("role") != "ADMIN":
        return "Access Denied"

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM system_settings"
    )

    settings = cursor.fetchall()

    conn.close()

    return render_template(
        "settings.html",
        settings=settings
    )

@app.route("/logs")
def logs():

    if session.get("role") != "ADMIN":
        return "Access Denied"

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM audit_logs"
    )

    logs = cursor.fetchall()

    conn.close()

    return render_template(
        "logs.html",
        logs=logs
    )

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")

@app.route("/sync-history")
def sync_history():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM sync_jobs
        ORDER BY job_id DESC
        """
    )

    jobs = cursor.fetchall()

    conn.close()

    return render_template(
        "sync_history.html",
        jobs=jobs
    )
@app.route("/explorer", methods=["GET","POST"])
def explorer():

    connections = get_databases()

    tables = []

    preview_rows = []
    preview_columns = []

    selected_database = None

    if request.method == "POST":

        selected_database = request.form["database"]

        tables = get_tables(
            selected_database
        )

        if "preview" in request.form:

            selected_table = request.form[
                "selected_table"
            ]

            preview_columns, preview_rows = preview_table(
                selected_database,
                selected_table
            )

    return render_template(
        "explorer.html",
        connections=connections,
        tables=tables,
        preview_rows=preview_rows,
        preview_columns=preview_columns,
        selected_database=selected_database
    )
    
@app.route("/replication", methods=["GET", "POST"])
def replication():

    if session.get("role") != "ADMIN":
        return "Access Denied"

    connections = get_databases()

    tables = []

    preview_rows = []
    preview_columns = []

    sync_results = []

    selected_source = None
    selected_destination = None

    conn = get_connection()
    cursor = conn.cursor()

    if request.method == "POST":

        selected_source = request.form["source_db"]
        selected_destination = request.form["destination_db"]

        source_database = selected_source
        destination_database = selected_destination

        tables = get_tables(source_database)

        if not tables:
            sync_results.append(
                "No objects found in source database."
            )

        if "preview" in request.form:

            if tables:

                selected_table = request.form["selected_table"]

                preview_columns, preview_rows = preview_table(
                    source_database,
                    selected_table
                )

                if not preview_rows:

                    sync_results.append(
                        "No records found in selected table."
                    )

        elif "replicate" in request.form:

            if source_database == destination_database:

                sync_results.append(
                    "Source and Destination databases cannot be the same."
                )

            else:

                sync_data = replicate_database(
                    "localhost",
                    "root",
                    "root",
                    source_database,
                    destination_database
                )

                sync_results = sync_data["results"]

                cursor.execute(
                    """
                    INSERT INTO sync_jobs
                    (
                        frequency,
                        last_run,
                        status,
                        source_database,
                        destination_database,
                        objects_synced,
                        rows_inserted,
                        rows_updated
                    )
                    VALUES
                    (
                        'MANUAL',
                        NOW(),
                        'SUCCESS',
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )
                    """,
                    (
                        source_database,
                        destination_database,
                        sync_data["objects_synced"],
                        sync_data["rows_inserted"],
                        sync_data["rows_updated"]
                    )
                )

                cursor.execute(
                    """
                    INSERT INTO audit_logs
                    (
                        username,
                        activity,
                        status
                    )
                    VALUES
                    (
                        'admin',
                        %s,
                        'SUCCESS'
                    )
                    """,
                    (
                        f"Replicated {source_database} to {destination_database}",
                    )
                )

                conn.commit()

                sync_results.append(
                    f"Total Inserted: {sync_data['rows_inserted']}"
                )

                sync_results.append(
                    f"Total Updated: {sync_data['rows_updated']}"
                )

    conn.close()

    return render_template(
        "replication.html",
        connections=connections,
        tables=tables,
        preview_rows=preview_rows,
        preview_columns=preview_columns,
        sync_results=sync_results,
        selected_source=selected_source,
        selected_destination=selected_destination
    )
if __name__ == "__main__":
    app.run(debug=True)