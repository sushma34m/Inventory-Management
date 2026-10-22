
import streamlit as st
import pandas as pd
import numpy as np
from backend.database import (
    initialize_database,
    add_inventory_item,
    get_all_inventory,
    get_inventory_by_branch,
    add_sales_record,
    get_all_sales,
    create_transfer_request,
    get_all_transfer_requests,
)

st.set_page_config(
    page_title="Near-Expiry Inventory Recovery",
    page_icon="📦",
    layout="wide"
)

BRANCHES = ["Hampankatta", "Kadri", "Bejai", "Kankanady", "Urwa"]

# Demo login credentials
USERS = {
    "admin": {"password": "Admin@123", "role": "admin", "branch": None},
    "manager1": {"password": "Branch@123", "role": "manager", "branch": "Hampankatta"},
    "manager2": {"password": "Branch@123", "role": "manager", "branch": "Kadri"},
    "manager3": {"password": "Branch@123", "role": "manager", "branch": "Bejai"},
    "manager4": {"password": "Branch@123", "role": "manager", "branch": "Kankanady"},
    "manager5": {"password": "Branch@123", "role": "manager", "branch": "Urwa"},
}

# Sample inventory: demonstration data
SAMPLE_INVENTORY = pd.DataFrame({
    "Batch ID": ["B1001", "B1002", "B1003", "B1004", "B1005",
                 "B1006", "B1007", "B1008", "B1009", "B1010"],
    "Product": ["Biscuits 200g", "Bread", "Biscuits", "Yogurt",
                "Juice", "Butter", "Cheese", "Cake", "Curd", "Snacks"],
    "Branch": ["Hampankatta", "Hampankatta", "Kadri", "Kadri", "Bejai",
               "Bejai", "Kankanady", "Kankanady", "Urwa", "Urwa"],
    "Quantity": [40, 25, 50, 30, 35, 20, 15, 18, 28, 45],
    "Days Left": [20, 1, 8, 3, 4, 6, 2, 1, 5, 9],
    "Unit Cost (₹)": [10, 20, 10, 18, 15, 40, 60, 25, 12, 8],
    "Selling Price (₹)": [15, 28, 15, 25, 22, 50, 75, 35, 18, 12],
})

# Sample sales records. Replace with actual store data when available.
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

    if "inventory" not in st.session_state:
        db_inventory = get_all_inventory()

        if db_inventory:
            inventory_df = pd.DataFrame(db_inventory)
            inventory_df = inventory_df.rename(columns={
                "batch_id": "Batch ID",
                "product_name": "Product",
                "branch": "Branch",
                "quantity": "Quantity",
                "days_left": "Days Left",
                "unit_cost": "Unit Cost (â‚¹)",
                "selling_price": "Selling Price (â‚¹)",
            })

            st.session_state.inventory = inventory_df[
                [
                    "Batch ID", "Product", "Branch", "Quantity",
                    "Days Left", "Unit Cost (â‚¹)", "Selling Price (â‚¹)"
                ]
            ]
        else:
            st.session_state.inventory = SAMPLE_INVENTORY.copy()

    if "sales" not in st.session_state:
        db_sales = get_all_sales()

        if db_sales:
            sales_df = pd.DataFrame(db_sales)
            sales_df = sales_df.rename(columns={
                "sale_date": "Date",
                "product_name": "Product",
                "branch": "Branch",
                "units_sold": "Units Sold",
            })

            st.session_state.sales = sales_df[
                ["Date", "Product", "Branch", "Units Sold"]
            ]
        else:
            st.session_state.sales = SAMPLE_SALES.copy()

    if "transfer_requests" not in st.session_state:
        st.session_state.transfer_requests = get_all_transfer_requests()


