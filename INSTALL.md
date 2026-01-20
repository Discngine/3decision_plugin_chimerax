# ChimeraX 3decision Plugin - Quick Installation Guide

## Prerequisites
- ChimeraX 1.8 or later installed
- 3decision API credentials (API key and server URL)

## Installation Commands

### Universal Installation (Recommended)
Download the plugin and run:

**macOS/Linux:**
```bash
./install.sh
```

**Windows:**
```cmd
install_windows.bat
```

### Platform-Specific Installation

**macOS:**
```bash
./install_macos.sh
```

**Linux:**
```bash
# Install dependencies first (Ubuntu/Debian):
sudo apt-get install python3-dev build-essential unzip

# Then install plugin:
./install_linux.sh
```

**Windows:**
```cmd
install_windows.bat
```

## After Installation

1. **Start ChimeraX**

2. **Register the plugin** (in ChimeraX Python Shell):
   ```python
   from chimerax.threedecision.commands import threedecision_cmd, threedecision_desc
   from chimerax.core.commands import register
   register('threedecision', threedecision_desc, threedecision_cmd)
   threedecision
   ```

3. **Or use the menu**: Tools → Structure Analysis → Discngine 3decision

4. **Configure your credentials** by clicking the Settings (⚙️) button

## Troubleshooting

**If installation fails:**
- Ensure ChimeraX is properly installed
- Run as Administrator (Windows) or with sudo (Linux/Mac) if needed
- Check that you have write permissions to ChimeraX installation

**If plugin doesn't appear:**
- Restart ChimeraX completely
- Try both registration methods above
- Check ChimeraX Python Shell for error messages

## Usage
- **Search**: Enter search terms and browse results
- **Projects**: Browse project structures with transformations
- **Associated Files**: Download and open related files

For complete documentation, see README.md
