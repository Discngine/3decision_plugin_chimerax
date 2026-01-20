# ChimeraX 3decision Plugin

A ChimeraX plugin for connecting to 3decision services, allowing users to search for structures, browse projects, and visualize molecular data directly within ChimeraX.

## Features

- **Structure Search**: Search the 3decision database for molecular structures with real-time job polling
- **Project Browser**: Browse and load structures from 3decision projects with transformation matrices
- **Authentication Management**: Secure storage of API credentials with automatic token refresh
- **ChimeraX Integration**: Native integration with ChimeraX's tool system and menu structure
- **Batch Operations**: Load multiple structures simultaneously with proper metadata

## Installation

### Prerequisites

- **ChimeraX 1.8 or later** - Download from [ChimeraX official website](https://www.rbvi.ucsf.edu/chimerax/download.html)
- **Active 3decision API credentials** (API key and server URL)
- **Platform-specific requirements:**
  - **Linux**: `python3-dev`, `build-essential` (Ubuntu/Debian) or `python3-devel`, `gcc` (CentOS/RHEL/Fedora)
  - **Windows**: No additional requirements
  - **macOS**: No additional requirements

### Official ChimeraX Installation Method (Recommended)

This bundle follows the official ChimeraX development guidelines. The recommended installation method uses ChimeraX's built-in `devel install` command:

1. **Download or clone this repository:**
   ```bash
   git clone <repository-url>
   cd chimerax-plugin
   ```

2. **Install using ChimeraX:**
   ```bash
   # Automatic installation (detects ChimeraX location)
   ./install.sh           # Unix-like systems
   install_windows.bat    # Windows
   
   # Manual installation (if you know ChimeraX path)
   /path/to/ChimeraX --nogui --cmd "devel install $(pwd); exit"
   
   # Using make (if available)
   make install
   ```

### Alternative Installation Methods

**Option 1 - Using Makefile:**
```bash
# Edit Makefile to set your ChimeraX path if needed
make install    # Build and install
make test       # Verify installation
make app        # Start ChimeraX for testing
```

**Option 2 - Manual wheel installation:**
```bash
# Build wheel
/path/to/ChimeraX --nogui --cmd "devel build $(pwd); exit"

# Install wheel using toolshed
/path/to/ChimeraX --nogui --cmd "toolshed install dist/ChimeraX_threedecision-*.whl; exit"
```

### Distribution via ChimeraX Toolshed

This bundle is designed for distribution through the official [ChimeraX Toolshed](https://cxtoolshed.rbvi.ucsf.edu/). Once published, users can install it directly from ChimeraX:

```bash
# In ChimeraX command line:
toolshed install threedecision
```

### Verification

After installation, verify the bundle is properly installed:

1. **Test import:**
   ```bash
   /path/to/ChimeraX --nogui --cmd "python 'import chimerax.threedecision; print(\"✅ Bundle installed successfully\")'; exit"
   ```

2. **Check toolshed:**
   ```bash
   /path/to/ChimeraX --nogui --cmd "toolshed list; exit"
   ```

3. **Interactive test:**
   - Start ChimeraX
   - Run command: `threedecision`
   - Or use menu: Tools → Structure Analysis → Discngine 3decision

### Platform-Specific Notes

#### macOS
- ChimeraX is typically installed in `/Applications/ChimeraX.app/`
- The installer will request administrator privileges if needed
- Supports both Intel and Apple Silicon Macs

#### Windows  
- ChimeraX is typically installed in `C:\Program Files\ChimeraX\`
- Run Command Prompt as Administrator if you encounter permission issues
- Compatible with Windows 10 and 11

#### Linux
- Install build dependencies first:
  ```bash
  # Ubuntu/Debian:
  sudo apt-get install python3-dev build-essential unzip
  
  # CentOS/RHEL/Fedora:
  sudo yum install python3-devel gcc gcc-c++ unzip
  ```
- ChimeraX may be in `/usr/local/bin/`, `/opt/`, or `~/` depending on installation method
- The installer supports both system-wide and user installations

### Troubleshooting Installation

**Common Issues:**

1. **ChimeraX not found:**
   - Ensure ChimeraX is installed and accessible
   - On Linux/Mac, add ChimeraX to your PATH or use: `export CHIMERAX_PATH=/path/to/ChimeraX`
   - On Windows, verify the installation path

2. **Permission denied:**
   - Run the installer as Administrator (Windows) or with sudo (Linux/Mac)
   - Or install ChimeraX in a user-writable location

3. **Build failures:**
   - On Linux, install development packages: `sudo apt-get install python3-dev build-essential`
   - Verify ChimeraX version is 1.8 or later
   - Check that Python development headers are available

4. **Import errors after installation:**
   - Restart ChimeraX completely
   - Check the ChimeraX log for specific error messages
   - Verify file permissions in the installation directory

### Verification

After installation, verify the plugin works:

1. **Start ChimeraX**
2. **Open Python Shell:** Tools → General → Shell  
3. **Test import:**
   ```python
   import chimerax.threedecision
   print("✅ Plugin installed successfully!")
   ```

If this works, proceed to the [Usage](#usage) section.

## Usage

### Starting the Plugin

**Method 1 - Command Registration (Recommended):**
1. Start ChimeraX
2. Open Python Shell: **Tools → General → Shell**
3. Copy and paste this code:
   ```python
   from chimerax.threedecision.commands import threedecision_cmd, threedecision_desc
   from chimerax.core.commands import register
   register('threedecision', threedecision_desc, threedecision_cmd)
   threedecision
   ```

**Method 2 - Menu Access:**
**Tools → Structure Analysis → Discngine 3decision**

**Method 3 - Direct Launch:**
```python
from chimerax.threedecision.gui import ThreeDecisionTool
tool = ThreeDecisionTool(session, 'threedecision')
tool.display(True)
```

### Command Line Usage

After registering the command (Method 1 above), you can use the `threedecision` command in ChimeraX:

#### Basic Command
```
threedecision
```
Opens the Discngine 3decision tool interface.

#### Command with Search
```
threedecision search <query>
```
Opens the tool interface and immediately starts a search.

**Examples:**
```
threedecision search kinase
threedecision search "protein name"
threedecision search ABL1
```

#### Command Options
- `threedecision` - Opens the tool interface
- `threedecision search <terms>` - Opens interface and searches for the specified terms
- Search terms can include:
  - Protein names (e.g., "ABL1", "kinase")
  - PDB codes (e.g., "1ATP")
  - Compound names
  - Any searchable text in the 3decision database

**Note:** The command must be registered first using Method 1 above before it can be used.

### Configuration

1. Click the **Settings** button (⚙️) in the plugin interface
2. Enter your 3decision API credentials:
   - **Server URL**: Your 3decision server URL (e.g., `https://your-server.com`)
   - **API Key**: Your 3decision API key
3. Click **Save** to store credentials securely
4. The plugin will automatically authenticate and refresh tokens as needed

## Plugin Interface

### Search Tab
- **Structure Search**: Enter search terms (e.g., "kinase", "ABL1")
- **Real-time Progress**: View search progress and job status
- **Results Table**: Browse search results with structure details
- **Structure Loading**: Select structures and load them into ChimeraX

### Projects Tab
- **Project List**: Automatically loads available projects when tab is selected
- **Project Selection**: Click on a project to view its structures
- **Structure Details**: View external codes, titles, methods, and resolutions
- **Batch Loading**: Use checkboxes to select multiple structures
- **Load with Transforms**: Maintains project superposition when loading
- **Associated Files**: Select structures and click "Select Associated Files" to view related files

### Associated Files Tab
- **File Management**: Browse associated files for selected project structures
- **File Information**: View file IDs, names, types, descriptions, and metadata
- **File Selection**: Use checkboxes to select multiple files
- **File Download & Open**: Click "Open" to download and automatically open files in ChimeraX
- **Format Support**: Automatic detection and opening of supported formats
- **Multi-Structure Support**: View files for multiple selected structures in one table

#### Supported File Formats
Files are automatically opened in ChimeraX if they match these formats:
- **Structure Files**: `.pdb`, `.mmcif`, `.cif`
- **Density Maps**: `.dx`, `.dsn6`, `.ccp4`, `.mrc`
- **Reflection Data**: `.mtz`

For unsupported formats, the plugin offers to save the file to disk instead.

## Key Features

### Automatic Token Refresh
- Uses API key for initial authentication
- Automatically refreshes expired tokens on 401/403 responses
- Transparent to user - no manual re-authentication needed
- Secure credential storage in user config file

### Comprehensive API Integration
- **Search API**: Submit searches and poll for completion
- **Structure Details**: Fetch detailed structure information via GraphQL
- **Project API**: Browse projects and their structures
- **Export API**: Download PDB files with transformation matrices
- **Associated Files API**: Access related files for structures (`/structures/{code}/associated-files`)
- **File Info API**: Get file metadata (`/structures/file/{file-id}`)
- **File Download API**: Download files by ID (`/structures/file/{file-id}/download`)
- **Batch Operations**: Handle multiple structures efficiently

### Error Handling
- Network connectivity issues
- Authentication failures with automatic retry
- API response validation
- User-friendly error messages

## File Structure

```
chimerax-plugin/
├── src/                          # Core plugin source code
│   ├── __init__.py              # Bundle API integration
│   ├── api_client.py            # 3decision API client with token refresh
│   ├── commands.py              # ChimeraX command integration
│   ├── gui.py                   # Qt-based user interface
│   └── settings.py              # Settings dialog and configuration
├── bundle_info.xml              # ChimeraX bundle metadata
├── setup.py                     # Plugin build configuration
├── LICENSE                      # MIT license
├── README.md                    # This file
├── .gitignore                   # Git ignore patterns
├── install.sh                   # Universal installer (Unix-like)
├── install_macos.sh            # macOS-specific installer
├── install_linux.sh            # Linux-specific installer
├── install_windows.bat         # Windows-specific installer
├── test_file_download.py       # Test script for file download functionality
└── build/                       # Build artifacts (generated)
    ├── lib/                     # Built Python modules
    └── dist/                    # Distribution wheels
```

### Installation Scripts

- **`install.sh`**: Universal installer for Unix-like systems (macOS/Linux)
- **`install_macos.sh`**: macOS-specific installer with App bundle detection
- **`install_linux.sh`**: Linux installer with dependency checking
- **`install_windows.bat`**: Windows installer with registry scanning

## Troubleshooting

### Common Issues

1. **Plugin Not Found**: Run the enhanced installer and try both Method 1 and Method 2
2. **Authentication Errors**: Verify API key and server URL in settings dialog
3. **Empty Project Lists**: Ensure you're authenticated and have project access
4. **Structure Loading Fails**: Check network connectivity and API server status

### Debug Information

The plugin includes extensive debug logging. Enable it in the settings dialog to see:
- API request/response details
- Authentication status
- Structure loading progress
- Error details and stack traces

### Getting Help

1. Check the ChimeraX Python Shell for error messages
2. Enable debug logging in plugin settings
3. Verify API credentials and server connectivity
4. Review the logs for specific error details

## Development

For development information, see:
- `DEVELOPMENT.md` - Development setup and guidelines
- `IMPLEMENTATION_SUMMARY.md` - Technical implementation details

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
