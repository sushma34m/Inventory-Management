
import sqlite3
from pathlib import Path

# Database file will be created inside the backend folder
BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "inventory.db"


def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database():
    """Create the database tables if they do not exist."""

    with get_connection() as connection:

        connection.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id TEXT UNIQUE NOT NULL,
                product_name TEXT NOT NULL,
                branch TEXT NOT NULL,
                quantity INTEGER NOT NULL CHECK (quantity >= 0),
                days_left INTEGER NOT NULL,
                unit_cost REAL NOT NULL CHECK (unit_cost >= 0),
                selling_price REAL NOT NULL CHECK (selling_price >= 0)
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_name TEXT NOT NULL,
                branch TEXT NOT NULL,
                sale_date TEXT NOT NULL,
                units_sold INTEGER NOT NULL CHECK (units_sold >= 0)
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS transfer_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id TEXT NOT NULL,
                source_branch TEXT NOT NULL,
                destination_branch TEXT NOT NULL,
                quantity INTEGER NOT NULL CHECK (quantity > 0),
                transport_cost REAL NOT NULL DEFAULT 0
                    CHECK (transport_cost >= 0),
                status TEXT NOT NULL DEFAULT 'Pending'
                    CHECK (status IN ('Pending', 'Approved', 'Rejected')),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)


def add_inventory_item(
    batch_id, product_name, branch, quantity,
    days_left, unit_cost, selling_price
):
    with get_connection() as connection:
        connection.execute("""
            INSERT INTO inventory (
                batch_id, product_name, branch, quantity,
                days_left, unit_cost, selling_price
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            batch_id, product_name, branch, quantity,
            days_left, unit_cost, selling_price
        ))


def get_all_inventory():
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM inventory ORDER BY id DESC"
        ).fetchall()
        return [dict(row) for row in rows]


def get_inventory_by_branch(branch):
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM inventory WHERE branch = ? ORDER BY id DESC",
            (branch,)
        ).fetchall()
        return [dict(row) for row in rows]


def add_sales_record(product_name, branch, sale_date, units_sold):
    with get_connection() as connection:
        connection.execute("""
            INSERT INTO sales (product_name, branch, sale_date, units_sold)
            VALUES (?, ?, ?, ?)
        """, (product_name, branch, sale_date, units_sold))


def get_all_sales():
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM sales ORDER BY sale_date DESC"
        ).fetchall()
        return [dict(row) for row in rows]


def create_transfer_request(
    batch_id, source_branch, destination_branch,
    quantity, transport_cost
):
    with get_connection() as connection:
        connection.execute("""
            INSERT INTO transfer_requests (
                batch_id, source_branch, destination_branch,
                quantity, transport_cost
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            batch_id, source_branch, destination_branch,
            quantity, transport_cost
        ))


def get_all_transfer_requests():
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM transfer_requests ORDER BY id DESC"
        ).fetchall()
        return [dict(row) for row in rows]


if __name__ == "__main__":
    initialize_database()
    print("Database initialized successfully!")
    print(f"Database location: {DATABASE_PATH}")
