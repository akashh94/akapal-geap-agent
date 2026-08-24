"""Read-only order-analysis tools; these tools never submit a trade."""

from app.config.container import brokerage_service


def preview_order_impact(symbol: str, quantity: float, side: str) -> dict:
    """Estimate a mock buy or sell order's portfolio impact without placing it.

    Returns projected position weight with a concentration warning, plus
    affordability context: available_cash / sufficient_funds for buys,
    shares_held / sufficient_shares for sells.
    """
    normalized_side = side.strip().upper()
    if normalized_side not in {"BUY", "SELL"}:
        return {"error": "side must be BUY or SELL"}
    if quantity <= 0:
        return {"error": "quantity must be greater than zero"}
    quote = brokerage_service.get_quote(symbol)
    if quote is None:
        return {"error": f"No mock quote is available for {symbol.upper().strip()}."}

    summary = brokerage_service.get_portfolio_summary()
    holding = next(
        (
            item
            for item in brokerage_service.get_holdings()
            if item.symbol == quote.symbol
        ),
        None,
    )
    current_value = holding.market_value if holding else 0.0
    shares_held = holding.shares if holding else 0
    order_value = round(quote.price * quantity, 2)
    projected_value = (
        current_value + order_value
        if normalized_side == "BUY"
        else max(0.0, current_value - order_value)
    )
    projected_weight = round(projected_value / summary.total_value * 100, 2)

    result = {
        "symbol": quote.symbol,
        "side": normalized_side,
        "quantity": quantity,
        "estimated_price": quote.price,
        "estimated_order_value": order_value,
        "projected_position_weight_percent": projected_weight,
        "concentration_warning": projected_weight > 15,
        "is_mock": True,
        "order_submitted": False,
    }
    if normalized_side == "BUY":
        result["available_cash"] = summary.cash_balance
        result["sufficient_funds"] = order_value <= summary.cash_balance
    else:
        result["shares_held"] = shares_held
        result["sufficient_shares"] = quantity <= shares_held
    return result
