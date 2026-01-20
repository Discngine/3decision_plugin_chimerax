#!/bin/bash
#===============================================================================
# ChimeraX 3decision Plugin Installer for Linux
# Automatically detects ChimeraX installation and installs the plugin
#===============================================================================

set -e  # Exit on any error

echo "========================================"
echo "ChimeraX 3decision Plugin Installer"
echo "Platform: Linux"
echo "========================================"

# Function to find ChimeraX on Linux
find_chimerax_linux() {
    local chimerax_paths=(
        "/usr/local/bin/ChimeraX"
        "/usr/bin/ChimeraX"
        "/opt/ChimeraX*/bin/ChimeraX"
        "/opt/ucsf/chimerax*/bin/ChimeraX"
        "$HOME/ChimeraX*/bin/ChimeraX"
        "$HOME/.local/bin/ChimeraX"
        "$HOME/bin/ChimeraX"
        "$(which ChimeraX 2>/dev/null)"
    )
    
    for pattern in "${chimerax_paths[@]}"; do
        if [[ "$pattern" == *"*"* ]]; then
            # Handle glob patterns
            for path in $pattern; do
                if [[ -x "$path" ]]; then
                    echo "$path"
                    return 0
                fi
            done
        else
            # Direct path check
            if [[ -x "$pattern" ]]; then
                echo "$pattern"
                return 0
            fi
        fi
    done
    
    return 1
}

# Function to get ChimeraX version
get_chimerax_version() {
    local chimerax_path="$1"
    "$chimerax_path" --version 2>/dev/null | head -n 1 | sed 's/ChimeraX //' || echo "unknown"
}

# Function to check if running with sufficient permissions
check_permissions() {
    local target_dir="$1"
    if [[ -w "$target_dir" ]] || [[ -w "$(dirname "$target_dir")" ]]; then
        return 0
    else
        return 1
    fi
}

