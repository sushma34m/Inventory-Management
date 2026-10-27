
from backend.transport import (
    calculate_transport_cost,
    check_transfer_feasibility
)


def evaluate_markdown(
    quantity,
    selling_price,
    unit_cost,
    days_left,
    expected_daily_demand,
    discount_rate=0.25,
    demand_uplift=0.25
):
    """
    Estimate recovery value from markdown sales.

    The discount and demand uplift are assumptions that
    should be calibrated using real store data.
    """

    if quantity < 0 or selling_price < 0 or unit_cost < 0:
        raise ValueError("Quantity and prices cannot be negative.")

    if days_left < 0:
        return {
            "action": "Markdown",
            "feasible": False,
            "estimated_recovery": 0,
            "reason": "Product is already expired."
        }

    if expected_daily_demand < 0:
        raise ValueError("Expected daily demand cannot be negative.")

    if not 0 <= discount_rate <= 1:
        raise ValueError("Discount rate must be between 0 and 1.")

    if demand_uplift < 0:
        raise ValueError("Demand uplift cannot be negative.")

    discounted_price = selling_price * (1 - discount_rate)
    adjusted_daily_demand = expected_daily_demand * (1 + demand_uplift)

    # Estimate how many units can sell before expiry.
    estimated_units_sold = min(
        quantity,
        int(adjusted_daily_demand * days_left)
    )

    revenue = estimated_units_sold * discounted_price

    return {
        "action": "Markdown",
        "feasible": estimated_units_sold > 0,
        "estimated_units_sold": estimated_units_sold,
        "unsold_units": quantity - estimated_units_sold,
        "discounted_price": round(discounted_price, 2),
        "estimated_recovery": round(revenue, 2),
        "reason": (
            "Estimated markdown sales before expiry."
            if estimated_units_sold > 0
            else "No units are expected to sell before expiry."
        )
    }


def evaluate_transport(
    quantity,
    selling_price,
    unit_cost,
    days_left,
    destination_daily_demand,
    distance_km,
    cost_per_km,
    handling_cost=0,
    transport_days=1
):
    """
    Estimate recovery from transferring stock to another branch.

    Assumes destination demand can absorb transferred units.
    Real branch capacity and demand data should be checked.
    """

    if quantity < 0 or selling_price < 0 or unit_cost < 0:
        raise ValueError("Quantity and prices cannot be negative.")

    if destination_daily_demand < 0:
        raise ValueError("Destination demand cannot be negative.")

    if days_left < 0:
        return {
            "action": "Transportation",
            "feasible": False,
            "estimated_recovery": 0,
            "reason": "Product is already expired."
        }

    feasibility = check_transfer_feasibility(
        days_left=days_left,
        transport_days=transport_days
    )

    if not feasibility["feasible"]:
        return {
            "action": "Transportation",
            "feasible": False,
            "estimated_recovery": 0,
            "reason": feasibility["message"]
        }

    transport = calculate_transport_cost(
        distance_km=distance_km,
        cost_per_km=cost_per_km,
        handling_cost=handling_cost,
        quantity=quantity
    )

    # Assume sales start after the journey.
    selling_days = max(0, days_left - transport_days)

    estimated_units_sold = min(
        quantity,
        int(destination_daily_demand * selling_days)
    )

    revenue = estimated_units_sold * selling_price
    recovery = revenue - transport["total_transport_cost"]

    return {
        "action": "Transportation",
        "feasible": estimated_units_sold > 0,
        "estimated_units_sold": estimated_units_sold,
        "unsold_units": quantity - estimated_units_sold,
        "transport_cost": transport["total_transport_cost"],
        "transport_cost_per_unit": transport["cost_per_unit"],
        "estimated_recovery": round(recovery, 2),
        "reason": (
            "Estimated destination sales minus transport costs."
            if estimated_units_sold > 0
            else "No destination sales are expected before expiry."
        )
    }


