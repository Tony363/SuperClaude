#!/bin/bash
#
# SuperClaude Installation Fix Script
# This script fixes corrupted metadata issues that prevent SuperClaude from working
#
# Usage: ./fix_installation.sh [--backup] [--verbose]
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CLAUDE_DIR="$HOME/.claude"
METADATA_FILE="$CLAUDE_DIR/.superclaude-metadata.json"
SETTINGS_FILE="$CLAUDE_DIR/settings.json"
BACKUP_DIR="$CLAUDE_DIR/backups/$(date +%Y%m%d_%H%M%S)"

# Detect repository root dynamically
detect_repo_root() {
    local current_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local repo_root="$(cd "$current_dir/.." && pwd)"
    echo "$repo_root"
}

REPO_ROOT="$(detect_repo_root)"

# Parse arguments
BACKUP=false
VERBOSE=false
for arg in "$@"; do
    case $arg in
        --backup)
            BACKUP=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --help)
            echo "SuperClaude Installation Fix Script"
            echo ""
            echo "Usage: $0 [--backup] [--verbose]"
            echo ""
            echo "Options:"
            echo "  --backup   Create backups before cleaning"
            echo "  --verbose  Show detailed output"
            echo "  --help     Show this help message"
            exit 0
            ;;
    esac
done

# Functions
print_header() {
    echo -e "${BLUE}===============================================${NC}"
    echo -e "${BLUE}    SuperClaude Installation Fix Script${NC}"
    echo -e "${BLUE}===============================================${NC}"
    echo ""
}

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

check_file_validity() {
    local file="$1"
    if [ -f "$file" ]; then
        if $VERBOSE; then
            print_info "Checking $file..."
        fi

        # Try to parse JSON file
        if python3 -m json.tool "$file" > /dev/null 2>&1; then
            return 0  # Valid JSON
        else
            return 1  # Invalid JSON
        fi
    else
        return 2  # File doesn't exist
    fi
}

backup_files() {
    print_info "Creating backups..."
    mkdir -p "$BACKUP_DIR"

    if [ -f "$METADATA_FILE" ]; then
        cp "$METADATA_FILE" "$BACKUP_DIR/.superclaude-metadata.json"
        print_success "Backed up metadata file"
    fi

    if [ -f "$SETTINGS_FILE" ]; then
        cp "$SETTINGS_FILE" "$BACKUP_DIR/settings.json"
        print_success "Backed up settings file"
    fi

    echo "  Backups saved to: $BACKUP_DIR"
}

clean_metadata() {
    print_info "Cleaning metadata files..."

    # Check metadata file
    check_file_validity "$METADATA_FILE"
    metadata_status=$?

    if [ $metadata_status -eq 0 ]; then
        if $VERBOSE; then
            print_info "Metadata file is valid"
        fi

        # Ask user if they want to clean valid metadata
        echo -e "${YELLOW}Metadata file appears valid. Clean anyway?${NC}"
        read -p "Clean valid metadata? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "Keeping existing metadata"
            return
        fi
    elif [ $metadata_status -eq 1 ]; then
        print_warning "Metadata file is corrupted"
        mv "$METADATA_FILE" "${METADATA_FILE}.corrupted.$(date +%Y%m%d_%H%M%S)"
        print_success "Moved corrupted metadata to backup"
    else
        if $VERBOSE; then
            print_info "Metadata file doesn't exist"
        fi
    fi

    # Remove metadata if it exists
    if [ -f "$METADATA_FILE" ]; then
        rm -f "$METADATA_FILE"
        print_success "Cleaned metadata file"
    fi

    # Check settings file
    check_file_validity "$SETTINGS_FILE"
    settings_status=$?

    if [ $settings_status -eq 1 ]; then
        print_warning "Settings file is corrupted"
        mv "$SETTINGS_FILE" "${SETTINGS_FILE}.corrupted.$(date +%Y%m%d_%H%M%S)"
        print_success "Moved corrupted settings to backup"
    fi
}

verify_superclaude() {
    print_info "Verifying SuperClaude installation..."

    # Check if superclaude command exists
    if command -v superclaude &> /dev/null; then
        print_success "superclaude command found: $(which superclaude)"

        # Try to get version
        if superclaude --version &> /dev/null; then
            version=$(superclaude --version 2>&1 || echo "unknown")
            print_success "superclaude version: $version"
        else
            print_warning "Could not determine superclaude version"
        fi
    else
        print_error "superclaude command not found in PATH"
        echo "  You may need to run: pip install -e ."
        return 1
    fi

    # Check installation directory
    if [ -d "$CLAUDE_DIR" ]; then
        print_success "Claude directory exists: $CLAUDE_DIR"
    else
        print_warning "Claude directory doesn't exist: $CLAUDE_DIR"
        print_info "It will be created during next install"
    fi

    return 0
}

run_installation() {
    print_info "Running SuperClaude installation..."

    if command -v superclaude &> /dev/null; then
        # Run installation with force flag
        if superclaude install --force --yes; then
            print_success "Installation completed successfully!"
            return 0
        else
            print_error "Installation failed"
            print_info "Please check the error messages above"
            return 1
        fi
    else
        print_error "superclaude command not available"
        print_info "Please install SuperClaude first:"
        echo "  cd $REPO_ROOT"
        echo "  pip install -e ."
        return 1
    fi
}

# Main execution
main() {
    print_header

    # Step 1: Backup if requested
    if $BACKUP; then
        backup_files
        echo ""
    fi

    # Step 2: Clean metadata
    clean_metadata
    echo ""

    # Step 3: Verify installation
    if verify_superclaude; then
        echo ""

        # Step 4: Ask to run installation
        echo -e "${BLUE}Ready to reinstall SuperClaude${NC}"
        read -p "Run 'superclaude install --force' now? (Y/n): " -n 1 -r
        echo

        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            echo ""
            run_installation
        else
            print_info "Skipping installation"
            echo ""
            echo "To complete the fix, run:"
            echo "  superclaude install --force"
        fi
    else
        echo ""
        print_error "SuperClaude verification failed"
        echo ""
        echo "Please ensure SuperClaude is installed:"
        echo "  1. cd $REPO_ROOT"
        echo "  2. pip install -e ."
        echo "  3. Run this script again"
    fi

    echo ""
    print_header

    # Final status
    if [ -f "$METADATA_FILE" ]; then
        check_file_validity "$METADATA_FILE"
        if [ $? -eq 0 ]; then
            print_success "Metadata file is valid"
        else
            print_error "Metadata file is still invalid"
        fi
    else
        print_warning "Metadata file doesn't exist (will be created on next install)"
    fi

    echo ""
    echo "Fix script completed!"
    echo ""
    echo "If you still have issues:"
    echo "  1. Run: superclaude clean --all"
    echo "  2. Run: superclaude install --force"
    echo "  3. Check logs: ~/.claude/logs/"
}

# Run main function
main