
from backend.simulation import run_monte_carlo

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
    simulations=1000
)

print("\nMONTE CARLO SIMULATION")
print("=" * 40)

for action, result in report["results"].items():
    print(f"\nAction: {action}")
    print("Average Recovery:", result["average_recovery"])
    print("Risk Score:", result["risk_score"])
    print("Worst Recovery:", result["worst_case_recovery"])
    print("Expected Expired Units:", result["expected_expired_units"])

print("\nRecommended Action:", report["recommended_action"])
