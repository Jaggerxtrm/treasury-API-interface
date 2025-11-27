#!/usr/bin/env python3
"""
Empty line cleanup utility for pipeline markdown files
Removes excessive empty lines while preserving formatting structure
"""

import re
import os
from pathlib import Path

def clean_empty_lines_from_file(file_path):
    """
    Remove excessive empty lines from a markdown file while preserving structure
    
    Args:
        file_path (str): Path to the markdown file to clean
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Read the file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Pattern to clean up multiple consecutive empty lines
        # Allow max 2 consecutive empty lines, but collapse more to 2
        cleaned_content = re.sub(r'\n{3,}', '\n\n\n', content)
        
        # Also clean up trailing whitespace on lines with content
        cleaned_content = re.sub(r'[ \t]+\n', '\n', cleaned_content)
        
        # Remove leading/trailing empty lines
        cleaned_content = cleaned_content.strip() + '\n'
        
        # Special handling for code blocks - preserve their formatting
        # Find code blocks and temporarily preserve their multiple newlines
        code_blocks = []
        def preserve_code_blocks(match):
            block = match.group(0)
            code_blocks.append(block)
            return f"__CODE_BLOCK_{len(code_blocks)-1}__"
        
        # Preserve code blocks
        cleaned_content = re.sub(r'```[^`]*```', preserve_code_blocks, cleaned_content, flags=re.DOTALL)
        
        # Apply the empty line cleanup to non-code sections
        cleaned_content = re.sub(r'\n{3,}', '\n\n\n', cleaned_content)
        
        # Restore code blocks
        for i, block in enumerate(code_blocks):
            cleaned_content = cleaned_content.replace(f"__CODE_BLOCK_{i}__", block)
        
        # Write back to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(cleaned_content)
        
        print(f"✓ Cleaned empty lines from: {file_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error cleaning {file_path}: {e}")
        return False

def find_and_clean_latest_pipeline_report():
    """
    Find the most recent pipeline report and clean its empty lines
    
    Returns:
        bool: True if successful, False otherwise
    """
    outputs_dir = Path("outputs")
    if not outputs_dir.exists():
        print("❌ outputs directory not found")
        return False
    
    # Find the most recent pipeline_raw-*.md file
    pipeline_files = list(outputs_dir.glob("pipeline_raw-*.md"))
    
    if not pipeline_files:
        print("❌ No pipeline_raw-*.md files found")
        return False
    
    # Sort by modification time and get the most recent
    latest_file = max(pipeline_files, key=lambda f: f.stat().st_mtime)
    
    print(f"🔧 Cleaning latest pipeline report: {latest_file}")
    return clean_empty_lines_from_file(str(latest_file))

def integrated_cleanup_for_current_file(file_path):
    """
    Function that can be called at the end of pipeline execution
    to clean the specific file that was just created
    """
    if os.path.exists(file_path):
        return clean_empty_lines_from_file(file_path)
    else:
        print(f"❌ File not found: {file_path}")
        return False

def main():
    """Main function - find and clean the latest pipeline report"""
    return find_and_clean_latest_pipeline_report()

if __name__ == "__main__":
    main()
