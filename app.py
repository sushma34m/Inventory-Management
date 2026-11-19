
import streamlit as st
import pandas as pd
import numpy as np
from backend.simulation import run_monte_carlo
from backend.database import (
    initialize_database,
    get_connection,
    add_inventory_item,
    get_all_inventory,
    get_inventory_by_branch,
    add_sales_record,
    get_all_sales,
    create_transfer_request,
    get_all_transfer_requests,
    approve_recovery_decision,
    get_recovery_decisions,
    get_notifications_for_branch,
    get_all_notifications,
    update_notification_status,
)

st.set_page_config(
    page_title="Near-Expiry Inventory Recovery",
    page_icon="📦",
    layout="wide"
)

BRANCHES = ["Hampankatta", "Kadri", "Bejai", "Kankanady", "Urwa"]

USERS = {
    "admin": {"password": "Admin@123", "role": "admin", "branch": None},
    "manager1": {"password": "Branch@123", "role": "manager", "branch": "Hampankatta"},
    "manager2": {"password": "Branch@123", "role": "manager", "branch": "Kadri"},
    "manager3": {"password": "Branch@123", "role": "manager", "branch": "Bejai"},
    "manager4": {"password": "Branch@123", "role": "manager", "branch": "Kankanady"},
    "manager5": {"password": "Branch@123", "role": "manager", "branch": "Urwa"},
}

SAMPLE_INVENTORY = pd.DataFrame({
    "Batch ID": ["B1001", "B1002", "B1003", "B1004", "B1005",
                 "B1006", "B1007", "B1008", "B1009", "B1010"],
    "Product Code": ["P001", "P002", "P001", "P003", "P004", "P005", "P006", "P007", "P008", "P009"],
    "Product": ["Biscuits 200g", "Bread", "Biscuits", "Yogurt",
                "Juice", "Butter", "Cheese", "Cake", "Curd", "Snacks"],
    "Branch": ["Hampankatta", "Hampankatta", "Kadri", "Kadri", "Bejai",
               "Bejai", "Kankanady", "Kankanady", "Urwa", "Urwa"],
    "Quantity": [40, 25, 50, 30, 35, 20, 15, 18, 28, 45],
    "Days Left": [20, 1, 8, 3, 4, 6, 2, 1, 5, 9],
    "Unit Cost (₹)": [10, 20, 10, 18, 15, 40, 60, 25, 12, 8],
    "Selling Price (₹)": [15, 28, 15, 25, 22, 50, 75, 35, 18, 12],
})

SAMPLE_SALES = pd.DataFrame([
    ["2026-10-15", "Biscuits 200g", "Hampankatta", 8],
    ["2026-10-16", "Biscuits 200g", "Hampankatta", 10],
    ["2026-10-17", "Biscuits 200g", "Hampankatta", 9],
    ["2026-10-18", "Biscuits 200g", "Hampankatta", 11],
    ["2026-10-19", "Biscuits 200g", "Hampankatta", 10],
    ["2026-10-15", "Biscuits 200g", "Kadri", 15],
    ["2026-10-16", "Biscuits 200g", "Kadri", 16],
    ["2026-10-17", "Biscuits 200g", "Kadri", 14],
    ["2026-10-18", "Biscuits 200g", "Kadri", 17],
    ["2026-10-19", "Biscuits 200g", "Kadri", 16],
    ["2026-10-15", "Bread", "Hampankatta", 10],
    ["2026-10-16", "Bread", "Hampankatta", 12],
    ["2026-10-17", "Bread", "Hampankatta", 11],
    ["2026-10-15", "Biscuits", "Kadri", 8],
    ["2026-10-16", "Biscuits", "Kadri", 10],
    ["2026-10-17", "Biscuits", "Kadri", 9],
    ["2026-10-15", "Yogurt", "Kadri", 6],
    ["2026-10-16", "Yogurt", "Kadri", 7],
    ["2026-10-17", "Yogurt", "Kadri", 5],
    ["2026-10-15", "Juice", "Bejai", 8],
    ["2026-10-16", "Juice", "Bejai", 9],
    ["2026-10-17", "Juice", "Bejai", 7],
], columns=["Date", "Product", "Branch", "Units Sold"])


