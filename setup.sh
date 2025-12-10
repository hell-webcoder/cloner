#!/bin/bash
# =============================================================================
# Website Cloner Pro - One-Click Setup Script
# =============================================================================
# This script installs all requirements for Website Cloner Pro
# 
# Usage: 
#   chmod +x setup.sh
#   ./setup.sh
#
# Or run directly:
#   bash setup.sh
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Print banner
echo -e "${CYAN}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║            WEBSITE CLONER PRO - SETUP SCRIPT                  ║"
echo "║           One-Click Installation & Configuration              ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Function to print status messages
print_status() {
    echo -e "${BLUE}[*]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Check if Python is installed
print_status "Checking Python installation..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
    PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d'.' -f1)
    PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d'.' -f2)
    
    if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 8 ]; then
        print_success "Python $PYTHON_VERSION found"
    else
        print_error "Python 3.8 or higher is required. Found: $PYTHON_VERSION"
        exit 1
    fi
else
    print_error "Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Check if pip is installed
print_status "Checking pip installation..."
if command -v pip3 &> /dev/null; then
    print_success "pip3 found"
    PIP_CMD="pip3"
elif command -v pip &> /dev/null; then
    print_success "pip found"
    PIP_CMD="pip"
else
    print_error "pip is not installed. Please install pip first."
    exit 1
fi

# Create virtual environment (optional)
if [ "$1" == "--venv" ]; then
    print_status "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    print_success "Virtual environment created and activated"
    PIP_CMD="pip"
fi

# Install Python dependencies
print_status "Installing Python dependencies..."
$PIP_CMD install -r requirements.txt --quiet
if [ $? -eq 0 ]; then
    print_success "Python dependencies installed"
else
    print_error "Failed to install Python dependencies"
    exit 1
fi

# Install the package in development mode
print_status "Installing Website Cloner package..."
$PIP_CMD install -e . --quiet
if [ $? -eq 0 ]; then
    print_success "Website Cloner package installed"
else
    print_error "Failed to install package"
    exit 1
fi

# Install Playwright browser
print_status "Installing Playwright Chromium browser..."
playwright install chromium
if [ $? -eq 0 ]; then
    print_success "Playwright Chromium browser installed"
else
    print_warning "Failed to install Playwright browser. You may need to run: playwright install chromium"
fi

# Print success message
echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              INSTALLATION COMPLETED SUCCESSFULLY!             ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BOLD}Usage:${NC}"
echo ""
echo -e "  ${CYAN}Command Line Interface:${NC}"
echo -e "    website-cloner --url https://example.com --output ./cloned"
echo -e "    website-cloner --url https://example.com --full-analysis"
echo ""
echo -e "  ${CYAN}Web User Interface:${NC}"
echo -e "    website-cloner-web"
echo -e "    Then open: ${BOLD}http://localhost:5000${NC}"
echo ""
echo -e "  ${CYAN}Alternative Commands:${NC}"
echo -e "    python -m website_cloner.main --url https://example.com"
echo -e "    python -m website_cloner.web.run"
echo ""
echo -e "${YELLOW}For more options, run: website-cloner --help${NC}"
echo ""
