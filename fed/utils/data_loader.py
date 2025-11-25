"""
Data Loading Utilities
Helper functions for loading CSV files with fallback paths.
"""

import os
import pandas as pd
from typing import Optional, List


def find_file(filename: str, search_paths: List[str]) -> Optional[str]:
    """
    Find a file in multiple possible locations.
    
    Args:
        filename: Name of the file to find
        search_paths: List of paths to search
    
    Returns:
        Full path to file if found, None otherwise
    """
    for path in search_paths:
        if os.path.exists(path):
            return path
    return None


def load_csv_with_fallback(
    filename: str,
    search_paths: List[str],
    **kwargs
) -> pd.DataFrame:
    """
    Load CSV file with automatic path resolution.
    
    Args:
        filename: Name of the CSV file
        search_paths: List of paths to try
        **kwargs: Additional arguments to pass to pd.read_csv
    
    Returns:
        DataFrame if file found and loaded, empty DataFrame otherwise
    """
    file_path = find_file(filename, search_paths)
    
    if file_path is None:
        print(f"File not found: {filename}")
        print(f"Searched paths: {search_paths}")
        return pd.DataFrame()
    
    try:
        print(f"Loading {filename} from {file_path}...")
        df = pd.read_csv(file_path, **kwargs)
        print(f"Loaded {len(df)} records")
        return df
        
    except Exception as e:
        print(f"Error loading {filename}: {e}")
        return pd.DataFrame()


def load_tga_data(csv_path: Optional[str] = None) -> pd.Series:
    """
    Load TGA balance data from fiscal analysis CSV.
    
    Args:
        csv_path: Optional path to fiscal analysis CSV
    
    Returns:
        Series with TGA balance indexed by date
    """
    if csv_path is None:
        # Try multiple locations
        search_paths = [
            "outputs/fiscal/fiscal_analysis_full.csv",
            "../outputs/fiscal/fiscal_analysis_full.csv",
            "fiscal/outputs/fiscal/fiscal_analysis_full.csv",
            "fiscal_analysis_full.csv",  # Fallback
        ]
        
        csv_path = find_file("fiscal_analysis_full.csv", search_paths)
        
        if csv_path is None:
            print("TGA data file not found")
            return pd.Series(dtype=float)
    
    try:
        print(f"Loading TGA data from {csv_path}...")
        df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
        
        if "TGA_Balance" not in df.columns:
            print("TGA_Balance column not found in fiscal data")
            return pd.Series(dtype=float)
        
        tga_series = df["TGA_Balance"]
        print(f"TGA data loaded: {len(tga_series)} records")
        
        return tga_series
        
    except Exception as e:
        print(f"Error loading TGA data: {e}")
        return pd.Series(dtype=float)


def ensure_directory_exists(directory: str) -> None:
    """
    Ensure a directory exists, create if it doesn't.
    
    Args:
        directory: Path to directory
    """
    os.makedirs(directory, exist_ok=True)


def get_output_path(filename: str, subdir: str = "fed") -> str:
    """
    Get full output path for a file.
    
    Args:
        filename: Name of the output file
        subdir: Subdirectory under outputs/ (fed, fiscal, auction, composite)
    
    Returns:
        Full path to output file
    """
    output_dir = f"outputs/{subdir}"
    ensure_directory_exists(output_dir)
    return os.path.join(output_dir, filename)