def initialise_data():
    initialize_database()

    if not st.session_state.get("inventory_migration_done", False):
        with get_connection() as connection:
            connection.execute("""
                DELETE FROM inventory
                WHERE batch_id = 'B1011'
                   OR LOWER(product_name) = 'milk'
            """)

        existing_items = get_all_inventory()
        existing_ids = {
            str(item["batch_id"]).strip().casefold()
            for item in existing_items
        }

        for _, item in SAMPLE_INVENTORY.iterrows():
            batch_id = str(item["Batch ID"])

            if batch_id.casefold() not in existing_ids:
                add_inventory_item(
                    batch_id=batch_id,
                    product_code=item["Product Code"],
                    product_name=item["Product"],
                    branch=item["Branch"],
                    quantity=int(item["Quantity"]),
                    days_left=int(item["Days Left"]),
                    unit_cost=float(item["Unit Cost (₹)"]),
                    selling_price=float(item["Selling Price (₹)"])
                )

        st.session_state.pop("inventory", None)
        st.session_state.inventory_migration_done = True

    db_inventory = get_all_inventory()

    if db_inventory:
        inventory_df = pd.DataFrame(db_inventory)

        inventory_df = inventory_df.rename(columns={
            "batch_id": "Batch ID",
            "product_code": "Product Code",
            "product_name": "Product",
            "branch": "Branch",
            "quantity": "Quantity",
            "days_left": "Days Left",
            "unit_cost": "Unit Cost (₹)",
            "selling_price": "Selling Price (₹)"
        })

        if "Product Code" not in inventory_df.columns:
            inventory_df["Product Code"] = ""

        inventory_df["Product Code"] = inventory_df["Product Code"].fillna("")

        st.session_state.inventory = inventory_df[
            [
                "Batch ID",
                "Product Code",
                "Product",
                "Branch",
                "Quantity",
                "Days Left",
                "Unit Cost (₹)",
                "Selling Price (₹)"
            ]
        ]

    if "sales" not in st.session_state:
        db_sales = get_all_sales()

        if db_sales:
            sales_df = pd.DataFrame(db_sales)

            sales_df = sales_df.rename(columns={
                "sale_date": "Date",
                "product_name": "Product",
                "branch": "Branch",
                "units_sold": "Units Sold"
            })

            sales_df["Product Code"] = ""

            st.session_state.sales = sales_df[
                ["Date", "Product", "Product Code", "Branch", "Units Sold"]
            ]
        else:
            st.session_state.sales = SAMPLE_SALES.copy()

        st.session_state.sales["Product Code"] = ""

    if "transfer_requests" not in st.session_state:
        st.session_state.transfer_requests = get_all_transfer_requests()


def estimate_daily_sales(product, branch, sales):
    history = sales[
        (sales["Product"].astype(str).str.casefold() == str(product).casefold())
        & (sales["Branch"] == branch)
    ].copy()

    if not history.empty:
        history["Date"] = pd.to_datetime(history["Date"], errors="coerce")
        history["Units Sold"] = pd.to_numeric(
            history["Units Sold"], errors="coerce"
        ).fillna(0)

        latest_date = history["Date"].max()

        if pd.notna(latest_date):
            recent = history[
                (history["Date"] <= latest_date)
                & (history["Date"] > latest_date - pd.Timedelta(days=7))
            ]

            if not recent.empty:
                daily = recent.groupby("Date")["Units Sold"].sum().mean()
                return max(0.0, float(daily)), "Branch sales history"

    other_branches = sales[
        sales["Product"].astype(str).str.casefold() == str(product).casefold()
    ].copy()

    if not other_branches.empty:
        other_branches["Date"] = pd.to_datetime(
            other_branches["Date"], errors="coerce"
        )
        other_branches["Units Sold"] = pd.to_numeric(
            other_branches["Units Sold"], errors="coerce"
        ).fillna(0)

        latest_date = other_branches["Date"].max()

        if pd.notna(latest_date):
            recent = other_branches[
                (other_branches["Date"] <= latest_date)
                & (other_branches["Date"] > latest_date - pd.Timedelta(days=7))
            ]

            if not recent.empty:
                per_branch = (
                    recent.groupby(["Branch", "Date"])["Units Sold"]
                    .sum()
                    .groupby("Branch")
                    .mean()
                )
                return max(0.0, float(per_branch.mean())), "Other-branch sales history"

    product_name = str(product).casefold()
    fallback_rates = {
        "bread": 5.0,
        "biscuit": 4.0,
        "snack": 4.0,
        "juice": 3.0,
        "yogurt": 3.0,
        "curd": 3.0,
        "cake": 2.0,
        "butter": 2.0,
        "cheese": 2.0,
    }

    for keyword, rate in fallback_rates.items():
        if keyword in product_name:
            return rate, "Illustrative product-category estimate"

    return 1.0, "Generic fallback estimate (1 unit/day)"


