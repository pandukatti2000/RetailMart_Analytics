"""
RetailMart 360 - Data Loader Module
Handles robust, portable ingestion of raw retail database extracts.
"""

from pathlib import Path
from typing import Dict, Optional
import pandas as pd

# Determine project root dynamically from this file's position
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"


def get_project_root() -> Path:
    """Returns the absolute project root path."""
    return PROJECT_ROOT


def load_raw_table(table_name: str, raw_dir: Optional[Path] = None) -> pd.DataFrame:
    """
    Loads a single raw CSV table with appropriate encoding and NA preservation.
    
    Args:
        table_name: Table name without extension (e.g., 'customers')
        raw_dir: Optional override for raw data directory
    
    Returns:
        pd.DataFrame
    """
    data_dir = raw_dir or RAW_DATA_DIR
    file_path = data_dir / f"{table_name}.csv"
    
    if not file_path.exists():
        # Fallback to retail_analysis-main nested directory if data/raw was not populated
        fallback = PROJECT_ROOT / "retail_analysis-main" / "retail_analysis-main" / "Data" / "CSV" / f"{table_name}.csv"
        if fallback.exists():
            file_path = fallback
        else:
            raise FileNotFoundError(f"Raw data file for table '{table_name}' not found at {file_path}")

    # Special handling for 'offices': 'NA' string is a valid territory (North America), not null
    if table_name == "offices":
        df = pd.read_csv(file_path, keep_default_na=False, na_values=["", "NULL", "null"])
    else:
        df = pd.read_csv(file_path)
        
    return df


def load_all_raw_tables(raw_dir: Optional[Path] = None) -> Dict[str, pd.DataFrame]:
    """
    Loads all 8 raw relational tables into a dictionary.
    
    Returns:
        Dictionary mapping table name to pd.DataFrame
    """
    table_names = [
        "customers",
        "employees",
        "offices",
        "orders",
        "orderdetails",
        "payments",
        "productlines",
        "products"
    ]
    return {name: load_raw_table(name, raw_dir) for name in table_names}


def load_processed_table(table_name: str, processed_dir: Optional[Path] = None) -> pd.DataFrame:
    """
    Loads a cleaned, processed table from data/processed/.
    
    Args:
        table_name: Name of processed file (with or without .csv extension)
        processed_dir: Optional override for processed data directory
        
    Returns:
        pd.DataFrame
    """
    p_dir = processed_dir or PROCESSED_DATA_DIR
    clean_name = table_name if table_name.endswith(".csv") else f"{table_name}.csv"
    file_path = p_dir / clean_name
    
    if not file_path.exists():
        raise FileNotFoundError(f"Processed file '{clean_name}' not found at {file_path}. Please run data_cleaning.py first.")
        
    # Parse dates automatically if columns exist
    df = pd.read_csv(file_path)
    date_cols = [c for c in df.columns if "Date" in c or c.endswith("_date")]
    for col in date_cols:
        df[col] = pd.to_datetime(df[col], errors="coerce")
        
    return df
