# flight_search.py
"""
Mock API pencarian pesawat
"""
def _estimate_flight_price(budget: int, tier: str = "standard") -> int:
    safe_budget = max(int(budget), 2_000_000)

    if safe_budget <= 5_000_000:
        base_price = 1_800_000
    elif safe_budget <= 10_000_000:
        base_price = 3_500_000
    else:
        base_price = int(safe_budget * 0.34)

    multiplier_map = {
        "hemat": 0.9,
        "standard": 1.0,
        "premium": 1.12,
    }
    multiplier = multiplier_map.get(tier, 1.0)
    return int(base_price * multiplier)


def search(destination, date, budget=10_000_000, tier="standard"):
    price = _estimate_flight_price(budget=budget, tier=tier)
    return {
        "flight": f"Flight to {destination} on {date}",
        "price": price
    }

# ...existing code...