def evaluate_distributor_return(
    quantity,
    unit_cost,
    days_left,
    return_accepted=True,
    recovery_rate=0.50,
    handling_cost=0
):
    """
    Estimate recovery from returning stock to the distributor.

    The recovery rate and return acceptance are configurable
    assumptions, not verified distributor policies.
    """

    if quantity < 0 or unit_cost < 0 or handling_cost < 0:
        raise ValueError("Quantity and costs cannot be negative.")

    if days_left < 0:
        return {
            "action": "Distributor Return",
            "feasible": False,
            "estimated_recovery": 0,
            "reason": "Product is already expired."
        }

    if not 0 <= recovery_rate <= 1:
        raise ValueError("Recovery rate must be between 0 and 1.")

    if not return_accepted:
        return {
            "action": "Distributor Return",
            "feasible": False,
            "estimated_recovery": 0,
            "reason": "Distributor return is not permitted."
        }

    gross_recovery = quantity * unit_cost * recovery_rate
    net_recovery = gross_recovery - handling_cost

    return {
        "action": "Distributor Return",
        "feasible": net_recovery > 0,
        "gross_recovery": round(gross_recovery, 2),
        "handling_cost": round(handling_cost, 2),
        "estimated_recovery": round(net_recovery, 2),
        "reason": "Estimated refund minus return handling costs."
    }


def compare_recovery_actions(
    quantity,
    selling_price,
    unit_cost,
    days_left,
    source_daily_demand,
    destination_daily_demand,
    distance_km,
    cost_per_km,
    handling_cost=0,
    transport_days=1,
    return_accepted=True,
    return_recovery_rate=0.50,
    markdown_discount_rate=0.25,
    markdown_demand_uplift=0.25
):
    """Compare only Markdown, Transportation, and Distributor Return."""

    results = [
        evaluate_markdown(
            quantity=quantity,
            selling_price=selling_price,
            unit_cost=unit_cost,
            days_left=days_left,
            expected_daily_demand=source_daily_demand,
            discount_rate=markdown_discount_rate,
            demand_uplift=markdown_demand_uplift
        ),
        evaluate_transport(
            quantity=quantity,
            selling_price=selling_price,
            unit_cost=unit_cost,
            days_left=days_left,
            destination_daily_demand=destination_daily_demand,
            distance_km=distance_km,
            cost_per_km=cost_per_km,
            handling_cost=handling_cost,
            transport_days=transport_days
        ),
        evaluate_distributor_return(
            quantity=quantity,
            unit_cost=unit_cost,
            days_left=days_left,
            return_accepted=return_accepted,
            recovery_rate=return_recovery_rate,
            handling_cost=handling_cost
        )
    ]

    feasible_results = [
        result for result in results if result["feasible"]
    ]

    recommendation = (
        max(feasible_results, key=lambda result: result["estimated_recovery"])
        if feasible_results
        else None
    )

    return {
        "options": results,
        "recommended_action": (
            recommendation["action"] if recommendation else None
        ),
        "recommended_recovery": (
            recommendation["estimated_recovery"] if recommendation else None
        ),
        "message": (
            f"Recommended: {recommendation['action']}"
            if recommendation
            else "No feasible recovery action under the current assumptions."
        )
    }


if __name__ == "__main__":
    comparison = compare_recovery_actions(
        quantity=30,
        selling_price=25,
        unit_cost=18,
        days_left=4,
        source_daily_demand=3,
        destination_daily_demand=8,
        distance_km=5,
        cost_per_km=12,
        handling_cost=30,
        transport_days=1,
        return_accepted=True,
        return_recovery_rate=0.50
    )

    print("RECOVERY ACTION COMPARISON")
    print("=" * 45)

    for option in comparison["options"]:
        print(f"\nAction: {option['action']}")
        print(f"Feasible: {option['feasible']}")
        print(f"Estimated recovery: Rs. {option['estimated_recovery']}")
        print(f"Reason: {option['reason']}")

    print("\n" + "=" * 45)
    print(comparison["message"])
