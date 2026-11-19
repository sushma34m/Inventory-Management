
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "inventory.db"


def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database():
    with get_connection() as connection:

        connection.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id TEXT UNIQUE NOT NULL,
                product_code TEXT,
                product_name TEXT NOT NULL,
                branch TEXT NOT NULL,
                quantity INTEGER NOT NULL CHECK (quantity >= 0),
                days_left INTEGER NOT NULL,
                unit_cost REAL NOT NULL CHECK (unit_cost >= 0),
                selling_price REAL NOT NULL CHECK (selling_price >= 0)
            )
        """)

        inventory_columns = {
            row["name"] for row in connection.execute(
                "PRAGMA table_info(inventory)"
            ).fetchall()
        }

        if "product_code" not in inventory_columns:
            connection.execute(
                "ALTER TABLE inventory ADD COLUMN product_code TEXT"
            )

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

        connection.execute("""
            CREATE TABLE IF NOT EXISTS admin_instructions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id TEXT,
                product TEXT,
                branch TEXT,
                quantity INTEGER,
                action TEXT,
                selling_price REAL,
                destination TEXT,
                instruction TEXT,
                status TEXT DEFAULT 'Pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS recovery_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id TEXT NOT NULL,
                product_name TEXT NOT NULL,
                source_branch TEXT NOT NULL,
                destination_branch TEXT,
                quantity INTEGER NOT NULL,
                action TEXT NOT NULL,
                selling_price REAL,
                expected_recovery REAL DEFAULT 0,
                risk_score REAL DEFAULT 0,
                cvar_10 REAL DEFAULT 0,
                expected_expired_units REAL DEFAULT 0,
                admin_username TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Approved',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decision_id INTEGER NOT NULL,
                batch_id TEXT NOT NULL,
                target_branch TEXT NOT NULL,
                notification_type TEXT NOT NULL,
                message TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Pending'
                    CHECK (
                        status IN (
                            'Pending',
                            'Accepted',
                            'In Progress',
                            'Completed',
                            'Rejected'
                        )
                    ),
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (decision_id)
                    REFERENCES recovery_decisions(id)
            )
        """)


def add_inventory_item(
    batch_id,
    product_name,
    branch,
    quantity,
    days_left,
    unit_cost,
    selling_price,
    product_code=None
):
    with get_connection() as connection:
        connection.execute("""
            INSERT INTO inventory (
                batch_id, product_code, product_name, branch,
                quantity, days_left, unit_cost, selling_price
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            batch_id,
            product_code,
            product_name,
            branch,
            quantity,
            days_left,
            unit_cost,
            selling_price
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
            INSERT INTO sales (
                product_name, branch, sale_date, units_sold
            )
            VALUES (?, ?, ?, ?)
        """, (product_name, branch, sale_date, units_sold))


def get_all_sales():
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM sales ORDER BY sale_date DESC"
        ).fetchall()
        return [dict(row) for row in rows]


def create_transfer_request(
    batch_id,
    source_branch,
    destination_branch,
    quantity,
    transport_cost
):
    with get_connection() as connection:
        connection.execute("""
            INSERT INTO transfer_requests (
                batch_id, source_branch, destination_branch,
                quantity, transport_cost
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            batch_id,
            source_branch,
            destination_branch,
            quantity,
            transport_cost
        ))


def get_all_transfer_requests():
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM transfer_requests ORDER BY id DESC"
        ).fetchall()
        return [dict(row) for row in rows]


def create_recovery_decision(
    batch_id,
    product_name,
    source_branch,
    destination_branch,
    quantity,
    action,
    selling_price,
    expected_recovery,
    risk_score,
    cvar_10,
    expected_expired_units,
    admin_username
):
    with get_connection() as connection:
        cursor = connection.execute("""
            INSERT INTO recovery_decisions (
                batch_id,
                product_name,
                source_branch,
                destination_branch,
                quantity,
                action,
                selling_price,
                expected_recovery,
                risk_score,
                cvar_10,
                expected_expired_units,
                admin_username
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            batch_id,
            product_name,
            source_branch,
            destination_branch,
            quantity,
            action,
            selling_price,
            expected_recovery,
            risk_score,
            cvar_10,
            expected_expired_units,
            admin_username
        ))

        return cursor.lastrowid


def create_notification(
    decision_id,
    batch_id,
    target_branch,
    notification_type,
    message
):
    with get_connection() as connection:
        cursor = connection.execute("""
            INSERT INTO notifications (
                decision_id,
                batch_id,
                target_branch,
                notification_type,
                message
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            decision_id,
            batch_id,
            target_branch,
            notification_type,
            message
        ))

        return cursor.lastrowid


