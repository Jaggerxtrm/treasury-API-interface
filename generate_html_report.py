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
    fiscal_df, fed_df, ofr_df, metadata = load_all_data()
    
    # 2. Extract Metrics (for summary boxes)
    from generate_desk_report import calculate_integrated_flows
    flows_df = calculate_integrated_flows(fiscal_df, fed_df)
    metrics = extract_key_metrics(fiscal_df, fed_df, flows_df)
    
    # 3. Filter Data for Charts
    chart_start_date = '2023-10-01'
    fiscal_chart_df = filter_data_for_report(fiscal_df, chart_start_date)
    fed_chart_df = filter_data_for_report(fed_df, chart_start_date)
    ofr_chart_df = filter_data_for_report(ofr_df, chart_start_date)
    
    # 4. Generate Charts
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
        'cumulative_flow': generate_cumulative_yoy_fiscal_flow_chart(),
        'unemployment_yoy': generate_smoothed_yoy_chart('Cat_Unemployment', 'Unemployment Benefits (Smoothed YoY % Change)')
    }
    
    # 5. Generate Tables using the new multi-year function
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
    
    # 6. Render Template
    print("Rendering HTML template...")
    env = Environment(loader=FileSystemLoader('templates'))
    template = env.get_template('dashboard.html')
    
    # Placeholder for AI summary until integrated
    executive_summary = """
    <p><strong>Automated Analysis:</strong></p>
    <ul>
        <li>Net Liquidity remains stable with recent TGA fluctuations offset by RRP drawdowns.</li>
        <li>Fiscal impulse is tracking slightly above target, indicating continued support.</li>
        <li>Money market stress indicators (SOFR-IORB) remain within normal ranges.</li>
    </ul>
    <p><em>(AI integration pending...)</em></p>
    """
    
    html_output = template.render(
        report_date=datetime.now().strftime('%Y-%m-%d'),
        report_time=datetime.now().strftime('%H:%M:%S'),
        version="1.1.0",
        metrics=metrics,
        charts=charts,
        tables=tables,
        executive_summary=executive_summary
    )
    
    # 7. Save Output
    output_dir = 'outputs'
    os.makedirs(output_dir, exist_ok=True)
    filename = f"dashboard_{datetime.now().strftime('%Y-%m-%d')}.html"
    output_path = os.path.join(output_dir, filename)
    
    with open(output_path, 'w') as f:
        f.write(html_output)
        
    print(f"✅ Report generated successfully: {output_path}")

if __name__ == "__main__":
    generate_html_report()
