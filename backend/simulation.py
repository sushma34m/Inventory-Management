
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
    seed=42,
    lambda_risk=0.75
):
    rng = np.random.default_rng(seed)

    actions = [
        "Keep",
        "Markdown",
        "Transportation",
        "Distributor Return"
    ]

    recovery_values = {
        action: [] for action in actions
    }

    expired_values = {
        action: [] for action in actions
    }

    feasible_counts = {
        action: 0 for action in actions
    }

    recommendation_counts = {
        action: 0 for action in actions
    }

    for _ in range(simulations):

        source_demand = max(
            0,
            int(rng.poisson(max(0, source_daily_demand)))
        )

        destination_demand = max(
            0,
            int(rng.poisson(max(0, destination_daily_demand)))
        )

        transport_days = int(
            rng.choice([1, 2, 3], p=[0.70, 0.20, 0.10])
        )

        random_cost_per_km = max(
            0,
            rng.normal(cost_per_km, cost_per_km * 0.10)
        )

        random_handling_cost = max(
            0,
            rng.normal(handling_cost, handling_cost * 0.10)
        )

        keep_units = min(
            quantity,
            source_demand * days_left
        )

        keep_recovery = keep_units * selling_price

        recovery_values["Keep"].append(keep_recovery)

        expired_values["Keep"].append(
            quantity - keep_units
        )

        if keep_recovery > 0:
            feasible_counts["Keep"] += 1

        report = compare_recovery_actions(
            quantity=quantity,
            selling_price=selling_price,
            unit_cost=unit_cost,
            days_left=days_left,
            source_daily_demand=source_demand,
            destination_daily_demand=destination_demand,
            distance_km=distance_km,
            cost_per_km=random_cost_per_km,
            handling_cost=random_handling_cost,
            return_accepted=return_accepted,
            return_recovery_rate=return_recovery_rate,
            markdown_discount_rate=markdown_discount_rate,
            markdown_demand_uplift=markdown_demand_uplift,
            transport_days=transport_days
        )

        scenario_recoveries = {
            "Keep": keep_recovery
        }

        for option in report["options"]:

            action = option["action"]

            recovery = (
                option["estimated_recovery"]
                if option["feasible"]
                else 0.0
            )

            recovery_values[action].append(recovery)

            if action == "Distributor Return":
                expired = (
                    0 if option["feasible"] else quantity
                )
            else:
                sold_units = option.get(
                    "estimated_units_sold", 0
                )
                expired = quantity - sold_units

            expired_values[action].append(
                max(0, expired)
            )

            if option["feasible"]:
                feasible_counts[action] += 1

            scenario_recoveries[action] = recovery

        positive_actions = {
            action: recovery
            for action, recovery in scenario_recoveries.items()
            if recovery > 0
        }

        if positive_actions:
            scenario_best = max(
                positive_actions,
                key=positive_actions.get
            )

            recommendation_counts[scenario_best] += 1

    results = {}

    for action in actions:

        recoveries = np.array(
            recovery_values[action],
            dtype=float
        )

        expired = np.array(
            expired_values[action],
            dtype=float
        )

        average_recovery = float(
            np.mean(recoveries)
        )

        downside_std = float(
            np.std(recoveries)
        )

        risk_score = (
            average_recovery
            - lambda_risk * downside_std
        )

        sorted_recoveries = np.sort(recoveries)

        lower_count = max(
            1,
            int(np.ceil(simulations * 0.10))
        )

        cvar_10 = float(
            np.mean(sorted_recoveries[:lower_count])
        )

        results[action] = {
            "average_recovery": round(
                average_recovery, 2
            ),
            "risk_score": round(
                risk_score, 2
            ),
            "downside_risk": round(
                downside_std, 2
            ),
            "cvar_10": round(
                cvar_10, 2
            ),
            "worst_case_recovery": round(
                float(np.min(recoveries)), 2
            ),
            "expected_expired_units": round(
                float(np.mean(expired)), 2
            ),
            "feasibility_rate_percent": round(
                feasible_counts[action]
                / simulations * 100,
                2
            ),
            "recommendation_count": (
                recommendation_counts[action]
            ),
            "recommendation_rate_percent": round(
                recommendation_counts[action]
                / simulations * 100,
                2
            )
        }

    feasible_actions = [
        action
        for action in actions
        if results[action]["feasibility_rate_percent"] > 0
    ]

    if feasible_actions:

        best_action = max(
            feasible_actions,
            key=lambda action: results[action]["risk_score"]
        )

    else:
        best_action = None

    return {
        "simulation_count": simulations,
        "results": results,
        "recommended_action": best_action,
        "recommendation_count": (
            recommendation_counts.get(best_action, 0)
            if best_action else 0
        ),
        "no_feasible_actions": (
            simulations
            if not feasible_actions
            else 0
        )
    }