def approve_recovery_decision(
    batch_id,
    product_name,
    source_branch,
    destination_branch,
    quantity,
    action,
    selling_price,
    expected_recovery,
    risk_score,
    cvar_10,
    expected_expired_units,
    admin_username
):
    with get_connection() as connection:

        cursor = connection.execute("""
            INSERT INTO recovery_decisions (
                batch_id,
                product_name,
                source_branch,
                destination_branch,
                quantity,
                action,
                selling_price,
                expected_recovery,
                risk_score,
                cvar_10,
                expected_expired_units,
                admin_username
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            batch_id,
            product_name,
            source_branch,
            destination_branch,
            quantity,
            action,
            selling_price,
            expected_recovery,
            risk_score,
            cvar_10,
            expected_expired_units,
            admin_username
        ))

        decision_id = cursor.lastrowid

        if action == "Keep":
            message = (
                f"Admin approved KEEP for {product_name}. "
                f"Batch: {batch_id}. Sell {quantity} units "
                f"at ₹{selling_price}."
            )

        elif action == "Markdown":
            message = (
                f"Admin approved MARKDOWN for {product_name}. "
                f"Batch: {batch_id}. Sell {quantity} units "
                f"at ₹{selling_price}."
            )

        elif action == "Transportation":
            message = (
                f"Prepare {quantity} units of {product_name} "
                f"from batch {batch_id} for transfer to "
                f"{destination_branch}."
            )

        elif action == "Distributor Return":
            message = (
                f"Prepare {quantity} units of {product_name} "
                f"from batch {batch_id} for distributor return."
            )

        else:
            raise ValueError("Invalid recovery action")

        connection.execute("""
            INSERT INTO notifications (
                decision_id,
                batch_id,
                target_branch,
                notification_type,
                message
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            decision_id,
            batch_id,
            source_branch,
            "Source Branch",
            message
        ))

        if action == "Transportation" and destination_branch:
            destination_message = (
                f"Incoming stock notification: {quantity} units "
                f"of {product_name}, batch {batch_id}, "
                f"will be transferred from {source_branch}. "
                f"Prepare to receive and confirm the stock."
            )

            connection.execute("""
                INSERT INTO notifications (
                    decision_id,
                    batch_id,
                    target_branch,
                    notification_type,
                    message
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                decision_id,
                batch_id,
                destination_branch,
                "Destination Branch",
                destination_message
            ))

        return decision_id


def get_recovery_decisions():
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT *
            FROM recovery_decisions
            ORDER BY id DESC
        """).fetchall()

        return [dict(row) for row in rows]


def get_notifications_for_branch(branch):
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT *
            FROM notifications
            WHERE target_branch = ?
            ORDER BY id DESC
        """, (branch,)).fetchall()

        return [dict(row) for row in rows]


def get_all_notifications():
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT *
            FROM notifications
            ORDER BY id DESC
        """).fetchall()

        return [dict(row) for row in rows]


def update_notification_status(notification_id, status):
    allowed_statuses = [
        "Pending",
        "Accepted",
        "In Progress",
        "Completed",
        "Rejected"
    ]

    if status not in allowed_statuses:
        raise ValueError("Invalid notification status")

    with get_connection() as connection:
        connection.execute("""
            UPDATE notifications
            SET status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (status, notification_id))


def create_admin_instruction_table():
    initialize_database()


def send_admin_instruction(
    batch_id,
    product,
    branch,
    quantity,
    action,
    selling_price,
    destination,
    instruction
):
    with get_connection() as connection:
        connection.execute("""
            INSERT INTO admin_instructions (
                batch_id,
                product,
                branch,
                quantity,
                action,
                selling_price,
                destination,
                instruction
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(batch_id),
            product,
            branch,
            quantity,
            action,
            selling_price,
            destination,
            instruction
        ))


def get_admin_instructions(branch=None):
    with get_connection() as connection:
        if branch:
            rows = connection.execute("""
                SELECT *
                FROM admin_instructions
                WHERE branch = ?
                ORDER BY id DESC
            """, (branch,)).fetchall()
        else:
            rows = connection.execute("""
                SELECT *
                FROM admin_instructions
                ORDER BY id DESC
            """).fetchall()

        return [dict(row) for row in rows]


def update_admin_instruction_status(instruction_id, status):
    with get_connection() as connection:
        connection.execute("""
            UPDATE admin_instructions
            SET status = ?
            WHERE id = ?
        """, (status, instruction_id))


if __name__ == "__main__":
    initialize_database()
    print("Database initialized successfully!")
    print(f"Database location: {DATABASE_PATH}")
