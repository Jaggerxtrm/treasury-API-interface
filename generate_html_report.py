import os
import sys
import pandas as pd
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from typing import Dict, Tuple

# Add module paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'fiscal'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'fed'))

# Import existing data loaders
from generate_desk_report import load_all_data, extract_key_metrics
from dashboard_utils.charts import (
    generate_net_liquidity_chart,
    generate_fiscal_impulse_chart,
    generate_stress_chart,
    generate_treasury_fails_chart,
    generate_rates_chart,
    generate_qt_pace_chart,
    generate_ofr_stress_chart,
    generate_cumulative_yoy_fiscal_flow_chart,
    generate_smoothed_yoy_chart
)

# Import new table generator
from dashboard_utils.tables import create_multi_year_summary_table

def generate_html_table(df: pd.DataFrame, title: str) -> str:
    """
    Generate a styled HTML table from a DataFrame (last 30 rows).
    """
    if df.empty:
        return f"<p>No data available for {title}</p>"
    
    # Take last 30 rows and reverse order (newest first)
    table_df = df.tail(30).iloc[::-1]
    
    # Format numeric columns
    for col in table_df.select_dtypes(include=['float', 'int']).columns:
        # Check magnitude to decide formatting
        if table_df[col].abs().max() > 1000:
            table_df[col] = table_df[col].apply(lambda x: f"{x:,.0f}" if pd.notnull(x) else "-")
        else:
            table_df[col] = table_df[col].apply(lambda x: f"{x:,.2f}" if pd.notnull(x) else "-")
            
    # Format date index
    table_df.index = table_df.index.strftime('%Y-%m-%d')
    table_df.index.name = 'Date'
    
    return table_df.to_html(classes="table table-striped table-hover", border=0)

def filter_data_for_report(df: pd.DataFrame, start_date: str = '2023-10-01') -> pd.DataFrame:
    """
    Filter DataFrame to include data from the start of the previous fiscal year (default Oct 1, 2023).
    """
    if df.empty:
        return df
    return df[df.index >= start_date]

