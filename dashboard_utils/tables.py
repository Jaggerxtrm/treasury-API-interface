
import duckdb
import pandas as pd
from typing import List

DB_PATH = 'database/treasury_data.duckdb'

def create_multi_year_summary_table(
    metric_name: str, 
    title: str,
    years_to_show: int = 5,
    is_currency: bool = True
) -> str:
    """
    Queries weekly data for a specific metric, creates a multi-year pivot table,
    adds analytical columns (YoY, 4w MA), and returns a styled HTML table.
    """
    try:
        con = duckdb.connect(DB_PATH, read_only=True)
        
        # Query weekly data for the specified metric, including fiscal week number
        query = f"""
        SELECT 
            EXTRACT(YEAR FROM week_start_date) as year,
            Fiscal_Week_Num as week,
            SUM({metric_name}) as value
        FROM fiscal_weekly_metrics
        WHERE Fiscal_Week_Num IS NOT NULL
        GROUP BY year, week
        ORDER BY year, week;
        """
        df = con.execute(query).fetchdf()
        con.close()

        if df.empty:
            return f"<p>No data available to generate table: {title}</p>"

        # Pivot the table to have years as columns and weeks as index
        pivot_df = df.pivot_table(index='week', columns='year', values='value').sort_index()

        # Select the most recent N years
        available_years = sorted([col for col in pivot_df.columns if str(col).isdigit()], key=int)
        if not available_years:
            return f"<p>No yearly data found for {title}</p>"
            
        years = available_years[-years_to_show:]
        pivot_df = pivot_df[years]

        # Calculate analytical columns
        current_year_col = years[-1]
        prev_year_col = years[-2]

        # Year-over-Year Change (%)
        if prev_year_col in pivot_df.columns:
            pivot_df['y/y (%)'] = (pivot_df[current_year_col] / pivot_df[prev_year_col] - 1) * 100
        else:
            pivot_df['y/y (%)'] = None

        # 4-Week Moving Average on the current year
        pivot_df['4w_ma'] = pivot_df[current_year_col].rolling(window=4, min_periods=1).mean()
        
        # 3-Year Average
        three_year_cols = [y for y in years[-4:-1] if y in pivot_df.columns]
        if len(three_year_cols) > 0:
            pivot_df['3y_avg'] = pivot_df[three_year_cols].mean(axis=1)
        else:
            pivot_df['3y_avg'] = None

        # Reorder columns for presentation
        display_cols = years + ['y/y (%)', '4w_ma', '3y_avg']
        final_df = pivot_df[display_cols].copy()
        
        # Sort by week number descending to show latest first
        final_df = final_df.sort_index(ascending=False).head(15) # Show last 15 weeks

        # --- Formatting for HTML ---
        formatted_df = final_df.copy()
        
        # Format currency columns
        if is_currency:
            for year_col in years + ['4w_ma', '3y_avg']:
                if year_col in formatted_df.columns:
                    formatted_df[year_col] = formatted_df[year_col].apply(
                        lambda x: f"{x/1000:,.1f}B" if pd.notnull(x) and abs(x) > 1000 else f"{x:,.0f}M" if pd.notnull(x) else "-"
                    )
        
        # Format percentage column
        if 'y/y (%)' in formatted_df.columns:
            formatted_df['y/y (%)'] = formatted_df['y/y (%)'].apply(
                lambda x: f"{x:+.1f}%" if pd.notnull(x) else "-"
            )
            
        # Rename columns for display
        formatted_df.columns = [str(c).replace("_", " ").title() for c in formatted_df.columns]
        
        return formatted_df.to_html(classes="table table-striped table-hover", border=0)

    except Exception as e:
        print(f"Error creating multi-year table for '{title}': {e}")
        return f"<p>Could not generate table '{title}' due to an error: {e}</p>"

