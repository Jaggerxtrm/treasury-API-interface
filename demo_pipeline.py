#!/usr/bin/env python3
"""
Quick Pipeline Demo - Shows how the pipeline will work with timestamped output
"""

import os
import sys
from datetime import datetime

def create_demo_pipeline_report():
    """Create a demo pipeline report to show the output format"""
    PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_file = os.path.join(PROJECT_ROOT, "outputs", f"pipeline_raw-{timestamp}.md")
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Demo content showing what the final pipeline will produce
    demo_content = f"""# Treasury API Pipeline Report
**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**Status:** Demo Mode - Showing expected output format  
**Total Duration:** ~120.5 seconds  

## Execution Summary

| Status | Count | Percentage |
|--------|-------|------------|
| ✅ Success | 6 | 100.0% |
| ❌ Failed | 0 | 0.0% |

## Script Results

### 1. python fiscal/fiscal_analysis.py

**Status:** ✅ Success  
**Duration:** 45.2 seconds  
**Start:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**End:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

**Output:**
```
Fiscal Analysis Complete
- Deposits: $2.1T
- Withdrawals: $1.8T  
- Net Position: $300B
- Generated: fiscal/fiscal_2025-11-27.json
```

---

### 2. python fed/fed_liquidity.py

**Status:** ✅ Success  
**Duration:** 18.7 seconds  
**Start:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**End:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

**Output:**
```
Fed Liquidity Analysis Complete
- Repo Rate: 4.83%
- Reverse Repo: $2.05T
- TGA Balance: $775B
- Generated: fed/liquidity_2025-11-27.json
```

---

### 3. python fed/nyfed_operations.py

**Status:** ✅ Success  
**Duration:** 12.3 seconds  
**Start:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**End:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

**Output:**
```
NY Fed Operations Complete
- SOMA Holdings: $7.2T
- Treasury Securities: $6.8T
- Agency MBS: $425B
- Generated: fed/nyfed_ops_2025-11-27.json
```

---

### 4. python fed/nyfed_reference_rates.py

**Status:** ✅ Success  
**Duration:** 15.1 seconds  
**Start:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**End:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

**Output:**
```
NY Fed Reference Rates Complete
- SOFR: 4.83%
- EFFR: 4.83%  
- OBFR: 4.82%
- Generated: fed/reference_rates_2025-11-27.json
```

---

### 5. python fed/nyfed_settlement_fails.py

**Status:** ✅ Success  
**Duration:** 8.9 seconds  
**Start:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**End:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

**Output:**
```
NY Fed Settlement Fails Complete
- Treasury Fails: $2.1B
- Agency Fails: $0.8B
- Total Fails: $2.9B
- Generated: fed/settlement_fails_2025-11-27.json
```

---

### 6. python fed/liquidity_composite_index.py

**Status:** ✅ Success  
**Duration:** 20.3 seconds  
**Start:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**End:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

**Output:**
```
Liquidity Composite Index Complete
- Composite Index: 75.3
- Stress Level: Medium
- Component Count: 12
- Generated: fed/liquidity_composite_2025-11-27.json
```

---

## Pipeline Metadata

- **Pipeline Version:** 1.0.0
- **Python Version:** {sys.version}
- **Working Directory:** {PROJECT_ROOT}
- **Scripts Executed:**
  1. fiscal/fiscal_analysis.py
  2. fed/fed_liquidity.py
  3. fed/nyfed_operations.py  
  4. fed/nyfed_reference_rates.py
  5. fed/nyfed_settlement_fails.py
  6. fed/liquidity_composite_index.py

## Usage Instructions

To run the actual pipeline with real data execution:

**Python Version:**
```bash
python run_pipeline.py
```

**Bash Version:**  
```bash
./run_pipeline.sh
```

Both will create timestamped files like: `outputs/pipeline_raw-YYYY-MM-DD_HH-MM-SS.md`

*End of Pipeline Report*
"""
    
    # Write demo report
    with open(output_file, 'w') as f:
        f.write(demo_content)
    
    print(f"Demo pipeline report created: {output_file}")
    print("This shows the format - use run_pipeline.py or run_pipeline.sh for actual execution")
    
    return output_file

if __name__ == "__main__":
    create_demo_pipeline_report()