# Main installation function
main() {
    echo "Starting installation process..."
    echo "Plugin directory: $(pwd)"
    echo
    
    # Find ChimeraX
    if CHIMERAX_PATH=$(find_chimerax_linux); then
        CHIMERAX_VERSION=$(get_chimerax_version "$CHIMERAX_PATH")
        echo "✅ Found ChimeraX: $CHIMERAX_PATH"
        echo "   Version: $CHIMERAX_VERSION"
    else
        echo "❌ ChimeraX not found in standard locations."
        echo ""
        echo "Please install ChimeraX from: https://www.rbvi.ucsf.edu/chimerax/download.html"
        echo "Or add ChimeraX to your PATH, or specify the path manually:"
        echo "  export CHIMERAX_PATH='/path/to/ChimeraX'"
        echo "  $0"
        exit 1
    fi
    
    # Check if bundle_info.xml exists
    if [[ ! -f "bundle_info.xml" ]]; then
        echo "❌ bundle_info.xml not found. Please run from the plugin directory."
        exit 1
    fi
    
    echo
    echo "Checking installation permissions..."
    
    # Get ChimeraX site-packages directory
    SITE_PACKAGES_DIR=$("$CHIMERAX_PATH" -c "import site; print(site.getsitepackages()[0])" 2>/dev/null || echo "")
    
    if [[ -z "$SITE_PACKAGES_DIR" ]]; then
        echo "❌ Could not determine ChimeraX site-packages directory"
        exit 1
    fi
    
    CHIMERAX_PACKAGES_DIR="$SITE_PACKAGES_DIR/chimerax"
    
    # Check write permissions
    USE_SUDO=false
    if check_permissions "$CHIMERAX_PACKAGES_DIR"; then
        echo "✅ Have write permissions to ChimeraX packages directory"
    else
        echo "⚠️ Need elevated permissions for ChimeraX packages directory"
        if command -v sudo >/dev/null 2>&1; then
            echo "Will use sudo when needed"
            USE_SUDO=true
        else
            echo "❌ sudo not available and insufficient permissions"
            exit 1
        fi
    fi
    
    echo "   ChimeraX packages: $CHIMERAX_PACKAGES_DIR"
    
    echo
    echo "Cleaning up previous installations..."
    
    # Remove existing installation
    TARGET_DIR="$CHIMERAX_PACKAGES_DIR/threedecision"
    if [[ -d "$TARGET_DIR" ]]; then
        echo "Removing existing installation: $TARGET_DIR"
        if [[ "$USE_SUDO" == "true" ]]; then
            sudo rm -rf "$TARGET_DIR"
        else
            rm -rf "$TARGET_DIR"
        fi
    fi
    
    echo "Building plugin..."
    
    # Build the plugin
    if ! "$CHIMERAX_PATH" --nogui --cmd "devel build $(pwd); exit" >/dev/null 2>&1; then
        echo "❌ Plugin build failed"
        echo "This might be due to missing dependencies. On Ubuntu/Debian, try:"
        echo "  sudo apt-get install python3-dev build-essential"
        echo "On CentOS/RHEL/Fedora, try:"
        echo "  sudo yum install python3-devel gcc gcc-c++"
        exit 1
    fi
    
    echo "✅ Plugin built successfully"
    echo
    echo "Installing plugin..."
    
    # Try standard installation first
    echo "Attempting standard ChimeraX installation..."
    if "$CHIMERAX_PATH" --nogui --cmd "devel install $(pwd); exit" >/dev/null 2>&1; then
        echo "✅ Standard installation completed successfully"
    else
        echo "Standard installation failed, trying manual installation..."
        
        # Manual installation
        if [[ ! -d "dist" ]] || [[ -z "$(ls dist/*.whl 2>/dev/null)" ]]; then
            echo "❌ No wheel file found in dist/ directory"
            exit 1
        fi
        
        WHEEL_FILE=$(ls dist/*.whl | head -n 1)
        echo "Extracting wheel file: $WHEEL_FILE"
        
        # Create temporary directory
        TEMP_DIR=$(mktemp -d)
        trap "rm -rf $TEMP_DIR" EXIT
        
        # Extract wheel
        cd "$TEMP_DIR"
        
        # Try different unzip methods
        if command -v unzip >/dev/null 2>&1; then
            unzip -q "$OLDPWD/$WHEEL_FILE"
        elif command -v python3 >/dev/null 2>&1; then
            python3 -m zipfile -e "$OLDPWD/$WHEEL_FILE" .
        elif command -v python >/dev/null 2>&1; then
            python -m zipfile -e "$OLDPWD/$WHEEL_FILE" .
        else
            echo "❌ No suitable unzip tool found (unzip, python3, or python required)"
            exit 1
        fi
        
        # Copy files to ChimeraX
        echo "Copying files to ChimeraX packages directory..."
        if [[ "$USE_SUDO" == "true" ]]; then
            sudo cp -r chimerax/threedecision "$CHIMERAX_PACKAGES_DIR/"
            sudo chown -R $(whoami):$(whoami) "$CHIMERAX_PACKAGES_DIR/threedecision" 2>/dev/null || true
        else
            cp -r chimerax/threedecision "$CHIMERAX_PACKAGES_DIR/"
        fi
        
        cd "$OLDPWD"
        echo "✅ Manual installation completed"
    fi
    
    echo
    echo "Testing installation..."
    
    # Test the installation
    if "$CHIMERAX_PATH" --nogui --cmd "python 'import chimerax.threedecision; print(\"✅ Module import successful\")'; exit" 2>/dev/null | grep -q "Module import successful"; then
        echo "✅ Installation verified successfully"
        INSTALL_SUCCESS=true
    else
        echo "❌ Installation verification failed"
        echo "The plugin was built but import test failed."
        INSTALL_SUCCESS=false
    fi
    
    echo
    echo "========================================"
    echo "INSTALLATION COMPLETED!"
    echo "========================================"
    echo
    
    if [[ "$INSTALL_SUCCESS" == "true" ]]; then
        echo "The threedecision plugin has been installed successfully."
        echo
        echo "To use the plugin:"
        echo "1. Start ChimeraX"
        echo "2. Use menu: Tools → Structure Analysis → Discngine 3decision"
        echo "3. Or use command: threedecision (after registering - see README.md)"
    else
        echo "Installation encountered issues. You can try:"
        echo "1. Check ChimeraX error messages"
        echo "2. Install build dependencies (python3-dev, build-essential)"
        echo "3. Verify ChimeraX version compatibility (1.8+)"
        echo "4. Run with more privileges if needed"
    fi
    
    echo
    echo "For configuration and usage instructions, see README.md"
    echo "========================================"
}

# Check for help flag
if [[ "$1" == "--help" ]] || [[ "$1" == "-h" ]]; then
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --help, -h    Show this help message"
    echo ""
    echo "Environment variables:"
    echo "  CHIMERAX_PATH    Path to ChimeraX executable (if not in standard locations)"
    echo ""
    echo "This script will automatically find and install the 3decision plugin"
    echo "for ChimeraX on Linux systems."
    exit 0
fi

# Run main function
main "$@"
