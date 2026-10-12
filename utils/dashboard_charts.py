from __future__ import annotations

from decimal import Decimal

import altair as alt
import pandas as pd


def _to_float(value) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def build_bus_performance_chart_data(performance: list[dict]) -> pd.DataFrame:
    rows = []
    for item in performance:
        rows.append(
            {
                "Bus": item["registration_number"],
                "Type": "Revenue",
                "Amount": _to_float(item.get("revenue")),
            }
        )
        rows.append(
            {
                "Bus": item["registration_number"],
                "Type": "Expenses",
                "Amount": _to_float(item.get("expenses")),
            }
        )
    return pd.DataFrame(rows, columns=["Bus", "Type", "Amount"])


def build_bus_performance_chart(chart_data: pd.DataFrame) -> alt.Chart:
    return (
        alt.Chart(chart_data)
        .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
        .encode(
            x=alt.X("Bus:N", title="Bus", axis=alt.Axis(labelAngle=0)),
            xOffset=alt.XOffset("Type:N"),
            y=alt.Y(
                "Amount:Q",
                title="ZMW",
                scale=alt.Scale(domainMin=0),
                axis=alt.Axis(format=",.0f"),
            ),
            color=alt.Color(
                "Type:N",
                title="",
                scale=alt.Scale(
                    domain=["Revenue", "Expenses"],
                    range=["#2563eb", "#dc2626"],
                ),
            ),
            tooltip=[
                alt.Tooltip("Bus:N", title="Bus"),
                alt.Tooltip("Type:N", title="Type"),
                alt.Tooltip("Amount:Q", title="Amount", format=",.0f"),
            ],
        )
        .properties(height=260)
    )
