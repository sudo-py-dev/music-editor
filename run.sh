#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check for Python
if ! command_exists python3; then
    echo -e "${RED}❌ Python 3 is required but not installed.${NC}"
    echo -e "Please install Python 3.6 or higher using one of the following commands:"
    echo -e "  Debian/Ubuntu: ${YELLOW}sudo apt update && sudo apt install python3 python3-venv python3-pip${NC}"
    echo -e "  RHEL/CentOS:  ${YELLOW}sudo yum install python3 python3-venv python3-pip${NC}"
    echo -e "  macOS:         ${YELLOW}brew install python${NC} (using Homebrew)"
    echo -e "  Or download from: ${YELLOW}https://www.python.org/downloads/${NC}"
    exit 1
fi

# Check for Git
if ! command_exists git; then
    echo -e "${RED}❌ Git is required but not installed.${NC}"
    echo -e "Please install Git using one of the following commands:"
    echo -e "  Debian/Ubuntu: ${YELLOW}sudo apt update && sudo apt install git${NC}"
    echo -e "  RHEL/CentOS:  ${YELLOW}sudo yum install git${NC}"
    echo -e "  macOS:         ${YELLOW}brew install git${NC} (using Homebrew)"
    echo -e "  Or download from: ${YELLOW}https://git-scm.com/downloads${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Dependencies verified: Python 3 and Git are installed.${NC}\n"

echo -e "${YELLOW}🚀 Setting up Telegram Bot Environment 🚀${NC}\n"

# Check if .env exists, if not create it
if [ ! -f .env ]; then
    echo -e "${GREEN}Creating .env file...${NC}"
    touch .env
    
    # API Credentials
    echo -e "\n${YELLOW}Enter your Telegram API credentials:${NC}"
    while true; do
        read -p "API ID: " API_ID
        if [[ $API_ID =~ ^[0-9]+$ ]]; then
            break
        else
            echo -e "${RED}❌ Please enter a valid numeric API ID${NC}"
        fi
    done
    
    while true; do
        read -p "API HASH: " API_HASH
        if [ ! -z "$API_HASH" ]; then
            break
        else
            echo -e "${RED}❌ API HASH cannot be empty${NC}"
        fi
    done
    
    while true; do
        read -p "BOT TOKEN (from @BotFather): " BOT_TOKEN
        if [[ $BOT_TOKEN =~ ^[0-9]+:[a-zA-Z0-9_-]+$ ]]; then
            break
        else
            echo -e "${RED}❌ Invalid bot token format. Should be '1234567890:ABCdefGHIjklmNOPqrstUVWXYZ'${NC}"
        fi
    done
    
    read -p "BOT OWNER ID (your Telegram user ID, press Enter to skip): " BOT_OWNER_ID
    read -p "BOT CLIENT NAME [bot]: " BOT_CLIENT_NAME
    
    # Database
    echo -e "\n${YELLOW}Database Configuration:${NC}"
    echo -e "Leave empty to use SQLite (recommended for development)"
    read -p "Database URL (e.g., postgresql://user:pass@localhost/dbname): " DATABASE_URL
    
    # Optional Settings
    echo -e "\n${YELLOW}Optional Settings:${NC}"
    read -p "Bot Language [en]: " BOT_LANGUAGE
    read -p "Log File [bot.log]: " LOG_FILE
    
    # Set defaults if empty
    BOT_LANGUAGE=${BOT_LANGUAGE:-en}
    LOG_FILE=${LOG_FILE:-bot.log}
    BOT_CLIENT_NAME=${BOT_CLIENT_NAME:-bot}
    
    # Show summary
    echo -e "\n${YELLOW}Summary of your settings:${NC}"
    echo -e "API ID: ${GREEN}$API_ID${NC}"
    echo -e "API HASH: ${GREEN}${API_HASH:0:4}...${API_HASH: -4}${NC}"
    echo -e "Bot Token: ${GREEN}${BOT_TOKEN:0:10}...${BOT_TOKEN: -5}${NC}"
    [ ! -z "$BOT_OWNER_ID" ] && echo -e "Bot Owner ID: ${GREEN}$BOT_OWNER_ID${NC}"
    echo -e "Bot Client Name: ${GREEN}$BOT_CLIENT_NAME${NC}"
    if [ ! -z "$DATABASE_URL" ]; then
        echo -e "Database URL: ${GREEN}$DATABASE_URL${NC}"
        echo -e "${YELLOW}Note: Make sure the database server is running and accessible${NC}"
    fi
    echo -e "Bot Language: ${GREEN}$BOT_LANGUAGE${NC}"
    echo -e "Log File: ${GREEN}$LOG_FILE${NC}"
    
    read -p "Proceed with these settings? [Y/n] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]?$ ]]; then
        echo -e "${YELLOW}Setup cancelled.${NC}"
        exit 0
    fi
    
    # Write to .env
    echo "# Required" > .env
    echo "API_ID=$API_ID" >> .env
    echo "API_HASH=$API_HASH" >> .env
    echo "BOT_TOKEN=$BOT_TOKEN" >> .env
    [ ! -z "$BOT_OWNER_ID" ] && echo "BOT_OWNER_ID=$BOT_OWNER_ID" >> .env
    echo "BOT_CLIENT_NAME=$BOT_CLIENT_NAME" >> .env
    
    echo -e "\n# Database" >> .env
    if [ ! -z "$DATABASE_URL" ]; then
        echo "DATABASE_URL=$DATABASE_URL" >> .env
    else
        echo "# Using SQLite by default" >> .env
    fi
    
    echo -e "\n# Optional" >> .env
    echo "BOT_LANGUAGE=$BOT_LANGUAGE" >> .env
    echo "LOG_FILE=$LOG_FILE" >> .env
    
    echo -e "\n${GREEN}✅ .env file created successfully!${NC}"
else
    echo -e "${GREEN}✓ .env file already exists.${NC}"
    echo -e "  To modify settings, edit the .env file directly.${NC}"
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo -e "\n${YELLOW}Creating Python virtual environment...${NC}"
    python3 -m venv .venv || {
        echo -e "${RED}❌ Failed to create virtual environment${NC}"
        echo -e "Try running: ${YELLOW}python3 -m pip install --user virtualenv${NC}"
        exit 1
    }
else
    echo -e "\n${GREEN}✓ Virtual environment already exists.${NC}"
fi

# Activate virtual environment
echo -e "\n${YELLOW}Activating virtual environment...${NC}"
source .venv/bin/activate || {
    echo -e "${RED}❌ Failed to activate virtual environment${NC}"
    exit 1
}

# Install dependencies
echo -e "\n${YELLOW}Installing Python dependencies...${NC}"
pip install --upgrade pip
pip install -r requirements.txt || {
    echo -e "${RED}❌ Failed to install dependencies${NC}"
    echo -e "Try running: ${YELLOW}pip install -r requirements.txt${NC} manually"
    exit 1
}

# Create logs directory if it doesn't exist
mkdir -p logs

# Run the bot
echo -e "\n${GREEN}✅ Setup complete! Starting the bot...${NC}"
echo -e "${YELLOW}To stop the bot, press Ctrl+C"
echo -e "To run the bot in the future, simply run: ${GREEN}./run.sh${NC}"
echo

# Run the bot
python index.py
