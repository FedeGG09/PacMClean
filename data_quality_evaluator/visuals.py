from __future__ import annotations
import pandas as pd
import plotly.express as px

def make_plotly_figure(df: pd.DataFrame, chart_type: str = "auto", x: str | None = None, y: str | None = None, color: str | None = None):
    if df is None or df.empty:
        return px.scatter(title="Sin datos")
    cols = df.columns.tolist()
    if chart_type == "auto":
        num_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c]) or (str(df[c].dtype) == "object" and pd.to_numeric(df[c], errors="coerce").notna().mean() > 0.8)]
        date_cols = [c for c in cols if pd.to_datetime(df[c], errors="coerce", format="mixed", dayfirst=True).notna().mean() > 0.6]
        if len(num_cols) >= 2:
            x = x or num_cols[0]
            y = y or num_cols[1]
            return px.scatter(df, x=x, y=y, color=color if color in cols else None, title=f"{x} vs {y}")
        if len(num_cols) == 1:
            x = x or num_cols[0]
            return px.histogram(df, x=x, color=color if color in cols else None, title=f"Distribución de {x}")
        if date_cols:
            x = x or date_cols[0]
            tmp = df.copy()
            tmp[x] = pd.to_datetime(tmp[x], errors="coerce", format="mixed", dayfirst=True)
            return px.histogram(tmp, x=x, color=color if color in cols else None, title=f"Serie temporal de {x}")
        cat = cols[0]
        vc = df[cat].astype(str).value_counts().head(20).reset_index()
        vc.columns = [cat, "count"]
        return px.bar(vc, x=cat, y="count", title=f"Frecuencia de {cat}")
    if chart_type == "histogram" and x in cols:
        return px.histogram(df, x=x, color=color if color in cols else None, title=f"Histograma de {x}")
    if chart_type == "box" and x in cols:
        return px.box(df, y=x, color=color if color in cols else None, title=f"Boxplot de {x}")
    if chart_type == "bar" and x in cols:
        vc = df[x].astype(str).value_counts().head(30).reset_index()
        vc.columns = [x, "count"]
        return px.bar(vc, x=x, y="count", title=f"Frecuencia de {x}")
    if chart_type == "scatter" and x in cols and y in cols:
        return px.scatter(df, x=x, y=y, color=color if color in cols else None, title=f"{x} vs {y}")
    if chart_type == "line" and x in cols and y in cols:
        return px.line(df, x=x, y=y, color=color if color in cols else None, title=f"{y} a través de {x}")
    return px.scatter(title="Configuración de gráfico inválida")
