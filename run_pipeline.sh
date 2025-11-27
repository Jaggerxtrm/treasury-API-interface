#!/bin/bash
# Quick pipeline runner - executes all scripts and generates timestamped markdown

# Get current timestamp
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
OUTPUT_FILE="outputs/pipeline_raw-${TIMESTAMP}.md"
PROJECT_ROOT="/home/dawid/Projects/treasury-API-interface"

echo "Starting Treasury API Pipeline..."
echo "Output will be saved to: $OUTPUT_FILE"

# Create output directory
mkdir -p "$PROJECT_ROOT/outputs"

# Start markdown file
cat > "$PROJECT_ROOT/$OUTPUT_FILE" << EOF
# Treasury API Pipeline Report
**Generated:** $(date)  
**Status:** In Progress...

## Script Execution Results

EOF

# Scripts to run (in order)
SCRIPTS=(
    "python fiscal/fiscal_analysis.py"
    "python fed/fed_liquidity.py" 
    "python fed/nyfed_operations.py"
    "python fed/nyfed_reference_rates.py"
    "python fed/nyfed_settlement_fails.py"
    "python fed/liquidity_composite_index.py"
    "python generate_desk_report.py"
)

# Run each script and append to markdown
SUCCESS_COUNT=0
TOTAL_COUNT=${#SCRIPTS[@]}

for i in "${!SCRIPTS[@]}"; do
    SCRIPT="${SCRIPTS[$i]}"
    echo "Running: $SCRIPT"
    
    # Capture script start time
    START_TIME=$(date '+%Y-%m-%d %H:%M:%S')
    START_SEC=$(date +%s)
    
    # Run script and capture output
    if cd "$PROJECT_ROOT" && eval "$SCRIPT" >> /tmp/pipeline_stdout.txt 2>> /tmp/pipeline_stderr.txt; then
        END_TIME=$(date '+%Y-%m-%d %H:%M:%S')
        END_SEC=$(date +%s)
        DURATION=$((END_SEC - START_SEC))
        STATUS="✅ Success"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        
        cat >> "$PROJECT_ROOT/$OUTPUT_FILE" << EOF
### $((i+1)). $SCRIPT

**Status:** ✅ Success  
**Duration:** ${DURATION} seconds  
**Start:** $START_TIME  
**End:** $END_TIME

**Output:**
\`\`\`
$(cat /tmp/pipeline_stdout.txt)
\`\`\`

---

EOF
    else
        END_TIME=$(date '+%Y-%m-%d %H:%M:%S')
        END_SEC=$(date +%s)
        DURATION=$((END_SEC - START_SEC))
        STATUS="❌ Failed"
        
        cat >> "$PROJECT_ROOT/$OUTPUT_FILE" << EOF
### $((i+1)). $SCRIPT

**Status:** ❌ Failed  
**Duration:** ${DURATION} seconds  
**Start:** $START_TIME  
**End:** $END_TIME

**Errors:**
\`\`\`
$(cat /tmp/pipeline_stderr.txt)
\`\`\`

---

EOF
    fi
    
    echo "$STATUS: $SCRIPT (${DURATION}s)"
done

# Add summary to markdown
cat >> "$PROJECT_ROOT/$OUTPUT_FILE" << EOF

## Pipeline Summary

**Total Scripts:** $TOTAL_COUNT  
**Successful:** $SUCCESS_COUNT  
**Failed:** $((TOTAL_COUNT - SUCCESS_COUNT))  
**Success Rate:** $(( SUCCESS_COUNT * 100 / TOTAL_COUNT ))%

**Generated:** $(date)  
**Pipeline Runner:** Bash Shell
**Scripts Executed:**
1. fiscal/fiscal_analysis.py
2. fed/fed_liquidity.py
3. fed/nyfed_operations.py
4. fed/nyfed_reference_rates.py
5. fed/nyfed_settlement_fails.py
6. fed/liquidity_composite_index.py
7. generate_desk_report.py

EOF

echo "Pipeline Complete: $SUCCESS_COUNT/$TOTAL_COUNT scripts succeeded"
echo "Report saved to: $PROJECT_ROOT/$OUTPUT_FILE"

# Exit with appropriate code
if [ $SUCCESS_COUNT -eq $TOTAL_COUNT ]; then
    exit 0
else
    exit 1
fi
