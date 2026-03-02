# hotel_booking.py
"""
Mock API booking hotel
"""
def _estimate_hotel_price(budget: int, days: int, tier: str = "standard") -> int:
    safe_budget = max(int(budget), 2_000_000)
    nights = max(int(days), 1)

    if safe_budget <= 5_000_000:
        total_price = 1_000_000
    elif safe_budget <= 10_000_000:
        total_price = 3_000_000
    else:
        total_price = int(safe_budget * 0.3)

    multiplier_map = {
        "hemat": 0.88,
        "standard": 1.0,
        "premium": 1.15,
    }
    multiplier = multiplier_map.get(tier, 1.0)
    adjusted_total = int(total_price * multiplier)
    minimum_total = nights * 250_000
    return max(adjusted_total, minimum_total)


def book(destination, date, budget=10_000_000, days=3, tier="standard"):
    price = _estimate_hotel_price(budget=budget, days=days, tier=tier)
    return {
        "hotel": f"Hotel in {destination} on {date}",
        "price": price
    }

# ...existing code...
