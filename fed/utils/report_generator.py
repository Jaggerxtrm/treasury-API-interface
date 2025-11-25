"""
Report Generator Utilities
Standardized report formatting for all Fed scripts.
"""

import pandas as pd
from typing import Optional, List, Dict, Any


class ReportGenerator:
    """
    Unified report generator with consistent formatting.
    """
    
    def __init__(self, title: str, width: int = 60):
        """
        Initialize report generator.
        
        Args:
            title: Report title
            width: Width of report in characters
        """
        self.title = title
        self.width = width
    
    def print_header(self, text: str, char: str = "=") -> None:
        """
        Print a header section.
        
        Args:
            text: Header text
            char: Character to use for border
        """
        print("\n" + char * self.width)
        print(text)
        print(char * self.width)
    
    def print_subheader(self, text: str, char: str = "─") -> None:
        """
        Print a subheader section.
        
        Args:
            text: Subheader text
            char: Character to use for border
        """
        print("\n" + char * self.width)
        print(text)
        print(char * self.width)
    
    def print_metric(
        self,
        label: str,
        value: Any,
        unit: str = "",
        format_spec: str = ".2f",
        label_width: int = 25
    ) -> None:
        """
        Print a single metric in standardized format.
        
        Args:
            label: Metric label
            value: Metric value
            unit: Optional unit (%, bps, M, B, etc.)
            format_spec: Format specification for value
            label_width: Width for label column
        """
        if pd.isna(value):
            value_str = "N/A"
        elif isinstance(value, (int, float)):
            if format_spec == ",.0f":
                value_str = f"${value:,.0f}"
            elif format_spec == ".2f":
                value_str = f"{value:.2f}"
            else:
                value_str = f"{value:{format_spec}}"
        else:
            value_str = str(value)
        
        if unit:
            value_str += f" {unit}"
        
        print(f"{label:{label_width}s}: {value_str}")
    
    def print_table(
        self,
        df: pd.DataFrame,
        columns: Optional[List[str]] = None,
        max_rows: int = 10,
        float_format: str = "{:,.2f}"
    ) -> None:
        """
        Print a DataFrame as a formatted table.
        
        Args:
            df: DataFrame to print
            columns: Optional list of columns to include
            max_rows: Maximum number of rows to display
            float_format: Format string for float values
        """
        if df.empty:
            print("No data available")
            return
        
        display_df = df if columns is None else df[columns]
        
        if len(display_df) > max_rows:
            display_df = display_df.tail(max_rows)
        
        print(display_df.to_string(float_format=float_format.format))
    
    def print_section(self, title: str, metrics: Dict[str, Any]) -> None:
        """
        Print a section with multiple metrics.
        
        Args:
            title: Section title
            metrics: Dict of {label: value} pairs
        """
        print(f"\n--- {title} ---")
        for label, value in metrics.items():
            if isinstance(value, dict):
                # Nested metrics
                self.print_metric(label, value.get("value", "N/A"), 
                                value.get("unit", ""),
                                value.get("format", ".2f"))
            else:
                self.print_metric(label, value)
    
    def print_alert(self, message: str, severity: str = "INFO") -> None:
        """
        Print an alert message.
        
        Args:
            message: Alert message
            severity: Severity level (INFO, WARNING, CRITICAL)
        """
        icons = {
            "INFO": "ℹ️",
            "WARNING": "🟡",
            "CRITICAL": "🔴"
        }
        icon = icons.get(severity, "•")
        print(f"{icon} [{severity}] {message}")
    
    def export_summary(
        self,
        data: Dict[str, Any],
        filename: str,
        message: str = "Summary exported"
    ) -> None:
        """
        Export summary data to CSV.
        
        Args:
            data: Dictionary of data to export
            filename: Output filename
            message: Success message to print
        """
        df = pd.DataFrame(data)
        df.to_csv(filename, index=False)
        print(f"\n{message} to {filename}")


def format_currency(value: float, unit: str = "M") -> str:
    """
    Format a currency value with appropriate unit.
    
    Args:
        value: Numeric value
        unit: Unit (M for millions, B for billions)
    
    Returns:
        Formatted string
    """
    if pd.isna(value):
        return "N/A"
    return f"${value:,.0f} {unit}"


def format_percentage(value: float, decimals: int = 2) -> str:
    """
    Format a percentage value.
    
    Args:
        value: Numeric value (e.g., 3.5 for 3.5%)
        decimals: Number of decimal places
    
    Returns:
        Formatted string
    """
    if pd.isna(value):
        return "N/A"
    return f"{value:.{decimals}f}%"


def format_bps(value: float, decimals: int = 1) -> str:
    """
    Format a basis points value.
    
    Args:
        value: Numeric value in bps
        decimals: Number of decimal places
    
    Returns:
        Formatted string
    """
    if pd.isna(value):
        return "N/A"
    return f"{value:.{decimals}f} bps"


def format_change(value: float, show_sign: bool = True) -> str:
    """
    Format a change value with +/- sign.
    
    Args:
        value: Numeric value
        show_sign: Whether to show + sign for positive values
    
    Returns:
        Formatted string
    """
    if pd.isna(value):
        return "N/A"
    
    sign = "+" if value > 0 and show_sign else ""
    return f"{sign}{value:,.0f}"
