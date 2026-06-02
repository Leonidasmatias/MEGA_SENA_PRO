from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.estatisticas import frequencia_dezenas


def grafico_frequencia(df: pd.DataFrame) -> go.Figure:
    frequencia = frequencia_dezenas(df).sort_values("Dezena")
    figura = px.bar(
        frequencia,
        x="Dezena formatada",
        y="Frequência",
        title="Frequência histórica por dezena",
        labels={"Dezena formatada": "Dezena"},
        color_discrete_sequence=["#0f8f4f"],
    )
    figura.update_layout(
        margin={"l": 20, "r": 20, "t": 60, "b": 20},
        xaxis_tickangle=0,
    )
    return figura
