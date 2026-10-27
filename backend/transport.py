
from math import ceil


def calculate_transport_cost(
    distance_km,
    cost_per_km,
    handling_cost=0,
    quantity=1
):
    """
    Calculate the estimated cost of transferring inventory.

    distance_km: one-way distance in kilometres
    cost_per_km: vehicle cost per kilometre
    handling_cost: total loading and handling cost
    quantity: number of units being transferred
    """

    if distance_km < 0:
        raise ValueError("Distance cannot be negative.")

    if cost_per_km < 0:
        raise ValueError("Cost per kilometre cannot be negative.")

    if handling_cost < 0:
        raise ValueError("Handling cost cannot be negative.")

    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero.")

    travel_cost = distance_km * cost_per_km
    total_cost = travel_cost + handling_cost
    cost_per_unit = total_cost / quantity

    return {
        "distance_km": distance_km,
        "travel_cost": round(travel_cost, 2),
        "handling_cost": round(handling_cost, 2),
        "total_transport_cost": round(total_cost, 2),
        "quantity": quantity,
        "cost_per_unit": round(cost_per_unit, 2)
    }


def check_transfer_feasibility(days_left, transport_days=1):
    """
    Check whether stock has time to reach the destination.

    This is a basic screening rule, not a guarantee
    that the product will remain safe or sellable.
    """

    if days_left < 0:
        return {
            "feasible": False,
            "message": "Product is already expired."
        }

    if transport_days < 0:
        raise ValueError("Transport days cannot be negative.")

    if days_left <= transport_days:
        return {
            "feasible": False,
            "message": "Insufficient shelf life for the planned journey."
        }

    return {
        "feasible": True,
        "message": "Sufficient time under the configured transport estimate."
    }


if __name__ == "__main__":
    result = calculate_transport_cost(
        distance_km=5,
        cost_per_km=12,
        handling_cost=30,
        quantity=20
    )

    print("TRANSPORT COST TEST")
    print("-------------------")
    print(f"Distance: {result['distance_km']} km")
    print(f"Travel cost: Rs. {result['travel_cost']}")
    print(f"Handling cost: Rs. {result['handling_cost']}")
    print(f"Total transport cost: Rs. {result['total_transport_cost']}")
    print(f"Quantity: {result['quantity']} units")
    print(f"Transport cost per unit: Rs. {result['cost_per_unit']}")

    print("\nSHELF-LIFE TEST")
    print("----------------")
    print(check_transfer_feasibility(days_left=5, transport_days=1))
