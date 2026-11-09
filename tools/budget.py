"""Tool: calculate_budget. Sums up planned costs by category."""

from .common import CATEGORIES


def calculate_budget(items: list[dict], total_budget: float = 0) -> dict:
    """Sum up planned costs and compare them with the total budget.

    Args:
        items: List of planned costs, each an object like {"category": "food", "cost": 25.5}.
        total_budget: The user's total budget; use 0 if unknown.
    """
    by_category = {}
    total = 0.0

    for item in items:
        try:
            cost = float(item.get("cost") or 0)
        except (TypeError, ValueError):
            return {"error": f"Invalid cost in item: {item}"}
        category = item.get("category", "others")
        if category not in CATEGORIES:
            category = "others"
        by_category[category] = round(by_category.get(category, 0) + cost, 2)
        total += cost

    result = {"total_cost": round(total, 2), "by_category": by_category}
    if total_budget:
        result["total_budget"] = total_budget
        result["remaining"] = round(total_budget - total, 2)
        result["within_budget"] = total <= total_budget
    return result