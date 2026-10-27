
import numpy as np

from backend.recovery_engine import compare_recovery_actions


def run_monte_carlo(
    quantity,
    selling_price,
    unit_cost,
    days_left,
    source_daily_demand,
    destination_daily_demand,
    distance_km,
    cost_per_km,
    handling_cost=0,
    return_accepted=True,
    return_recovery_rate=0.50,
    markdown_discount_rate=0.25,
    markdown_demand_uplift=0.25,
    simulations=1000,
    seed=42
):
    """
    Simulate uncertain daily demand, transport duration,
    and transportation costs.

    Returns average estimated recovery and the frequency
    with which each action is recommended.

    All outputs depend on the model assumptions supplied.
    """

    if quantity < 0 or selling_price < 0 or unit_cost < 0:
        raise ValueError("Quantity and prices cannot be negative.")

    if days_left < 0:
        raise ValueError("Days left cannot be negative.")

    if source_daily_demand < 0 or destination_daily_demand < 0:
        raise ValueError("Daily demand cannot be negative.")

    if distance_km < 0 or cost_per_km < 0 or handling_cost < 0:
        raise ValueError("Transport costs and distance cannot be negative.")

    if simulations < 1:
        raise ValueError("Simulations must be at least 1.")

    rng = np.random.default_rng(seed)

    actions = [
        "Markdown",
        "Transportation",
        "Distributor Return"
    ]

    recovery_values = {action: [] for action in actions}
    recommendation_counts = {action: 0 for action in actions}
    feasible_counts = {action: 0 for action in actions}
    no_action_count = 0

    for _ in range(simulations):

        # Random daily demand around the supplied average.
        simulated_source_demand = int(
            rng.poisson(source_daily_demand)
        )

        simulated_destination_demand = int(
            rng.poisson(destination_daily_demand)
        )

        # Simulate a transport duration of 1, 2, or 3 days.
        simulated_transport_days = int(
            rng.choice([1, 2, 3], p=[0.70, 0.20, 0.10])
        )

        # Simulate transport rates with moderate variation.
        simulated_cost_per_km = max(
            0.0,
            float(rng.normal(cost_per_km, cost_per_km * 0.10))
        )

        simulated_handling_cost = max(
            0.0,
            float(rng.normal(
                handling_cost,
                max(1.0, handling_cost * 0.10)
            ))
        )

        results = compare_recovery_actions(
            quantity=quantity,
            selling_price=selling_price,
            unit_cost=unit_cost,
            days_left=days_left,
            source_daily_demand=simulated_source_demand,
            destination_daily_demand=simulated_destination_demand,
            distance_km=distance_km,
            cost_per_km=simulated_cost_per_km,
            handling_cost=simulated_handling_cost,
            transport_days=simulated_transport_days,
            return_accepted=return_accepted,
            return_recovery_rate=return_recovery_rate,
            markdown_discount_rate=markdown_discount_rate,
            markdown_demand_uplift=markdown_demand_uplift
        )

        for result in results["options"]:
            action = result["action"]

            if result["feasible"]:
                feasible_counts[action] += 1
                recovery_values[action].append(
                    result["estimated_recovery"]
                )

        if results["recommended_action"] is None:
            no_action_count += 1
        else:
            recommendation_counts[
                results["recommended_action"]
            ] += 1

    summary = {}

    for action in actions:
        values = recovery_values[action]

        summary[action] = {
            "average_recovery_when_feasible": (
                round(float(np.mean(values)), 2)
                if values else None
            ),
            "feasible_scenarios": feasible_counts[action],
            "feasibility_rate_percent": round(
                feasible_counts[action] / simulations * 100, 2
            ),
            "recommendation_count": recommendation_counts[action],
            "recommendation_rate_percent": round(
                recommendation_counts[action] / simulations * 100, 2
            )
        }

    # Most frequently recommended action across the simulations.
    best_action = (
        max(recommendation_counts, key=recommendation_counts.get)
        if sum(recommendation_counts.values()) > 0
        else None
    )

    return {
        "simulation_count": simulations,
        "results": summary,
        "recommended_action": best_action,
        "recommendation_count": recommendation_counts.get(best_action, 0)
        if best_action else 0,
        "no_feasible_action_scenarios": no_action_count,
        "no_feasible_action_rate_percent": round(
            no_action_count / simulations * 100, 2
        )
    }


if __name__ == "__main__":
    report = run_monte_carlo(
        quantity=30,
        selling_price=25,
        unit_cost=18,
        days_left=4,
        source_daily_demand=3,
        destination_daily_demand=8,
        distance_km=5,
        cost_per_km=12,
        handling_cost=30,
        simulations=1000,
        seed=42
    )

    print("MONTE CARLO RECOVERY SIMULATION")
    print("=" * 50)
    print(f"Scenarios simulated: {report['simulation_count']}")

    for action, values in report["results"].items():
        print(f"\nAction: {action}")
        print(
            "Average recovery when feasible:",
            values["average_recovery_when_feasible"]
        )
        print(
            "Feasibility rate:",
            f"{values['feasibility_rate_percent']}%"
        )
        print(
            "Recommendation rate:",
            f"{values['recommendation_rate_percent']}%"
        )

    print("\n" + "=" * 50)
    print("Most frequently recommended:", report["recommended_action"])
    print("Scenarios with no feasible action:",
          report["no_feasible_action_scenarios"])