def estimate_daily_sales(product, branch, sales):
    """Estimate daily sales using history or a clearly labelled fallback."""

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

    # Use the same product's history from other branches if available.
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

    # Illustrative fallback rates, not actual measured demand.
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
        cost = max(0.0, float(batch["Unit Cost (₹)"]))
        price = max(0.0, float(batch["Selling Price (₹)"]))

        daily_demand, prediction_source = estimate_daily_sales(
            product, source, sales
        )

        keep_units = min(
            quantity, int(np.floor(daily_demand * days_left))
        )

        markdown_units = min(
            quantity, int(np.floor(daily_demand * 1.25 * days_left))
        )

        options = [
            {
                "Action": "Keep",
                "Destination": source,
                "Estimated Units Sold": keep_units,
                "Estimated Revenue (₹)": round(keep_units * price, 2),
                "Estimated Unsold Units": quantity - keep_units,
                "Estimated Recovery Value (₹)": round(
                    keep_units * price
                    + (quantity - keep_units) * cost * 0.25, 2
                ),
                "Reason": "Estimated demand at the current branch before expiry.",
            },
            {
                "Action": "Markdown",
                "Destination": source,
                "Estimated Units Sold": markdown_units,
                "Estimated Revenue (₹)": round(
                    markdown_units * price * 0.75, 2
                ),
                "Estimated Unsold Units": quantity - markdown_units,
                "Estimated Recovery Value (₹)": round(
                    markdown_units * price * 0.75
                    + (quantity - markdown_units) * cost * 0.25, 2
                ),
                "Reason": "Assumes a 25% discount and a 25% demand uplift.",
            },
            {
                "Action": "Return to Distributor",
                "Destination": "Distributor",
                "Estimated Units Sold": 0,
                "Estimated Revenue (₹)": round(quantity * cost * 0.50, 2),
                "Estimated Unsold Units": quantity,
                "Estimated Recovery Value (₹)": round(
                    quantity * cost * 0.50, 2
                ),
                "Reason": (
                    "Assumes returns are accepted and 50% of unit cost "
                    "is recovered. Verify supplier policy."
                ),
            },
        ]

        # Consider transfers only when matching product history exists there.
        if days_left > 1:
            for destination in BRANCHES:
                if destination == source:
                    continue

                destination_history = sales[
                    (sales["Product"].astype(str).str.casefold() == product.casefold())
                    & (sales["Branch"] == destination)
                ]

                if destination_history.empty:
                    continue

                destination_daily, _ = estimate_daily_sales(
                    product, destination, sales
                )

                transfer_units = min(
                    quantity,
                    int(np.floor(destination_daily * (days_left - 1)))
                )

                # Illustrative assumptions: one day of transport, ₹2 per unit.
                transport_cost = quantity * 2
                transfer_revenue = transfer_units * price - transport_cost

                options.append({
                    "Action": "Transfer",
                    "Destination": destination,
                    "Estimated Units Sold": transfer_units,
                    "Estimated Revenue (₹)": round(transfer_revenue, 2),
                    "Estimated Unsold Units": quantity - transfer_units,
                    "Estimated Recovery Value (₹)": round(
                        transfer_revenue
                        + (quantity - transfer_units) * cost * 0.25, 2
                    ),
                    "Reason": (
                        "Uses destination sales history; assumes one day "
                        "for transport and ₹2 transport cost per unit."
                    ),
                })

        best = max(
            options,
            key=lambda option: option["Estimated Recovery Value (₹)"]
        )

        results.append({
            "Batch ID": batch_id,
            "Product": product,
            "Source Branch": source,
            "Days Left": days_left,
            "Quantity": quantity,
            "Predicted Daily Sales": round(daily_demand, 2),
            "Prediction Source": prediction_source,
            "Recommended Action": best["Action"],
            "Destination": best["Destination"],
            "Estimated Units Sold": best["Estimated Units Sold"],
            "Estimated Revenue (₹)": best["Estimated Revenue (₹)"],
            "Estimated Unsold Units": best["Estimated Unsold Units"],
            "Estimated Recovery Value (₹)": best["Estimated Recovery Value (₹)"],
            "Reason": best["Reason"],
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

    page = st.sidebar.radio(
        "Navigation",
        ["Dashboard", "Inventory", "Recovery Analysis", "Transfer Requests"]
    )

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
            "Expiring in 3 Days",
            int(inventory["Days Left"].between(0, 3).sum())
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
            batch_id = st.text_input("Batch ID")
            product = st.text_input("Product Name")

            if role == "admin":
                branch = st.selectbox("Branch", BRANCHES)
            else:
                branch = assigned_branch
                st.write(f"Branch: {assigned_branch}")

            quantity = st.number_input(
                "Quantity", min_value=1, value=10, step=1
            )
            days_left = st.number_input(
                "Days Left", min_value=0, max_value=365, value=10, step=1
            )
            unit_cost = st.number_input(
                "Unit Cost (₹)", min_value=0.0, value=10.0
            )
            selling_price = st.number_input(
                "Selling Price (₹)", min_value=0.0, value=15.0
            )
            add_batch = st.form_submit_button("Add Batch")

        if add_batch:
            batch_id = batch_id.strip()
            product = product.strip()

            if not batch_id or not product:
                st.error("Enter both Batch ID and product name.")
            elif batch_id in st.session_state.inventory["Batch ID"].astype(str).values:
                st.error("That Batch ID already exists.")
            else:
                new_batch = pd.DataFrame([{
                    "Batch ID": batch_id,
                    "Product": product,
                    "Branch": branch,
                    "Quantity": int(quantity),
                    "Days Left": int(days_left),
                    "Unit Cost (₹)": float(unit_cost),
                    "Selling Price (₹)": float(selling_price),
                }])

            try:
                    add_inventory_item(
                        batch_id=batch_id,
                        product_name=product,
                        branch=branch,
                        quantity=int(quantity),
                        days_left=int(days_left),
                        unit_cost=float(unit_cost),
                        selling_price=float(selling_price),
                    )

                    st.session_state.inventory = pd.concat(
                        [st.session_state.inventory, new_batch],
                        ignore_index=True
                    )

                    st.success("Batch added and saved to the database.")
                    st.rerun()

            except Exception as e:
                    st.error(f"Could not save the batch: {e}")

        st.subheader("Add Sales History")
        st.caption(
            "Add actual sales records to improve predictions. "
            "Product names must match the inventory product name."
        )

        with st.form("sales_form"):
            sale_date = st.date_input(
                "Sales Date", value=pd.Timestamp.today().date()
            )
            sale_product = st.text_input("Sales Product Name")
            sale_branch = st.selectbox("Sales Branch", BRANCHES)
            units_sold = st.number_input(
                "Units Sold", min_value=0, value=1, step=1
            )
            add_sale = st.form_submit_button("Add Sales Record")

        if add_sale:
            if not sale_product.strip():
                st.error("Enter a product name.")
            else:
                new_sale = pd.DataFrame([{
                    "Date": str(sale_date),
                    "Product": sale_product.strip(),
                    "Branch": sale_branch,
                    "Units Sold": int(units_sold),
                }])

                st.session_state.sales = pd.concat(
                    [st.session_state.sales, new_sale],
                    ignore_index=True
                )
                st.success("Sales record added.")
                st.rerun()

    elif page == "Recovery Analysis":
        st.subheader("Batch-Wise Recovery Analysis")

        st.warning(
            "Demonstration estimates use fallback demand and assumptions "
            "for markdown uplift, transport cost/time, and distributor refunds. "
            "Verify actual policies before taking action."
        )

        recommendations = get_recommendations(inventory, sales)

        if recommendations.empty:
            st.info(
                "No batches are within the 30-day analysis window."
            )
        else:
            col1, col2, col3 = st.columns(3)
            col1.metric("Batches Analysed", len(recommendations))
            col2.metric(
                "Estimated Recovery Value",
                f"₹{recommendations['Estimated Recovery Value (₹)'].sum():,.2f}"
            )
            col3.metric(
                "Estimated Unsold Units",
                int(recommendations["Estimated Unsold Units"].sum())
            )

            st.subheader("Exact Batch Recommendations")
            st.dataframe(
                recommendations,
                use_container_width=True,
                hide_index=True
            )

            st.download_button(
                "Download Recommendations CSV",
                data=recommendations.to_csv(index=False).encode("utf-8"),
                file_name="recovery_recommendations.csv",
                mime="text/csv"
            )

            st.subheader("Batch-Wise Estimated Sold vs Unsold Units")
            chart = recommendations[
                ["Batch ID", "Product", "Estimated Units Sold", "Estimated Unsold Units"]
            ].copy()

            chart["Batch"] = (
                chart["Batch ID"].astype(str) + " — " + chart["Product"]
            )

            st.bar_chart(
                chart.set_index("Batch")[
                    ["Estimated Units Sold", "Estimated Unsold Units"]
                ]
            )

            st.subheader("What Should Happen to Each Batch?")

            for _, row in recommendations.iterrows():
                heading = (
                    f"{row['Batch ID']} — {row['Product']} | "
                    f"{row['Recommended Action']} → {row['Destination']}"
                )

                with st.expander(heading):
                    st.write(f"**Source branch:** {row['Source Branch']}")
                    st.write(f"**Days left:** {row['Days Left']}")
                    st.write(
                        f"**Predicted daily sales:** "
                        f"{row['Predicted Daily Sales']} units/day"
                    )
                    st.write(
                        f"**Prediction basis:** {row['Prediction Source']}"
                    )
                    st.write(
                        f"**Recommended action:** {row['Recommended Action']}"
                    )
                    st.write(f"**Destination:** {row['Destination']}")
                    st.write(
                        f"**Estimated units sold:** {row['Estimated Units Sold']}"
                    )
                    st.write(
                        f"**Estimated unsold units:** {row['Estimated Unsold Units']}"
                    )
                    st.write(
                        f"**Estimated revenue:** ₹{row['Estimated Revenue (₹)']:,.2f}"
                    )
                    st.write(
                        f"**Estimated recovery value:** "
                        f"₹{row['Estimated Recovery Value (₹)']:,.2f}"
                    )
                    st.write(f"**Reason:** {row['Reason']}")

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
