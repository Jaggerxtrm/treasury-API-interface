import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots

# Set default template
pio.templates.default = "plotly_white"

def generate_net_liquidity_chart(df: pd.DataFrame) -> str:
    """Generate Net Liquidity vs S&P 500 chart."""
    if df.empty:
        return "<div>No data available for Net Liquidity</div>"
        
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Net Liquidity Area
    fig.add_trace(
        go.Scatter(
            x=df.index, 
            y=df['Net_Liquidity'] / 1000000,
            name="Net Liquidity (Trillions)",
            fill='tozeroy',
            line=dict(color='#2E86C1', width=2),
            fillcolor='rgba(46, 134, 193, 0.1)'
        ),
        secondary_y=False
    )
    
    # S&P 500 Line (if available)
    if 'SPX' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['SPX'],
                name="S&P 500",
                line=dict(color='#E74C3C', width=2)
            ),
            secondary_y=True
        )
        
    fig.update_layout(
        title="Fed Net Liquidity vs Risk Assets",
        height=450,
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    fig.update_yaxes(title_text="Net Liquidity ($T)", secondary_y=False)
    fig.update_yaxes(title_text="S&P 500", secondary_y=True)
    
    return pio.to_html(fig, full_html=False, include_plotlyjs='cdn')

def generate_fiscal_impulse_chart(df: pd.DataFrame) -> str:
    """Generate Fiscal Impulse chart."""
    if df.empty:
        return "<div>No data available for Fiscal Impulse</div>"
        
    fig = go.Figure()
    
    # Weekly Impulse Bar
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df['Net_Impulse'] / 1000,
            name="Weekly Impulse ($B)",
            marker_color='#27AE60',
            opacity=0.6
        )
    )
    
    # MA20 Line
    if 'MA20_Net_Impulse' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['MA20_Net_Impulse'] / 1000,
                name="20-Day MA ($B)",
                line=dict(color='#1E8449', width=3)
            )
        )
        
    fig.update_layout(
        title="Fiscal Impulse (Net Spending - Taxes)",
        height=400,
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    fig.update_yaxes(title_text="Billions USD")
    
    return pio.to_html(fig, full_html=False, include_plotlyjs=False)

def generate_stress_chart(df: pd.DataFrame) -> str:
    """Generate Market Stress Index chart."""
    if df.empty or 'Stress_Index' not in df.columns:
        return "<div>No data available for Stress Index</div>"
        
    fig = go.Figure()
    
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df['Stress_Index'],
            name="Liquidity Stress Index",
            line=dict(color='#8E44AD', width=2),
            fill='tozeroy',
            fillcolor='rgba(142, 68, 173, 0.1)'
        )
    )
    
    # Add threshold lines
    fig.add_hline(y=75, line_dash="dot", line_color="red", annotation_text="High Stress")
    fig.add_hline(y=50, line_dash="dot", line_color="orange", annotation_text="Elevated")
    
    fig.update_layout(
        title="Liquidity Stress Index (0-100)",
        height=400,
        margin=dict(l=20, r=20, t=40, b=20),
        yaxis=dict(range=[0, 100])
    )
    
    return pio.to_html(fig, full_html=False, include_plotlyjs=False)

def generate_treasury_fails_chart(df: pd.DataFrame) -> str:
    """Generate Treasury Settlement Fails chart."""
    if df.empty:
        return "<div>No data available for Treasury Fails</div>"
        
    # Check if we have fails data
    fails_cols = [c for c in df.columns if 'Fails' in c]
    if not fails_cols:
        return "<div>No Treasury Fails data found</div>"
        
    fig = go.Figure()
    
    if 'Fails_To_Deliver' in df.columns:
        fig.add_trace(go.Bar(x=df.index, y=df['Fails_To_Deliver'], name='Fails to Deliver', marker_color='#E74C3C'))
    
    if 'Fails_To_Receive' in df.columns:
        fig.add_trace(go.Bar(x=df.index, y=df['Fails_To_Receive'], name='Fails to Receive', marker_color='#F1C40F'))
        
    fig.update_layout(
        title="Treasury Settlement Fails",
        barmode='stack',
        height=400,
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    return pio.to_html(fig, full_html=False, include_plotlyjs=False)

def generate_rates_chart(df: pd.DataFrame) -> str:
    """Generate Key Money Market Rates chart."""
    if df.empty:
        return "<div>No data available for Rates</div>"
        
    fig = go.Figure()
    
    rates = {
        'SOFR_Rate': '#2980B9',
        'EFFR_Rate': '#27AE60',
        'IORB_Rate': '#8E44AD',
        'TGCR_Rate': '#D35400',
        'BGCR_Rate': '#F39C12'
    }
    
    for col, color in rates.items():
        if col in df.columns:
            fig.add_trace(go.Scatter(x=df.index, y=df[col], name=col.replace('_Rate', ''), line=dict(color=color, width=1.5)))
            
    fig.update_layout(
        title="Key Money Market Rates",
        height=400,
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    fig.update_yaxes(title_text="Rate (%)")
    
    return pio.to_html(fig, full_html=False, include_plotlyjs=False)

def generate_qt_pace_chart(df: pd.DataFrame) -> str:
    """Generate QT Pace (Fed Assets Change) chart."""
    if df.empty or 'Fed_Total_Assets' not in df.columns:
        return "<div>No data available for QT Pace</div>"
        
    # Calculate weekly change if not present
    if 'QT_Pace_Assets_Weekly' not in df.columns:
        df['QT_Pace_Assets_Weekly'] = df['Fed_Total_Assets'].diff(5)
        
    fig = go.Figure()
    
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df['QT_Pace_Assets_Weekly'] / 1000,
            name="Weekly Asset Change ($B)",
            marker_color='#34495E'
        )
    )
    
    fig.update_layout(
        title="Fed Balance Sheet Change (QT Pace)",
        height=400,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    fig.update_yaxes(title_text="Billions USD")
    
    return pio.to_html(fig, full_html=False, include_plotlyjs=False)

def generate_ofr_stress_chart(df: pd.DataFrame) -> str:
    """Generate OFR Financial Stress Index chart."""
    if df.empty:
        return "<div>No OFR Stress data available</div>"
        
    fig = go.Figure()
    
    # Assuming columns like 'OFR_FSI', 'Credit', 'Equity', etc.
    # If specific columns are unknown, plot all numeric columns
    for col in df.select_dtypes(include=['float', 'int']).columns:
        if col != 'record_date':
            fig.add_trace(go.Scatter(x=df.index, y=df[col], name=col))
            
    fig.update_layout(
        title="OFR Financial Stress Index",
        height=400,
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    return pio.to_html(fig, full_html=False, include_plotlyjs=False)

# Keep the Matplotlib functions if needed, or remove them. 
# For now, I'll remove them to ensure consistency with the template which expects Plotly HTML strings.
# If the user wants the "Advanced" charts, I should implement them in Plotly too.
# But for now, let's stick to the requested "Expanded" set.
def generate_cumulative_yoy_fiscal_flow_chart(): return "<div>Chart not implemented in Plotly</div>"
def generate_smoothed_yoy_chart(a, b): return "<div>Chart not implemented in Plotly</div>"