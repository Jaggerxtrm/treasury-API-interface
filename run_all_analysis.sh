#!/bin/bash
#
# Treasury API Interface - Complete Analysis Runner
# Executes all analysis scripts in the correct order
#

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}Treasury API Interface - Complete Analysis${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate

# 1. Fiscal Analysis (prerequisite for Fed Liquidity)
echo ""
echo -e "${GREEN}[1/5] Running Fiscal Analysis...${NC}"
echo "----------------------------------------------"
python fiscal/fiscal_analysis.py
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Fiscal analysis complete${NC}"
else
    echo -e "${YELLOW}⚠ Fiscal analysis had issues${NC}"
fi

# 2. Fed Liquidity Monitor (main script with all features)
echo ""
echo -e "${GREEN}[2/5] Running Fed Liquidity Monitor...${NC}"
echo "----------------------------------------------"
python fed/fed_liquidity.py
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Fed liquidity analysis complete${NC}"
else
    echo -e "${YELLOW}⚠ Fed liquidity analysis had issues${NC}"
fi

# 3. NY Fed Operations (repo/RRP data)
echo ""
echo -e "${GREEN}[3/6] Running NY Fed Operations...${NC}"
echo "----------------------------------------------"
cd fed
python nyfed_operations.py
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ NY Fed operations complete${NC}"
else
    echo -e "${YELLOW}⚠ NY Fed operations had issues${NC}"
fi
cd ..

# 4. NY Fed Reference Rates (SOFR, EFFR, etc.)
echo ""
echo -e "${GREEN}[4/6] Running NY Fed Reference Rates...${NC}"
echo "----------------------------------------------"
cd fed
python nyfed_reference_rates.py
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ NY Fed reference rates complete${NC}"
else
    echo -e "${YELLOW}⚠ NY Fed reference rates had issues${NC}"
fi
cd ..

# 5. OFR Repo Market Analysis
echo ""
echo -e "${GREEN}[5/6] Running OFR Repo Analysis...${NC}"
echo "----------------------------------------------"
cd fed
python ofr_analysis.py
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ OFR repo analysis complete${NC}"
else
    echo -e "${YELLOW}⚠ OFR repo analysis had issues${NC}"
fi
cd ..

# 6. Liquidity Composite Index (combined analysis)
echo ""
echo -e "${GREEN}[6/6] Running Liquidity Composite Index...${NC}"
echo "----------------------------------------------"
cd fed
python liquidity_composite_index.py
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Liquidity composite index complete${NC}"
else
    echo -e "${YELLOW}⚠ Liquidity composite index had issues${NC}"
fi
cd ..

# Summary
echo ""
echo -e "${BLUE}================================================${NC}"
echo -e "${GREEN}✅ All analysis complete!${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo "Output files generated in outputs/ directory:"
echo "  • outputs/fiscal/fiscal_analysis_full.csv"
echo "  • outputs/fed/fed_liquidity_full.csv"
echo "  • outputs/fed/fed_liquidity_summary.csv"
echo "  • outputs/fed/nyfed_repo_ops.csv"
echo "  • outputs/fed/nyfed_rrp_ops.csv"
echo "  • outputs/fed/nyfed_reference_rates.csv"
echo ""
echo -e "${YELLOW}Tip: Run 'python fed/fed_liquidity.py' for the main analysis${NC}"
echo ""
