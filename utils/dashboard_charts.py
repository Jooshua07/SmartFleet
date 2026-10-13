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
                "Type": "Recorded Revenue",
                "Amount": _to_float(item.get("revenue")),
            }
        )
        rows.append(
            {
                "Bus": item["registration_number"],
                "Type": "Attributed Operating Costs",
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
                    domain=["Recorded Revenue", "Attributed Operating Costs"],
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


def build_business_performance_chart_data(series: list[dict]) -> pd.DataFrame:
    rows = []
    for item in series:
        label = item["period_start"]
        if item["period_end"] != item["period_start"]:
            label = f"{item['period_start'].strftime('%d %b')} - {item['period_end'].strftime('%d %b')}"
        rows.extend(
            [
                {
                    "Date": item["period_start"],
                    "Period": label,
                    "Type": "Revenue",
                    "Amount": _to_float(item["revenue"]),
                },
                {
                    "Date": item["period_start"],
                    "Period": label,
                    "Type": "Operating Expenses",
                    "Amount": _to_float(item["operating_expenses"]),
                },
                {
                    "Date": item["period_start"],
                    "Period": label,
                    "Type": "Recorded Operating Profit/Loss",
                    "Amount": _to_float(item["net_profit_loss"]),
                },
            ]
        )
    return pd.DataFrame(rows, columns=["Date", "Period", "Type", "Amount"])


def build_business_performance_chart(chart_data: pd.DataFrame) -> alt.LayerChart:
    if chart_data.empty:
        return alt.Chart(chart_data).mark_line()
    min_amount = min(0, float(chart_data["Amount"].min()))
    max_amount = max(0, float(chart_data["Amount"].max()))
    padding = max((max_amount - min_amount) * 0.08, 100)
    y_domain = [min_amount - padding, max_amount + padding]

    base = alt.Chart(chart_data).encode(
        x=alt.X("Date:T", title="Date", axis=alt.Axis(format="%d %b")),
        y=alt.Y(
            "Amount:Q",
            title="ZMW",
            scale=alt.Scale(domain=y_domain, nice=True),
            axis=alt.Axis(format=",.0f"),
        ),
        color=alt.Color(
            "Type:N",
            title="",
            scale=alt.Scale(
                domain=["Revenue", "Operating Expenses", "Recorded Operating Profit/Loss"],
                range=["#2563eb", "#dc2626", "#16a34a"],
            ),
        ),
    )
    lines = base.mark_line(point=True, strokeWidth=3).encode(
        tooltip=[
            alt.Tooltip("Period:N", title="Period"),
            alt.Tooltip("Type:N", title="Type"),
            alt.Tooltip("Amount:Q", title="Amount (K)", format=",.0f"),
        ]
    )
    zero = (
        alt.Chart(pd.DataFrame({"Amount": [0]}))
        .mark_rule(strokeDash=[6, 4], color="#6b7280")
        .encode(y="Amount:Q")
    )
    return (zero + lines).properties(height=300)