def get_recommendations(inventory, sales):
    results = []

    at_risk = inventory[
        inventory["Days Left"].between(0, 30)
    ].copy()

    for _, batch in at_risk.iterrows():
        batch_id = str(batch["Batch ID"])
        product = str(batch["Product"])
        source = str(batch["Branch"])
        quantity = max(0, int(batch["Quantity"]))
        days_left = max(0, int(batch["Days Left"]))
        unit_cost = max(0.0, float(batch["Unit Cost (₹)"]))
        selling_price = max(
            0.0, float(batch["Selling Price (₹)"])
        )

        source_demand, demand_source = estimate_daily_sales(
            product, source, sales
        )

        destination = None
        destination_demand = 0.0

        for branch in BRANCHES:
            if branch == source:
                continue

            branch_sales = sales[
                (sales["Product"] == product)
                & (sales["Branch"] == branch)
            ]

            if branch_sales.empty:
                continue

            branch_demand, _ = estimate_daily_sales(
                product, branch, sales
            )

            if branch_demand > destination_demand:
                destination = branch
                destination_demand = branch_demand

        report = run_monte_carlo(
            quantity=quantity,
            selling_price=selling_price,
            unit_cost=unit_cost,
            days_left=days_left,
            source_daily_demand=source_demand,
            destination_daily_demand=destination_demand,
            distance_km=5,
            cost_per_km=12,
            handling_cost=30,
            simulations=1000,
            seed=42
        )

        action_results = []

        for action, values in report["results"].items():
            if action == "Transportation" and (
                destination is None or days_left <= 1
            ):
                continue

            if values["feasibility_rate_percent"] <= 0:
                continue

            action_results.append({
                "action": action,
                "destination": (
                    destination if action == "Transportation" else ""
                ),
                "expected_recovery": values["average_recovery"],
                "cvar_10": values["cvar_10"],
                "risk_aware_score": values["risk_score"],
                "expected_expired_units": values["expected_expired_units"],
                "worst_case_recovery": values["worst_case_recovery"],
                "expected_units_sold": max(
                    0, quantity - values["expected_expired_units"]
                )
            })

        if not action_results:
            continue

        best = max(
            action_results,
            key=lambda action: action["risk_aware_score"]
        )

        for action in action_results:
            action["Action"] = action["action"]
            action["Destination"] = action["destination"]
            action["Expected Recovery (₹)"] = action["expected_recovery"]
            action["CVaR 10% (₹)"] = action["cvar_10"]
            action["Risk-Aware Score (₹)"] = action["risk_aware_score"]
            action["Expected Expired Units"] = action["expected_expired_units"]
            action["Worst-Case Recovery (₹)"] = action["worst_case_recovery"]
            action["Expected Units Sold"] = action["expected_units_sold"]

        results.append({
            "Batch ID": batch_id,
            "Product": product,
            "Source Branch": source,
            "Days Left": days_left,
            "Quantity": quantity,
            "Predicted Daily Sales": round(source_demand, 2),
            "Prediction Source": demand_source,
            "Recommended Action": best["action"],
            "Destination": best["destination"],
            "Estimated Units Sold": round(best["expected_units_sold"]),
            "Estimated Revenue (₹)": best["expected_recovery"],
            "Estimated Unsold Units": round(best["expected_expired_units"]),
            "Estimated Recovery Value (₹)": best["expected_recovery"],
            "Expected Recovery (₹)": best["expected_recovery"],
            "CVaR 10% (₹)": best["cvar_10"],
            "Risk-Aware Score (₹)": best["risk_aware_score"],
            "Expected Expired Units": best["expected_expired_units"],
            "Worst-Case Recovery (₹)": best["worst_case_recovery"],
            "Action Simulation Results": action_results,
            "Reason": (
                f"Selected {best['action']} using Monte Carlo "
                f"risk-aware scoring. {demand_source}."
            )
        })

    return pd.DataFrame(results)


def login_screen():
    st.title("📦 Near-Expiry Inventory Recovery System")
    st.write("Sign in as the Main Admin or a branch manager.")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

    if submitted:
        user = USERS.get(username.strip())

        if user and user["password"] == password:
            st.session_state.logged_in = True
            st.session_state.username = username.strip()
            st.session_state.role = user["role"]
            st.session_state.branch = user["branch"]
            st.rerun()
        else:
            st.error("Incorrect username or password.")


