"""Data access style 2: raw cursor execution."""


def fetch_records(conn, table):
    """Execute raw SQL via database cursor."""
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table}")
    rows = cursor.fetchall()
    return rows


def fetch_one_record(conn, query, params):
    """Fetch a single row with parameterized query."""
    cursor = conn.cursor()
    cursor.execute(query, params)
    return cursor.fetchone()
