# ChimeraX 3decision Bundle - Distribution Guide

## For ChimeraX Toolshed Distribution

This document describes how to prepare and distribute the ChimeraX 3decision bundle through official channels.

### Bundle Preparation Checklist

- [x] **Bundle structure** follows official ChimeraX guidelines
- [x] **bundle_info.xml** contains complete metadata
- [x] **license.txt** file present
- [x] **Documentation** in `src/docs/user/` structure
- [x] **Makefile** for standard build process
- [x] **Official installation** using `devel install`

### Building for Distribution

1. **Clean build:**
   ```bash
   make clean
   make wheel
   ```

2. **Test locally:**
   ```bash
   make install
   make test
   ```

3. **Verify wheel:**
   ```bash
   ls dist/ChimeraX_threedecision-*.whl
   ```

### ChimeraX Toolshed Submission

1. **Visit [ChimeraX Toolshed](https://cxtoolshed.rbvi.ucsf.edu/)**
2. **Sign in** with Google account
3. **Submit bundle** using "Submit a Bundle" link
4. **Upload wheel** file from `dist/` directory
5. **Fill metadata:**
   - Description (from bundle_info.xml)
   - Screenshots of the interface
   - Installation instructions
   - Usage examples

### Required Metadata for Toolshed

```xml
<BundleInfo name="ChimeraX-threedecision" 
            version="1.0.0" 
            package="chimerax.threedecision">
  <Author>3decision Team</Author>
  <Email>support@3decision.com</Email>
  <URL>https://www.3decision.com</URL>
  <Synopsis>ChimeraX plugin for Discngine 3decision molecular structure database</Synopsis>
  <Description>...</Description>
  <Categories>
    <Category name="Molecular Structure"/>
    <Category name="Database"/>
  </Categories>
</BundleInfo>
```

### User Installation (After Toolshed Publication)

Users will be able to install using:

1. **ChimeraX Toolshed interface**
2. **Command line:**
   ```bash
   toolshed install threedecision
   ```

### Development vs Production

**Development Installation:**
- Use `devel install` for local development
- Changes require rebuild/reinstall

**Production Installation:**
- Use `toolshed install` for end users  
- Automatic updates through toolshed
- No build process required

### Documentation Links

- [ChimeraX Bundle Development](https://www.cgl.ucsf.edu/chimerax/docs/devel/writing_bundles.html)
- [ChimeraX Toolshed](https://cxtoolshed.rbvi.ucsf.edu/)
- [Bundle Information Tags](https://www.cgl.ucsf.edu/chimerax/docs/devel/tutorials/bundle_info.html)

### Bundle Files Structure

```
chimerax-plugin/
├── bundle_info.xml          # Bundle metadata (required)
├── license.txt             # License text (required)
├── setup.py               # Build configuration
├── Makefile              # Standard build targets
├── src/                  # Bundle source code
│   ├── __init__.py      # Bundle API implementation
│   ├── commands.py      # Command definitions
│   ├── gui.py          # Tool interface
│   ├── api_client.py   # 3decision API client
│   ├── settings.py     # Configuration dialog
│   └── docs/           # Help documentation
│       └── user/
│           ├── commands/
│           │   └── threedecision.html
│           └── tools/
│               └── threedecision.html
└── dist/                # Built wheels (generated)
```