def main():
    initialise_data()

    if not st.session_state.get("logged_in", False):
        login_screen()
        return

    username = st.session_state.username
    role = st.session_state.role
    assigned_branch = st.session_state.branch

    st.sidebar.title("📦 Inventory Recovery")
    st.sidebar.write(f"User: **{username}**")

    if role == "admin":
        st.sidebar.write("Role: **Main Admin**")
    else:
        st.sidebar.write(f"Branch: **{assigned_branch}**")

    if role == "admin":
        pages = [
            "Dashboard",
            "Inventory",
            "Recovery Analysis",
            "Admin Decision Center",
            "Transfer Requests"
        ]
    else:
        pages = [
            "Dashboard",
            "Inventory",
            "My Notifications",
            "Transfer Requests"
        ]

    page = st.sidebar.radio("Navigation", pages)

    if st.sidebar.button("Logout"):
        for key in ["logged_in", "username", "role", "branch"]:
            st.session_state.pop(key, None)
        st.rerun()

    all_inventory = st.session_state.inventory.copy()
    inventory = all_inventory.copy()
    sales = st.session_state.sales.copy()

    if role == "manager":
        inventory = inventory[
            inventory["Branch"] == assigned_branch
        ].copy()

    st.title("Near-Expiry Inventory Recovery")
    st.caption(
        "Scenario-based decision support for small retail stores in Mangalore."
    )

    if page == "Dashboard":
        st.subheader("Dashboard")

        at_risk = inventory[
            inventory["Days Left"].between(0, 30)
        ]

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Batches", len(inventory))
        col2.metric("At-Risk Batches", len(at_risk))
        col3.metric("At-Risk Units", int(at_risk["Quantity"].sum()))
        col4.metric(
            "Expiring in 30 Days",
            int(inventory["Days Left"].between(0, 30).sum())
        )

        if role == "admin":
            st.subheader("Branch Summary")
            summary = all_inventory.groupby("Branch").agg(
                Total_Batches=("Batch ID", "count"),
                Total_Units=("Quantity", "sum"),
                At_Risk_Batches=(
                    "Days Left",
                    lambda values: int(values.between(0, 30).sum())
                )
            ).reset_index()

            st.dataframe(
                summary, use_container_width=True, hide_index=True
            )

        st.subheader("Near-Expiry Stock")
        st.dataframe(
            at_risk.sort_values("Days Left"),
            use_container_width=True,
            hide_index=True
        )

    elif page == "Inventory":
        st.subheader("Inventory Management")
        st.info(
            "Managers can edit inventory only for their assigned branch."
        )

        edited = st.data_editor(
            inventory,
            use_container_width=True,
            hide_index=True,
            disabled=["Batch ID", "Branch"],
            key=f"inventory_editor_{username}"
        )

        if st.button("Save Inventory Changes"):
            if role == "admin":
                st.session_state.inventory = edited.copy()
            else:
                other_branches = all_inventory[
                    all_inventory["Branch"] != assigned_branch
                ]
                edited = edited.copy()
                edited["Branch"] = assigned_branch
                st.session_state.inventory = pd.concat(
                    [other_branches, edited], ignore_index=True
                )
            st.success("Inventory updated for this session.")

        st.subheader("Add New Batch")

        with st.form("add_batch_form"):
            product_code = st.text_input("Product Code", placeholder="e.g., PROD001")
            batch_id = st.text_input("Batch ID", placeholder="e.g., B1021")
            product = st.text_input("Product Name", placeholder="e.g., Cookies")

            if role == "admin":
                branch = st.selectbox("Branch", BRANCHES)
            else:
                branch = assigned_branch
                st.write(f"Branch: {assigned_branch}")

            quantity = st.number_input("Quantity", min_value=1, value=10, step=1)
            days_left = st.number_input("Days Left", min_value=0, max_value=365, value=10, step=1)
            unit_cost = st.number_input("Unit Cost (₹)", min_value=0.0, value=10.0)
            selling_price = st.number_input("Selling Price (₹)", min_value=0.0, value=15.0)
            add_batch = st.form_submit_button("Add Batch")

        if add_batch:
            product_code = product_code.strip().upper()
            batch_id = batch_id.strip()
            product = product.strip()

            if not product_code or not batch_id or not product:
                st.error("Product Code, Batch ID, and Product Name are required.")
            elif selling_price < 0 or unit_cost < 0:
                st.error("Prices cannot be negative.")
            else:
                try:
                    db_inventory = get_all_inventory()
                    db_ids = {str(item["batch_id"]).strip().casefold() for item in db_inventory}
                    session_ids = {str(value).strip().casefold() for value in st.session_state.inventory["Batch ID"]}
                    if batch_id.casefold() in db_ids or batch_id.casefold() in session_ids:
                        st.error("This Batch ID already exists. Every stock batch needs a unique Batch ID.")
                    else:
                        new_batch = pd.DataFrame([{
                            "Batch ID": batch_id,
                            "Product Code": product_code,
                            "Product": product,
                            "Branch": branch,
                            "Quantity": int(quantity),
                            "Days Left": int(days_left),
                            "Unit Cost (₹)": float(unit_cost),
                            "Selling Price (₹)": float(selling_price),
                        }])
                        add_inventory_item(
                            batch_id=batch_id,
                            product_code=product_code,
                            product_name=product,
                            branch=branch,
                            quantity=int(quantity),
                            days_left=int(days_left),
                            unit_cost=float(unit_cost),
                            selling_price=float(selling_price),
                        )
                        st.session_state.inventory = pd.concat(
                            [st.session_state.inventory, new_batch], ignore_index=True
                        )
                        st.success("Batch added and saved successfully.")
                        st.rerun()
                except Exception as e:
                    st.error(f"Could not save the batch. Check database.py supports product_code. Details: {e}")

        st.subheader("Sales History")
        st.caption("Choose a Product Code so sales records consistently refer to the same product across branches.")

        products = st.session_state.inventory[["Product Code", "Product"]].drop_duplicates().copy()
        products["Product Code"] = products["Product Code"].fillna("").astype(str)
        products = products[products["Product Code"].str.strip() != ""]
        product_options = {
            f"{row['Product Code']} — {row['Product']}": (row["Product Code"], row["Product"])
            for _, row in products.iterrows()
        }

        with st.form("sales_form"):
            sale_date = st.date_input("Sales Date", value=pd.Timestamp.today().date())
            if product_options:
                selected_product_label = st.selectbox("Product Code / Product", list(product_options.keys()))
            else:
                selected_product_label = None
                st.warning("Add Product Codes to inventory before recording sales.")
            sale_branch_options = [assigned_branch] if role == "manager" else BRANCHES
            sale_branch = st.selectbox("Sales Branch", sale_branch_options)
            units_sold = st.number_input("Units Sold", min_value=0, value=1, step=1)
            add_sale = st.form_submit_button("Add Sales Record", disabled=not bool(product_options))

        if add_sale and selected_product_label:
            product_code, sale_product = product_options[selected_product_label]
            try:
                add_sales_record(
                    product_name=sale_product,
                    branch=sale_branch,
                    sale_date=str(sale_date),
                    units_sold=int(units_sold),
                )
                new_sale = pd.DataFrame([{
                    "Date": str(sale_date),
                    "Product Code": product_code,
                    "Product": sale_product,
                    "Branch": sale_branch,
                    "Units Sold": int(units_sold),
                }])
                if "Product Code" not in st.session_state.sales.columns:
                    st.session_state.sales["Product Code"] = ""
                st.session_state.sales = pd.concat([st.session_state.sales, new_sale], ignore_index=True)
                st.success("Sales record saved to the database.")
                st.rerun()
            except Exception as e:
                st.error(f"Could not save sales record: {e}")

        st.subheader("Recorded Sales")
        st.dataframe(st.session_state.sales, use_container_width=True, hide_index=True)

    elif page == "Recovery Analysis":
        st.title("Recovery Analysis")
        st.caption("Monte Carlo-Based Inventory Recovery Optimization")

        recommendations = get_recommendations(
            inventory,
            sales
        )

        if recommendations.empty:
            st.success("No near-expiry inventory found.")

        else:
            st.subheader("Recovery Summary")

            total_batches = len(recommendations)
            total_quantity = recommendations["Quantity"].sum()
            total_recovery = recommendations["Expected Recovery (₹)"].sum()
            total_expired = recommendations["Expected Expired Units"].sum()

            col1, col2, col3, col4 = st.columns(4)

            col1.metric("At-Risk Batches", total_batches)
            col2.metric("At-Risk Units", int(total_quantity))
            col3.metric("Expected Recovery", f"₹{total_recovery:,.2f}")
            col4.metric("Expected Expired Units", f"{total_expired:.2f}")

            st.divider()

            st.subheader("Recommended Recovery Actions")

            display_columns = [
                "Batch ID",
                "Product",
                "Source Branch",
                "Days Left",
                "Recommended Action",
                "Destination",
                "Expected Recovery (₹)",
                "Risk-Aware Score (₹)",
                "Expected Expired Units"
            ]

            st.dataframe(
                recommendations[display_columns],
                use_container_width=True,
                hide_index=True
            )

            st.download_button(
                label="Download Recovery Report",
                data=recommendations[display_columns].to_csv(index=False),
                file_name="recovery_report.csv",
                mime="text/csv"
            )

            st.divider()

            st.subheader("Monte Carlo Recovery Comparison")

            for _, row in recommendations.iterrows():

                with st.expander(
                    f"{row['Product']} | Batch {row['Batch ID']}"
                ):

                    st.write(f"**Source Branch:** {row['Source Branch']}")
                    st.write(f"**Days Left:** {row['Days Left']}")
                    st.write(
                        f"**Recommended Action:** {row['Recommended Action']}"
                    )

                    if row["Destination"]:
                        st.write(
                            f"**Suggested Destination:** {row['Destination']}"
                        )

                    col1, col2, col3 = st.columns(3)

                    col1.metric(
                        "Expected Recovery",
                        f"₹{row['Expected Recovery (₹)']:,.2f}"
                    )

                    col2.metric(
                        "Risk-Aware Score",
                        f"₹{row['Risk-Aware Score (₹)']:,.2f}"
                    )

                    col3.metric(
                        "Expected Expired Units",
                        f"{row['Expected Expired Units']:.2f}"
                    )

                    st.metric(
                        "CVaR 10%",
                        f"₹{row['CVaR 10% (₹)']:,.2f}"
                    )

                    st.metric(
                        "Worst-Case Recovery",
                        f"₹{row['Worst-Case Recovery (₹)']:,.2f}"
                    )

                    st.divider()

                    action_df = pd.DataFrame(
                        row["Action Simulation Results"]
                    )

                    comparison_columns = [
                        "Action",
                        "Destination",
                        "Expected Recovery (₹)",
                        "CVaR 10% (₹)",
                        "Risk-Aware Score (₹)",
                        "Expected Expired Units",
                        "Worst-Case Recovery (₹)"
                    ]

                    st.dataframe(
                        action_df[comparison_columns],
                        use_container_width=True,
                        hide_index=True
                    )

                    st.bar_chart(
                        action_df.set_index("Action")[
                            "Risk-Aware Score (₹)"
                        ]
                    )

                    st.info(row["Reason"])


                    st.divider()

                    st.subheader("What-If Scenario Analysis")

                    st.caption(
                        "Change business conditions and compare the new "
                        "simulation with the original prediction."
                    )

                    batch_data = inventory[
                        inventory["Batch ID"].astype(str) == str(row["Batch ID"])
                    ].iloc[0]

                    col1, col2 = st.columns(2)

                    with col1:
                        demand_change = st.slider(
                            "Daily Demand Change (%)",
                            min_value=-50,
                            max_value=100,
                            value=0,
                            step=5,
                            key=f"demand_change_{row['Batch ID']}"
                        )

                        scenario_days = st.number_input(
                            "Remaining Expiry Days",
                            min_value=0,
                            max_value=365,
                            value=int(row["Days Left"]),
                            step=1,
                            key=f"scenario_days_{row['Batch ID']}"
                        )

                    with col2:
                        transport_change = st.slider(
                            "Transportation Cost Change (%)",
                            min_value=-50,
                            max_value=100,
                            value=0,
                            step=5,
                            key=f"transport_change_{row['Batch ID']}"
                        )

                        st.metric(
                            "Original Daily Demand",
                            f"{row['Predicted Daily Sales']:.2f} units"
                        )

                    scenario_source_demand = max(
                        0.0,
                        float(row["Predicted Daily Sales"])
                        * (1 + demand_change / 100)
                    )

                    destination_name = row["Destination"]

                    if destination_name:
                        scenario_destination_demand, _ = estimate_daily_sales(
                            row["Product"],
                            destination_name,
                            sales
                        )
                    else:
                        scenario_destination_demand = 0.0

                    scenario_cost_per_km = max(
                        0.0,
                        12 * (1 + transport_change / 100)
                    )

                    st.write(
                        f"**Scenario Daily Demand:** "
                        f"{scenario_source_demand:.2f} units"
                    )

                    st.write(
                        f"**Scenario Transportation Cost:** "
                        f"₹{scenario_cost_per_km:.2f} per km"
                    )

                    if st.button(
                        "Run What-If Simulation",
                        key=f"run_what_if_{row['Batch ID']}",
                        type="primary"
                    ):

                        original_report = run_monte_carlo(
                            quantity=int(row["Quantity"]),
                            selling_price=float(batch_data["Selling Price (₹)"]),
                            unit_cost=float(batch_data["Unit Cost (₹)"]),
                            days_left=int(row["Days Left"]),
                            source_daily_demand=float(row["Predicted Daily Sales"]),
                            destination_daily_demand=float(
                                scenario_destination_demand
                            ),
                            distance_km=5,
                            cost_per_km=12,
                            handling_cost=30,
                            simulations=1000,
                            seed=42
                        )

                        scenario_report = run_monte_carlo(
                            quantity=int(row["Quantity"]),
                            selling_price=float(batch_data["Selling Price (₹)"]),
                            unit_cost=float(batch_data["Unit Cost (₹)"]),
                            days_left=int(scenario_days),
                            source_daily_demand=float(scenario_source_demand),
                            destination_daily_demand=float(
                                scenario_destination_demand
                            ),
                            distance_km=5,
                            cost_per_km=float(scenario_cost_per_km),
                            handling_cost=30,
                            simulations=1000,
                            seed=42
                        )

                        st.subheader("Original vs What-If Results")

                        original_action = original_report["recommended_action"]
                        scenario_action = scenario_report["recommended_action"]

                        result_columns = []

                        for action in original_report["results"]:

                            original_values = original_report["results"][action]
                            scenario_values = scenario_report["results"][action]

                            result_columns.append({
                                "Action": action,
                                "Original Recovery (₹)": original_values["average_recovery"],
                                "What-If Recovery (₹)": scenario_values["average_recovery"],
                                "Original Risk Score (₹)": original_values["risk_score"],
                                "What-If Risk Score (₹)": scenario_values["risk_score"],
                                "Original Expired Units": original_values["expected_expired_units"],
                                "What-If Expired Units": scenario_values["expected_expired_units"]
                            })

                        comparison_df = pd.DataFrame(result_columns)

                        st.dataframe(
                            comparison_df,
                            use_container_width=True,
                            hide_index=True
                        )

                        col1, col2 = st.columns(2)

                        with col1:
                            st.metric(
                                "Original Recommendation",
                                original_action or "No feasible action"
                            )

                        with col2:
                            st.metric(
                                "What-If Recommendation",
                                scenario_action or "No feasible action"
                            )

                        if original_action == scenario_action:
                            st.success(
                                "The recommended action remains the same "
                                "under the changed conditions."
                            )
                        else:
                            st.warning(
                                f"The recommendation changed from "
                                f"{original_action} to {scenario_action}."
                            )

                        st.subheader("What-If Risk Score Comparison")

                        chart_df = comparison_df.set_index("Action")[
                            [
                                "Original Risk Score (₹)",
                                "What-If Risk Score (₹)"
                            ]
                        ]

                        st.bar_chart(chart_df)

                        st.caption(
                            "Both results use 1,000 simulations and the same "
                            "random seed. Scenario changes are temporary and "
                            "do not modify inventory or sales records."
                        )

    elif page == "Admin Decision Center":
        st.title("Admin Decision Center")
        st.caption(
            "Review Monte Carlo recommendations and approve the final recovery action."
        )

        if role != "admin":
            st.error("Only the admin can approve recovery decisions.")
            st.stop()

        recommendations = get_recommendations(
            all_inventory,
            sales
        )

        if recommendations.empty:
            st.success("No near-expiry inventory requires a decision.")

        else:
            st.subheader("Batches Awaiting Admin Decision")

            for _, row in recommendations.iterrows():

                batch_id = str(row["Batch ID"])
                product = str(row["Product"])
                source_branch = str(row["Source Branch"])

                action_df = pd.DataFrame(
                    row["Action Simulation Results"]
                )

                with st.expander(
                    f"{product} | Batch {batch_id} | {source_branch}"
                ):

                    st.write(f"**Product:** {product}")
                    st.write(f"**Batch ID:** {batch_id}")
                    st.write(f"**Source Branch:** {source_branch}")
                    st.write(f"**Available Quantity:** {row['Quantity']}")
                    st.write(f"**Days Until Expiry:** {row['Days Left']}")

                    st.subheader("Monte Carlo Comparison")

                    comparison_columns = [
                        "Action",
                        "Destination",
                        "Expected Recovery (₹)",
                        "CVaR 10% (₹)",
                        "Risk-Aware Score (₹)",
                        "Expected Expired Units",
                        "Worst-Case Recovery (₹)"
                    ]

                    st.dataframe(
                        action_df[comparison_columns],
                        use_container_width=True,
                        hide_index=True
                    )

                    st.bar_chart(
                        action_df.set_index("Action")[
                            "Risk-Aware Score (₹)"
                        ]
                    )

                    recommended_action = row["Recommended Action"]

                    st.success(
                        f"Monte Carlo recommends: {recommended_action}"
                    )

                    action_options = action_df["Action"].tolist()

                    selected_action = st.selectbox(
                        "Admin: Select Final Recovery Action",
                        action_options,
                        index=action_options.index(recommended_action),
                        key=f"admin_action_{batch_id}"
                    )

                    selected_result = action_df[
                        action_df["Action"] == selected_action
                    ].iloc[0]

                    destination_branch = None

                    if selected_action == "Transportation":

                        destination_options = [
                            branch for branch in BRANCHES
                            if branch != source_branch
                        ]

                        suggested_destination = str(
                            selected_result["Destination"]
                        )

                        if suggested_destination not in destination_options:
                            suggested_destination = destination_options[0]

                        destination_branch = st.selectbox(
                            "Select Destination Branch",
                            destination_options,
                            index=destination_options.index(
                                suggested_destination
                            ),
                            key=f"admin_destination_{batch_id}"
                        )

                    batch_inventory = all_inventory[
                        all_inventory["Batch ID"].astype(str) == batch_id
                    ]

                    if batch_inventory.empty:
                        st.error("Batch not found in inventory.")
                        continue

                    batch_data = batch_inventory.iloc[0]

                    original_price = float(
                        batch_data["Selling Price (₹)"]
                    )

                    if selected_action == "Markdown":
                        final_selling_price = round(
                            original_price * 0.75, 2
                        )

                    elif selected_action == "Keep":
                        final_selling_price = original_price

                    else:
                        final_selling_price = None

                    if final_selling_price is not None:
                        st.metric(
                            "Selling Price",
                            f"₹{final_selling_price:.2f}"
                        )

                    st.metric(
                        "Expected Recovery",
                        f"₹{selected_result['Expected Recovery (₹)']:,.2f}"
                    )

                    st.metric(
                        "Risk-Aware Score",
                        f"₹{selected_result['Risk-Aware Score (₹)']:,.2f}"
                    )

                    st.metric(
                        "Expected Expired Units",
                        f"{selected_result['Expected Expired Units']:.2f}"
                    )

                    st.warning(
                        "Approving this decision will permanently save it "
                        "and send notifications to the relevant branch managers."
                    )

                    if st.button(
                        "Approve Final Decision",
                        key=f"approve_decision_{batch_id}",
                        type="primary"
                    ):

                        try:
                            decision_id = approve_recovery_decision(
                                batch_id=batch_id,
                                product_name=product,
                                source_branch=source_branch,
                                destination_branch=destination_branch,
                                quantity=int(row["Quantity"]),
                                action=selected_action,
                                selling_price=final_selling_price,
                                expected_recovery=float(
                                    selected_result["Expected Recovery (₹)"]
                                ),
                                risk_score=float(
                                    selected_result["Risk-Aware Score (₹)"]
                                ),
                                cvar_10=float(
                                    selected_result["CVaR 10% (₹)"]
                                ),
                                expected_expired_units=float(
                                    selected_result["Expected Expired Units"]
                                ),
                                admin_username=username
                            )

                            st.success(
                                f"Decision #{decision_id} approved successfully. "
                                "Branch notifications have been created."
                            )

                            st.rerun()

                        except Exception as error:
                            st.error(
                                f"Could not approve decision: {error}"
                            )

            st.divider()

        st.subheader("Approved Decision History")

        decisions = get_recovery_decisions()

        if decisions:
            st.dataframe(
                pd.DataFrame(decisions),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No approved recovery decisions yet.")

            st.divider()

        st.subheader("Branch Notification Tracking")

        notifications = get_all_notifications()

        if notifications:
            notification_df = pd.DataFrame(notifications)

            display_columns = [
                "decision_id",
                "batch_id",
                "target_branch",
                "notification_type",
                "message",
                "status",
                "created_at",
                "updated_at"
            ]

            notification_df = notification_df[display_columns]

            notification_df = notification_df.rename(columns={
                "decision_id": "Decision ID",
                "batch_id": "Batch ID",
                "target_branch": "Branch",
                "notification_type": "Notification Type",
                "message": "Instruction",
                "status": "Manager Status",
                "created_at": "Sent At",
                "updated_at": "Last Updated"
            })

            st.dataframe(
                notification_df,
                use_container_width=True,
                hide_index=True
            )

            st.subheader("Notification Status Summary")

            status_counts = notification_df[
                "Manager Status"
            ].value_counts()

            st.bar_chart(status_counts)

        else:
            st.info("No branch notifications available.")

    elif page == "My Notifications":
        st.title("My Notifications")
        st.caption(f"Messages for {assigned_branch} Branch")

        notifications = get_notifications_for_branch(assigned_branch)

        if not notifications:
            st.info("No notifications received yet.")

        else:
            for notification in notifications:
                with st.container(border=True):
                    st.subheader(
                        f"Notification #{notification['id']}"
                    )

                    st.write(
                        f"**Product Batch:** {notification['batch_id']}"
                    )

                    st.write(
                        f"**Type:** {notification['notification_type']}"
                    )

                    st.write(
                        f"**Message:** {notification['message']}"
                    )

                    st.write(
                        f"**Current Status:** {notification['status']}"
                    )

                    statuses = [
                        "Pending",
                        "Accepted",
                        "In Progress",
                        "Completed",
                        "Rejected"
                    ]

                    selected_status = st.selectbox(
                        "Update Status",
                        statuses,
                        index=statuses.index(notification["status"]),
                        key=f"notification_status_{notification['id']}"
                    )

                    if st.button(
                        "Update Status",
                        key=f"update_notification_{notification['id']}"
                    ):
                        update_notification_status(
                            notification["id"],
                            selected_status
                        )

                        st.success("Notification status updated.")
                        st.rerun()
    
    elif page == "Transfer Requests":
        st.subheader("Inter-Branch Transfer Requests")

        if role == "manager":
            st.write(f"Submit a transfer request from **{assigned_branch}**.")

            if inventory.empty:
                st.info("No inventory batches are available.")
            else:
                with st.form("transfer_request_form"):
                    selected_batch = st.selectbox(
                        "Batch", inventory["Batch ID"].astype(str).tolist()
                    )
                    destination = st.selectbox(
                        "Destination Branch",
                        [branch for branch in BRANCHES if branch != assigned_branch]
                    )
                    transfer_quantity = st.number_input(
                        "Quantity to Transfer", min_value=1, value=1, step=1
                    )
                    reason = st.text_area("Reason for Transfer")
                    submit_request = st.form_submit_button(
                        "Submit Transfer Request"
                    )

                if submit_request:
                    batch = inventory[
                        inventory["Batch ID"].astype(str) == selected_batch
                    ].iloc[0]

                    if transfer_quantity > int(batch["Quantity"]):
                        st.error(
                            "Transfer quantity exceeds available stock."
                        )
                    else:
                        st.session_state.transfer_requests.append({
                            "Request ID": (
                                f"TR{len(st.session_state.transfer_requests) + 1:03d}"
                            ),
                            "Batch ID": selected_batch,
                            "Product": batch["Product"],
                            "Source Branch": assigned_branch,
                            "Destination Branch": destination,
                            "Quantity": int(transfer_quantity),
                            "Reason": reason,
                            "Status": "Pending",
                        })
                        st.success("Transfer request submitted.")
                        st.rerun()

        requests = st.session_state.transfer_requests

        if role == "admin":
            st.subheader("All Branch Requests")

            if not requests:
                st.info("No transfer requests yet.")

            for index, request in enumerate(requests):
                st.write(
                    f"**{request['Request ID']}** | {request['Product']} | "
                    f"{request['Source Branch']} → {request['Destination Branch']} | "
                    f"Quantity: {request['Quantity']} | Status: **{request['Status']}**"
                )

                if request["Status"] == "Pending":
                    left, right = st.columns(2)

                    if left.button("Approve", key=f"approve_{index}"):
                        request["Status"] = "Approved"
                        st.rerun()

                    if right.button("Reject", key=f"reject_{index}"):
                        request["Status"] = "Rejected"
                        st.rerun()

                st.divider()

        else:
            branch_requests = [
                request for request in requests
                if request["Source Branch"] == assigned_branch
                or request["Destination Branch"] == assigned_branch
            ]

            if branch_requests:
                st.dataframe(
                    pd.DataFrame(branch_requests),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No transfer requests for your branch.")

        st.caption(
            "Demo limitation: approving a request changes its status only; "
            "it does not move stock. Session data is not permanently saved."
        )


if __name__ == "__main__":
    main()
