#!/bin/bash
# Setup cron jobs for PodRipper
# This script helps you set up automated podcast processing and weekly email digest

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}PodRipper Cron Setup${NC}\n"

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PYTHON_PATH="$SCRIPT_DIR/venv/bin/python"
PODRIPPER_SCRIPT="$SCRIPT_DIR/podripper.py"

# Check if virtual environment exists
if [ ! -f "$PYTHON_PATH" ]; then
    echo -e "${YELLOW}Warning: Virtual environment not found at $SCRIPT_DIR/venv${NC}"
    echo "Please ensure you have created a virtual environment"
    echo "You can create one with: python -m venv venv"
    exit 1
fi

echo "Installation directory: $SCRIPT_DIR"
echo "Python path: $PYTHON_PATH"
echo ""

# Create cron entries
DAILY_CRON="0 2 * * * cd $SCRIPT_DIR && $PYTHON_PATH $PODRIPPER_SCRIPT run >> $SCRIPT_DIR/data/cron.log 2>&1"
WEEKLY_EMAIL="0 8 * * SAT cd $SCRIPT_DIR && $PYTHON_PATH $PODRIPPER_SCRIPT send-email >> $SCRIPT_DIR/data/cron.log 2>&1"

echo -e "${BLUE}Suggested cron jobs:${NC}\n"

echo -e "${GREEN}1. Daily podcast processing (runs at 2 AM every day):${NC}"
echo "$DAILY_CRON"
echo ""

echo -e "${GREEN}2. Weekly email digest (Saturday at 8 AM):${NC}"
echo "$WEEKLY_EMAIL"
echo ""

# Ask user what they want to set up
echo -e "${BLUE}What would you like to set up?${NC}"
echo "1) Daily processing only"
echo "2) Weekly email only"
echo "3) Both"
echo "4) Show me the commands (don't install)"
read -p "Choose [1-4]: " choice

case $choice in
    1)
        (crontab -l 2>/dev/null; echo "$DAILY_CRON") | crontab -
        echo -e "${GREEN}✓ Daily processing cron job installed${NC}"
        ;;
    2)
        (crontab -l 2>/dev/null; echo "$WEEKLY_EMAIL") | crontab -
        echo -e "${GREEN}✓ Weekly email cron job installed${NC}"
        ;;
    3)
        (crontab -l 2>/dev/null; echo "$DAILY_CRON"; echo "$WEEKLY_EMAIL") | crontab -
        echo -e "${GREEN}✓ Both cron jobs installed${NC}"
        ;;
    4)
        echo ""
        echo "To manually add these cron jobs, run: crontab -e"
        echo "Then add the lines shown above"
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo ""
echo -e "${BLUE}Cron jobs installed. To view your crontab:${NC}"
echo "  crontab -l"
echo ""
echo -e "${BLUE}To remove cron jobs:${NC}"
echo "  crontab -e"
echo "  (then delete the lines related to PodRipper)"
echo ""
echo -e "${BLUE}Logs will be written to:${NC}"
echo "  $SCRIPT_DIR/data/cron.log"