def generate_html_report():
    print("Starting HTML Report Generation...")
    
    # 1. Load Data from DuckDB
    # 1. Load Data from DuckDB
    fiscal_df, fed_df, ofr_df, metadata = load_all_data()
    
    # GLOBAL FIX: Remove index names to prevent "record_date" artifact in charts
    fiscal_df.index.name = None
    fed_df.index.name = None
    if not ofr_df.empty:
        ofr_df.index.name = None
    
    # 2. Extract Metrics (for summary boxes)
    from generate_desk_report import calculate_integrated_flows
    flows_df = calculate_integrated_flows(fiscal_df, fed_df)
    metrics = extract_key_metrics(fiscal_df, fed_df, flows_df)
    
    # 3. Filter Data for Charts
    chart_start_date = '2023-10-01'
    fiscal_chart_df = filter_data_for_report(fiscal_df, chart_start_date)
    fed_chart_df = filter_data_for_report(fed_df, chart_start_date)
    ofr_chart_df = filter_data_for_report(ofr_df, chart_start_date)
    
    # 4. Generate Standard Charts
    print("Generating interactive charts...")
    charts = {
        'net_liquidity': generate_net_liquidity_chart(fed_chart_df),
        'fiscal_impulse': generate_fiscal_impulse_chart(fiscal_chart_df),
        'stress': generate_stress_chart(fed_chart_df),
        'treasury_fails': generate_treasury_fails_chart(fed_chart_df),
        'rates': generate_rates_chart(fed_chart_df),
        'qt_pace': generate_qt_pace_chart(fed_chart_df),
        'ofr_stress': generate_ofr_stress_chart(ofr_chart_df),
        # New charts inspired by the PDF
        'cumulative_flow': generate_cumulative_yoy_fiscal_flow_chart(fiscal_df),
        'unemployment_yoy': generate_smoothed_yoy_chart(fiscal_df, 'Cat_Unemployment', 'Unemployment Benefits (Smoothed YoY % Change)')
    }
    
    # 5. Generate Comprehensive Charts (Chart Dump)
    print("Generating comprehensive chart dump...")
    from dashboard_utils.charts import generate_generic_chart, generate_generic_table
    
    comprehensive_config = {
        'Fiscal Analysis': {
            'df': fiscal_df,
            'charts': [
                {'title': 'Fiscal Impulse Components', 'cols': ['Total_Spending', 'Total_Taxes', 'Net_Impulse'], 'y_axis': 'Millions USD'},
                {'title': 'Moving Averages', 'cols': ['MA20_Net_Impulse', 'MA5_Net_Impulse'], 'y_axis': 'Millions USD'},
                {'title': 'TGA Balance', 'cols': ['TGA_Balance'], 'y_axis': 'Millions USD'},
                {'title': 'Spending Categories', 'cols': ['Defense', 'Medicare', 'Social_Security', 'Interest_on_Debt', 'Education', 'Health', 'Veterans'], 'y_axis': 'Millions USD'},
                {'title': 'Tax Categories', 'cols': ['Withheld_Income', 'Individual_Income_Tax', 'Corporate_Income_Tax', 'Excise_Taxes'], 'y_axis': 'Millions USD'}
            ]
        },
        'Fed Balance Sheet': {
            'df': fed_df,
            'charts': [
                {'title': 'Fed Assets Breakdown', 'cols': ['Fed_Total_Assets', 'Fed_Treasury_Holdings', 'Fed_MBS_Holdings'], 'y_axis': 'Millions USD'},
                {'title': 'Liabilities Breakdown', 'cols': ['RRP_Balance', 'TGA_Balance', 'Reserve_Balances'], 'y_axis': 'Millions USD'},
                {'title': 'Liquidity Injection/Drain', 'cols': ['Repo_Ops_Balance', 'RRP_Balance'], 'y_axis': 'Billions USD'},
                {'title': 'QT Pace', 'cols': ['QT_Pace_Assets_Weekly', 'QT_Pace_Treasury_Weekly', 'MBS_Runoff_Weekly'], 'y_axis': 'Millions USD'}
            ]
        },
        'Market Plumbing & Rates': {
            'df': fed_df,
            'charts': [
                {'title': 'Key Rates', 'cols': ['SOFR_Rate', 'IORB_Rate', 'EFFR_Rate', 'TGCR_Rate', 'BGCR_Rate'], 'y_axis': 'Percent'},
                {'title': 'Spreads', 'cols': ['Spread_SOFR_IORB', 'Spread_EFFR_IORB'], 'y_axis': 'Basis Points'},
                {'title': 'Treasury Yields', 'cols': ['UST_2Y', 'UST_5Y', 'UST_10Y', 'UST_30Y'], 'y_axis': 'Percent'},
                {'title': 'Yield Curve', 'cols': ['Curve_10Y2Y', 'Curve_5s30s'], 'y_axis': 'Basis Points'},
                {'title': 'Breakevens (Inflation Exp)', 'cols': ['Breakeven_10Y', 'Breakeven_5Y'], 'y_axis': 'Percent'},
                {'title': 'Settlement Fails', 'cols': ['Total_Fails', 'Fails_To_Deliver', 'Fails_To_Receive'], 'y_axis': 'Millions USD'}
            ]
        }
    }
    
    comprehensive_data = {}
    
    for category, config in comprehensive_config.items():
        df = config['df']
        # Filter for charts (last 2 years)
        chart_df = filter_data_for_report(df, chart_start_date)
        
        category_content = []
        for item in config['charts']:
            # Generate Chart
            chart_html = generate_generic_chart(chart_df, item['cols'], item['title'], item['y_axis'])
            
            # Generate Table (last 30 days)
            table_html = generate_generic_table(df, item['cols'], f"{item['title']} (Recent Data)")
            
            category_content.append({
                'title': item['title'],
                'chart': chart_html,
                'table': table_html
            })
            
        comprehensive_data[category] = category_content

    # 6. Generate Tables using the new multi-year function
    print("Generating multi-year data tables...")
    tables = {
        'fiscal_impulse_summary': create_multi_year_summary_table('Net_Impulse', 'Fiscal Impulse Summary'),
        'tax_receipts_summary': create_multi_year_summary_table('Total_Taxes', 'Tax Receipts Summary'),
        'unemployment_summary': create_multi_year_summary_table('Cat_Unemployment', 'Unemployment Benefits Summary'),
        # Add last 30 days data tables
        'fiscal': generate_html_table(fiscal_df[['Net_Impulse', 'MA20_Net_Impulse', 'TGA_Balance', 'Total_Taxes']], "Fiscal Data"),
        'fed': generate_html_table(fed_df[['Net_Liquidity', 'Fed_Total_Assets', 'RRP_Balance', 'TGA_Balance']], "Fed Liquidity"),
        'plumbing': generate_html_table(fed_df[['SOFR_Rate', 'IORB_Rate', 'Spread_SOFR_IORB', 'Repo_Ops_Balance']], "Market Plumbing")
    }
    
    # 7. Render Template
    print("Rendering HTML template...")
    env = Environment(loader=FileSystemLoader('templates'))
    template = env.get_template('dashboard.html')
    
    # Dynamic Executive Summary
    impulse_pct = metrics['fiscal'].get('impulse_pct_gdp', 0)
    net_liq = metrics['monetary'].get('net_liquidity', 0) / 1_000_000_000_000
    stress_idx = metrics['regime'].get('stress_index', 0)
    
    executive_summary = f"""
    <p><strong>Automated Analysis:</strong></p>
    <ul>
        <li><strong>Fiscal Stance:</strong> Weekly impulse is running at {impulse_pct:.2f}% of GDP. 
            {'This is above target, indicating expansionary pressure.' if impulse_pct > 0.74 else 'This is below target, indicating contractionary pressure.' if impulse_pct < 0.54 else 'This is roughly on target.'}</li>
        <li><strong>Liquidity Conditions:</strong> Net Liquidity stands at ${net_liq:.2f}T. 
            {'RRP drawdowns are supporting liquidity despite QT.' if metrics['monetary'].get('rrp_change', 0) < 0 else 'RRP balances are stable.'}</li>
        <li><strong>Market Stress:</strong> The Liquidity Stress Index is at {stress_idx:.0f}/100. 
            {'Conditions are normal.' if stress_idx < 50 else 'Conditions are elevated, monitor SOFR spreads.'}</li>
    </ul>
    <p><em>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}</em></p>
    """
    
    html_output = template.render(
        report_date=datetime.now().strftime('%Y-%m-%d'),
        report_time=datetime.now().strftime('%H:%M:%S'),
        version="1.2.0 (Comprehensive)",
        metrics=metrics,
        charts=charts,
        tables=tables,
        executive_summary=executive_summary,
        comprehensive_data=comprehensive_data  # Pass new data
    )
    
    # 8. Save Output
    output_dir = 'outputs'
    os.makedirs(output_dir, exist_ok=True)
    filename = f"dashboard_{datetime.now().strftime('%Y-%m-%d')}.html"
    output_path = os.path.join(output_dir, filename)
    
    with open(output_path, 'w') as f:
        f.write(html_output)
        
    print(f"✅ Report generated successfully: {output_path}")

if __name__ == "__main__":
    generate_html_report()
