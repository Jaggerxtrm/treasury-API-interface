#!/usr/bin/env python3
"""
Pipeline Runner - Executes all analysis scripts and generates consolidated report
Creates timestamped markdown file that gets overwritten on each run
"""

import subprocess
import sys
import os
from datetime import datetime
import json
import traceback

# Import the cleanup utility
try:
    from cleanup_empty_lines import integrated_cleanup_for_current_file
except ImportError:
    integrated_cleanup_for_current_file = None

# Project root setup
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.append(PROJECT_ROOT)

# Scripts to run in order
# NOTE: nyfed_reference_rates.py and nyfed_operations.py must run BEFORE fed_liquidity.py
# because fed_liquidity.py loads the NY Fed rates CSV for fresher daily rates data
SCRIPTS = [
    "python fiscal/fiscal_analysis.py",
    "python fed/nyfed_reference_rates.py",   # Moved up - provides daily rates (SOFR, EFFR, TGCR)
    "python fed/nyfed_operations.py",        # Moved up - provides RRP/Repo operations data
    "python fed/fed_liquidity.py",           # Now can load NY Fed rates CSV
    "python fed/nyfed_settlement_fails.py",
    "python fed/liquidity_composite_index.py",
    "python generate_desk_report.py"
]

def run_script(command):
    """Run a single script and capture output"""
    print(f"Running: {command}")
    start_time = datetime.now()
    
    try:
        result = subprocess.run(
            command.split(),
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout per script
        )
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        return {
            "script": command,
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "duration": duration,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }
        
    except subprocess.TimeoutExpired:
        return {
            "script": command,
            "success": False,
            "stdout": "",
            "stderr": "Script timed out after 5 minutes",
            "duration": 300,
            "start_time": start_time.isoformat(),
            "end_time": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "script": command,
            "success": False,
            "stdout": "",
            "stderr": f"Unexpected error: {str(e)}",
            "duration": 0,
            "start_time": start_time.isoformat(),
            "end_time": datetime.now().isoformat()
        }

def generate_pipeline_report(results, output_path):
    """Generate markdown report from pipeline results"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Count successes/failures
    successful = sum(1 for r in results if r["success"])
    failed = len(results) - successful
    total_duration = sum(r["duration"] for r in results)
    
    # Generate markdown
    report = f"""# Treasury API Pipeline Report
**Generated:** {timestamp}  
**Status:** {successful}/{len(results)} scripts completed successfully  
**Total Duration:** {total_duration:.1f} seconds  

## Execution Summary

| Status | Count | Percentage |
|--------|-------|------------|
| ✅ Success | {successful} | {successful/len(results)*100:.1f}% |
| ❌ Failed | {failed} | {failed/len(results)*100:.1f}% |

## Script Results

"""
    
    for i, result in enumerate(results, 1):
        status_emoji = "✅" if result["success"] else "❌"
        status_text = "Success" if result["success"] else "Failed"
        
        report += f"""
### {i}. {result["script"]}

**Status:** {status_emoji} {status_text}  
**Duration:** {result["duration"]:.1f} seconds  
**Start:** {result["start_time"]}  
**End:** {result["end_time"]}

"""
        
        if result["stdout"]:
            report += f"**Output:**\n```\n{result['stdout']}\n```\n"
            
        if result["stderr"]:
            report += f"**Errors:**\n```\n{result['stderr']}\n```\n"
        
        report += "---\n"
    
    # Add pipeline metadata
    report += f"""
## Pipeline Metadata

- **Pipeline Version:** 1.0.0
- **Python Version:** {sys.version}
- **Working Directory:** {PROJECT_ROOT}
- **Scripts Executed:**
  1. fiscal/fiscal_analysis.py
  2. fed/nyfed_reference_rates.py
  3. fed/nyfed_operations.py
  4. fed/fed_liquidity.py
  5. fed/nyfed_settlement_fails.py
  6. fed/liquidity_composite_index.py
  7. generate_desk_report.py
- **Output Directory:** {os.path.dirname(output_path)}

*End of Pipeline Report*
"""
    
    # Write to file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(report)
    
    print(f"Pipeline report saved to: {output_path}")
    return output_path

def main():
    """Main pipeline execution"""
    print("Starting Treasury API Pipeline...")
    print("=" * 60)
    
    # Run all scripts
    results = []
    for script in SCRIPTS:
        result = run_script(script)
        results.append(result)
        
        # Print immediate status
        if result["success"]:
            print(f"✅ {script} - {result['duration']:.1f}s")
        else:
            print(f"❌ {script} - FAILED")
            if result["stderr"]:
                print(f"   Error: {result['stderr'][:200]}...")
    
    print("=" * 60)
    
    # Generate timestamped output file
    timestamp_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_file = os.path.join(PROJECT_ROOT, "outputs", f"pipeline_raw-{timestamp_str}.md")
    
    # Create report
    report_path = generate_pipeline_report(results, output_file)
    
    # Clean up empty lines from the generated file
    print("\nCleaning up empty lines from pipeline report...")
    if integrated_cleanup_for_current_file:
        cleanup_success = integrated_cleanup_for_current_file(output_file)
        if cleanup_success:
            print("✓ Empty lines cleanup completed successfully")
        else:
            print("⚠️ Empty lines cleanup failed - file left with original formatting")
    else:
        print("⚠️ Cleanup utility not available - keeping original formatting")
    
    # Summary
    successful = sum(1 for r in results if r["success"])
    print(f"\nPipeline Complete: {successful}/{len(results)} scripts succeeded")
    print(f"Report saved to: {report_path}")
    
    # Exit with error code if any scripts failed
    if successful != len(results):
        sys.exit(1)
    
    return report_path

if __name__ == "__main__":
    main()
