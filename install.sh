#!/bin/bash
#===============================================================================
# ChimeraX 3decision Plugin Installer
# Follows official ChimeraX bundle development guidelines
# https://www.cgl.ucsf.edu/chimerax/docs/devel/writing_bundles.html
#===============================================================================

set -e  # Exit on any error

echo "========================================"
echo "ChimeraX 3decision Plugin Installer"
echo "Official ChimeraX Bundle Format"
echo "========================================"

# Function to find ChimeraX
find_chimerax() {
    local chimerax_paths=(
        "/Applications/ChimeraX-*.app/Contents/bin/ChimeraX"  # macOS
        "/Applications/ChimeraX.app/Contents/bin/ChimeraX"
        "/usr/local/bin/ChimeraX"                             # Linux
        "/usr/bin/ChimeraX"
        "/opt/ChimeraX*/bin/ChimeraX"
        "$HOME/ChimeraX*/bin/ChimeraX"
        "$(which ChimeraX 2>/dev/null)"
    )
    
    # Also check Windows paths if we're in a Windows-like environment
    if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]] || [[ -n "$WINDIR" ]]; then
        chimerax_paths+=(
            "/c/Program Files/ChimeraX*/bin/ChimeraX.exe"
            "/c/Program Files (x86)/ChimeraX*/bin/ChimeraX.exe"
        )
    fi
    
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

# Main installation function following official guidelines
main() {
    echo "Starting installation using official ChimeraX method..."
    echo "Plugin directory: $(pwd)"
    echo
    
    # Check if we're in the correct directory
    if [[ ! -f "bundle_info.xml" ]]; then
        echo "❌ bundle_info.xml not found. Please run from the plugin directory."
        echo "Expected files: bundle_info.xml, setup.py, src/ directory"
        exit 1
    fi
    
    # Find ChimeraX
    if CHIMERAX_PATH=$(find_chimerax); then
        echo "✅ Found ChimeraX: $CHIMERAX_PATH"
        CHIMERAX_VERSION=$("$CHIMERAX_PATH" --version 2>/dev/null | head -n 1 | sed 's/ChimeraX //' || echo "unknown")
        echo "   Version: $CHIMERAX_VERSION"
    else
        echo "❌ ChimeraX not found."
        echo ""
        echo "Please install ChimeraX from: https://www.rbvi.ucsf.edu/chimerax/download.html"
        echo ""
        echo "Or specify ChimeraX path manually:"
        echo "  export CHIMERAX_PATH='/path/to/ChimeraX'"
        echo "  $0"
        exit 1
    fi
    
    echo
    echo "Building and installing bundle using official ChimeraX method..."
    echo "Command: $CHIMERAX_PATH --nogui --cmd \"devel install $(pwd); exit\""
    echo
    
    # Use the official ChimeraX devel install command
    # This is the recommended method from the official documentation
    if "$CHIMERAX_PATH" --nogui --cmd "devel install $(pwd); exit"; then
        echo
        echo "✅ Bundle installed successfully!"
    else
        echo
        echo "❌ Installation failed!"
        echo
        echo "Troubleshooting tips:"
        echo "1. Ensure ChimeraX version is 1.8 or later"
        echo "2. Check that you have write permissions to ChimeraX bundle directory"
        echo "3. On Linux, install build dependencies: sudo apt-get install python3-dev build-essential"
        echo "4. Try running ChimeraX with debug output: $CHIMERAX_PATH --debug"
        exit 1
    fi
    
    echo
    echo "Testing installation..."
    
    # Test the installation
    if "$CHIMERAX_PATH" --nogui --cmd "python 'import chimerax.threedecision; print(\"✅ Module import successful\")'; exit" 2>/dev/null | grep -q "Module import successful"; then
        echo "✅ Installation verified successfully"
    else
        echo "⚠️ Installation completed but verification failed"
        echo "Try restarting ChimeraX and check for error messages"
    fi
    
    echo
    echo "========================================"
    echo "INSTALLATION COMPLETED!"
    echo "========================================"
    echo
    echo "The 3decision plugin has been installed as a ChimeraX bundle."
    echo
    echo "To use the plugin:"
    echo "1. Start ChimeraX"
    echo "2. Use menu: Tools → Structure Analysis → Discngine 3decision"
    echo "3. Or use command: threedecision"
    echo
    echo "For configuration, click the Settings (⚙️) button in the plugin interface."
    echo
    echo "Bundle location: Check with 'toolshed list' command in ChimeraX"
    echo "========================================"
}

# Show help if requested
if [[ "$1" == "--help" ]] || [[ "$1" == "-h" ]]; then
    echo "ChimeraX 3decision Plugin Installer"
    echo
    echo "This installer follows the official ChimeraX bundle development guidelines."
    echo "It uses the 'devel install' command which is the recommended method for"
    echo "building and installing ChimeraX bundles."
    echo
    echo "Usage: $0 [--help]"
    echo
    echo "Environment variables:"
    echo "  CHIMERAX_PATH    Path to ChimeraX executable (if not in standard locations)"
    echo
    echo "Official documentation:"
    echo "  https://www.cgl.ucsf.edu/chimerax/docs/devel/writing_bundles.html"
    exit 0
fi

# Run main installation
main "$@"
