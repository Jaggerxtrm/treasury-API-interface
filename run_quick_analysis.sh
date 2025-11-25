#!/bin/bash
#
# Treasury API Interface - Quick Analysis
# Runs only the essential scripts (fiscal + fed liquidity)
#

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}Treasury API - Quick Analysis (Essential Only)${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate

# 1. Fiscal Analysis (prerequisite)
echo ""
echo -e "${GREEN}[1/2] Running Fiscal Analysis...${NC}"
echo "----------------------------------------------"
python fiscal/fiscal_analysis.py
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Fiscal analysis complete${NC}"
else
    echo -e "${YELLOW}⚠ Fiscal analysis had issues${NC}"
fi

# 2. Fed Liquidity Monitor (main script - COMPLETE!)
echo ""
echo -e "${GREEN}[2/2] Running Fed Liquidity Monitor (COMPLETE)...${NC}"
echo "----------------------------------------------"
python fed/fed_liquidity.py
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Fed liquidity analysis complete${NC}"
else
    echo -e "${YELLOW}⚠ Fed liquidity analysis had issues${NC}"
fi

# Summary
echo ""
echo -e "${BLUE}================================================${NC}"
echo -e "${GREEN}✅ Quick analysis complete!${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo "Essential output files:"
echo "  • outputs/fiscal/fiscal_analysis_full.csv"
echo "  • outputs/fed/fed_liquidity_full.csv (COMPLETE with all features)"
echo "  • outputs/fed/fed_liquidity_summary.csv"
echo ""
echo -e "${YELLOW}Features included:${NC}"
echo "  ✓ MTD/QTD/3M temporal analysis"
echo "  ✓ Spread spike detection"
echo "  ✓ Composite stress index (0-100)"
echo "  ✓ Regime detection (QE/QT)"
echo "  ✓ Correlations with fiscal data"
echo "  ✓ 5-day trend forecasting"
echo "  ✓ Alert system"
echo ""
