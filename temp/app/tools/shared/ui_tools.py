"""No-op signaling tools: calling one tells the client which rich widget to render.

These carry no business data -- the client already has everything it needs
(BrokerageData, state.aiSettings) to build the widget locally from real state.
The tool call itself is just a structured, reliable "show widget X now" flag,
which the model emits via normal function-calling rather than an instruction
to type an exact literal string in free text.
"""


def show_rebalance_widget() -> dict:
    """Signal the client to render the interactive rebalance ticket widget.

    Call this immediately after recommending a specific rebalance action
    (e.g. trimming a concentrated position into a diversified asset), in
    addition to your normal text explanation.
    """
    return {"widget": "REBALANCE_FORM"}
