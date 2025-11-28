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
    
    has_breakdown = 'Fails_To_Deliver' in df.columns and 'Fails_To_Receive' in df.columns
    
    if has_breakdown:
        if 'Fails_To_Deliver' in df.columns:
            fig.add_trace(go.Bar(x=df.index, y=df['Fails_To_Deliver'], name='Fails to Deliver', marker_color='#E74C3C'))
        
        if 'Fails_To_Receive' in df.columns:
            fig.add_trace(go.Bar(x=df.index, y=df['Fails_To_Receive'], name='Fails to Receive', marker_color='#F1C40F'))
    elif 'Total_Fails' in df.columns:
        # Fallback to Total Fails if breakdown is missing
        fig.add_trace(go.Bar(x=df.index, y=df['Total_Fails'], name='Total Fails', marker_color='#E67E22'))
        
    fig.update_layout(
        title="Treasury Settlement Fails",
        barmode='stack',
        height=400,
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis_title="Fails ($ Millions)"
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
    
    # Define specific stress columns to plot
    stress_cols = ['Repo_Stress_Index', 'volume_stress', 'rate_stress', 'spread_stress', 'volatility_stress']
    
    # Plot available stress columns
    for col in stress_cols:
        if col in df.columns:
            # Use a thicker line for the main index
            width = 3 if col == 'Repo_Stress_Index' else 1.5
            # Use a distinct color for the main index
            color = '#E74C3C' if col == 'Repo_Stress_Index' else None
            
            fig.add_trace(go.Scatter(
                x=df.index, 
                y=df[col], 
                name=col.replace('_', ' ').title(),
                line=dict(width=width, color=color)
            ))
            
    fig.update_layout(
        title="OFR Financial Stress Index & Components",
        height=400,
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis_title="Stress Level (Index)"
    )
    
    return pio.to_html(fig, full_html=False, include_plotlyjs=False)

# Keep the Matplotlib functions if needed, or remove them. 
# For now, I'll remove them to ensure consistency with the template which expects Plotly HTML strings.
# If the user wants the "Advanced" charts, I should implement them in Plotly too.
# But for now, let's stick to the requested "Expanded" set.
def generate_cumulative_yoy_fiscal_flow_chart(df: pd.DataFrame = None) -> str:
    """
    Generate Cumulative Fiscal Flow YoY Comparison chart.
    Compares current fiscal year cumulative net impulse vs previous fiscal year.
    """
    # Note: This function needs the dataframe passed to it, unlike the placeholder which had no args
    # We will update the call site in generate_html_report.py to pass fiscal_df
    
    if df is None or df.empty:
        return "<div>No data available for Cumulative Fiscal Flow</div>"
        
    # Ensure we have the necessary columns
    if 'Net_Impulse' not in df.columns:
        return "<div>Missing Net_Impulse data</div>"
        
    # Calculate Fiscal Year
    df = df.copy()
    df['Fiscal_Year'] = df.index.map(lambda x: x.year + 1 if x.month >= 10 else x.year)
    
    # Get current and previous fiscal years
    current_fy = df['Fiscal_Year'].max()
    prev_fy = current_fy - 1
    
    # Filter data
    current_df = df[df['Fiscal_Year'] == current_fy].copy()
    prev_df = df[df['Fiscal_Year'] == prev_fy].copy()
    
    # Calculate cumulative sum for each year
    # We need to align them by "Day of Fiscal Year" for comparison
    def get_day_of_fy(date):
        fy_start = pd.Timestamp(year=date.year if date.month >= 10 else date.year - 1, month=10, day=1)
        return (date - fy_start).days
        
    current_df['Day_of_FY'] = current_df.index.map(get_day_of_fy)
    prev_df['Day_of_FY'] = prev_df.index.map(get_day_of_fy)
    
    current_df['Cumulative_Impulse'] = current_df['Net_Impulse'].cumsum()
    prev_df['Cumulative_Impulse'] = prev_df['Net_Impulse'].cumsum()
    
    fig = go.Figure()
    
    # Current FY Line
    fig.add_trace(
        go.Scatter(
            x=current_df['Day_of_FY'],
            y=current_df['Cumulative_Impulse'] / 1000,
            name=f"FY{current_fy} (Current)",
            line=dict(color='#2E86C1', width=3)
        )
    )
    
    # Previous FY Line
    fig.add_trace(
        go.Scatter(
            x=prev_df['Day_of_FY'],
            y=prev_df['Cumulative_Impulse'] / 1000,
            name=f"FY{prev_fy} (Previous)",
            line=dict(color='#95A5A6', width=2, dash='dot')
        )
    )
    
    fig.update_layout(
        title=f"Cumulative Fiscal Impulse (FY{current_fy} vs FY{prev_fy})",
        height=400,
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis_title="Days into Fiscal Year"
    )
    
    fig.update_yaxes(title_text="Cumulative Net Impulse ($B)")
    
    return pio.to_html(fig, full_html=False, include_plotlyjs=False)

def generate_smoothed_yoy_chart(df: pd.DataFrame, category_col: str, title: str) -> str:
    """
    Generate Smoothed YoY % Change chart for a specific category.
    Useful for unemployment benefits or tax receipts analysis.
    """
    if df is None or df.empty or category_col not in df.columns:
        return f"<div>No data available for {title}</div>"
        
    # Calculate YoY Change
    # We need to resample to ensure daily frequency or handle missing dates
    # For simplicity, we'll use a 252-day lag (approx 1 trading year) on the raw data
    # assuming it's mostly daily.
    
    series = df[category_col]
    
    # Calculate 4-week rolling average first to smooth noise
    smoothed = series.rolling(window=20).mean()
    
    # Calculate YoY % change of the smoothed series
    # Using 252 days as proxy for 1 year
    yoy_change = smoothed.pct_change(periods=252) * 100
    
    # Filter to last 2 years for relevance
    start_date = df.index.max() - pd.Timedelta(days=730)
    plot_data = yoy_change[yoy_change.index >= start_date]
    
    fig = go.Figure()
    
    fig.add_trace(
        go.Scatter(
            x=plot_data.index,
            y=plot_data,
            name="YoY % Change",
            line=dict(color='#E67E22', width=2),
            fill='tozeroy',
            fillcolor='rgba(230, 126, 34, 0.1)'
        )
    )
    
    # Add zero line
    fig.add_hline(y=0, line_color="black", line_width=1)
    
    fig.update_layout(
        title=title,
        height=400,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    fig.update_yaxes(title_text="YoY Change (%)")
    
    return pio.to_html(fig, full_html=False, include_plotlyjs=False)