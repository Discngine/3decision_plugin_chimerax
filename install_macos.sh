#!/bin/bash
#===============================================================================
# ChimeraX 3decision Plugin Installer for macOS
# Automatically detects ChimeraX installation and installs the plugin
#===============================================================================

set -e  # Exit on any error

echo "========================================"
echo "ChimeraX 3decision Plugin Installer"
echo "Platform: macOS"
echo "========================================"

# Function to find ChimeraX on macOS
find_chimerax_macos() {
    local chimerax_paths=(
        "/Applications/ChimeraX-*.app/Contents/bin/ChimeraX"
        "/Applications/ChimeraX.app/Contents/bin/ChimeraX"
        "$HOME/Applications/ChimeraX-*.app/Contents/bin/ChimeraX"
        "$HOME/Applications/ChimeraX.app/Contents/bin/ChimeraX"
    )
    
    for pattern in "${chimerax_paths[@]}"; do
        for path in $pattern; do
            if [[ -x "$path" ]]; then
                echo "$path"
                return 0
            fi
        done
    done
    
    return 1
}

# Function to get ChimeraX version
get_chimerax_version() {
    local chimerax_path="$1"
    "$chimerax_path" --version 2>/dev/null | head -n 1 | sed 's/ChimeraX //' || echo "unknown"
}

# Main installation function
main() {
    echo "Starting installation process..."
    echo "Plugin directory: $(pwd)"
    echo
    
    # Find ChimeraX
    if CHIMERAX_PATH=$(find_chimerax_macos); then
        CHIMERAX_VERSION=$(get_chimerax_version "$CHIMERAX_PATH")
        echo "✅ Found ChimeraX: $CHIMERAX_PATH"
        echo "   Version: $CHIMERAX_VERSION"
    else
        echo "❌ ChimeraX not found in standard locations."
        echo ""
        echo "Please install ChimeraX from: https://www.rbvi.ucsf.edu/chimerax/download.html"
        echo "Or specify the path manually:"
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
    if [[ -w "$CHIMERAX_PACKAGES_DIR" ]]; then
        echo "✅ Have write permissions to ChimeraX packages directory"
        USE_SUDO=false
    else
        echo "⚠️ Need elevated permissions for ChimeraX packages directory"
        echo "Will prompt for administrator password when needed"
        USE_SUDO=true
    fi
    
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
        unzip -q "$OLDPWD/$WHEEL_FILE"
        
        # Copy files to ChimeraX
        echo "Copying files to ChimeraX packages directory..."
        if [[ "$USE_SUDO" == "true" ]]; then
            sudo cp -r chimerax/threedecision "$CHIMERAX_PACKAGES_DIR/"
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
        echo "2. Verify ChimeraX version compatibility (1.8+)"
        echo "3. Run with verbose output: $0 --verbose"
    fi
    
    echo
    echo "For configuration and usage instructions, see README.md"
    echo "========================================"
}

# Run main function
main "$@"
