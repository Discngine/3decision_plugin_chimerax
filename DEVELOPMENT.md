# 3decision ChimeraX Plugin - Development Guide

## Overview

This guide provides information for developers working with or modifying the 3decision ChimeraX plugin.

## Project Structure

```
chimerax-plugin/
├── bundle_info.xml          # ChimeraX bundle metadata
├── setup.py                 # Python package setup
├── toolshed.yml            # Toolshed metadata  
├── install.sh              # Installation script
├── test_plugin.py          # Component testing
├── LICENSE                 # MIT license
├── README.md               # User documentation
├── DEVELOPMENT.md          # This file
├── src/                    # Plugin source code
│   ├── __init__.py         # Bundle API and initialization
│   ├── api_client.py       # 3decision API client
│   ├── gui.py              # Main user interface
│   ├── settings.py         # Configuration dialog
│   ├── commands.py         # Command-line interface
│   └── tool_info.py        # Tool metadata
└── docs/                   # Documentation
    └── user/
        └── tools/
            └── threedecision.html  # User help documentation
```

## Key Components

### API Client (`api_client.py`)

The API client handles all communication with 3decision services:

- **Authentication**: Login with API key and token management
- **Search**: Structure search submission and result polling
- **Structure Export**: PDB format downloads
- **Project Management**: Project and structure listing
- **Configuration**: Persistent settings storage

Key features:
- Asynchronous job polling for search results
- GraphQL integration for structure details
- SSL verification disabled for development servers
- Comprehensive error handling and logging

### User Interface (`gui.py`)

The main GUI provides a tabbed interface:

- **Search Tab**: Structure search with results table
- **Projects Tab**: Project browser with structure selection
- **Background Processing**: All network operations in threads
- **Progress Indicators**: Real-time status updates

Key classes:
- `ThreeDecisionTool`: Main tool class
- `SearchThread`: Background search operations
- `JobPollingThread`: Result polling
- `LoadStructuresThread`: Structure loading into ChimeraX
- `ProjectBrowserWidget`: Project navigation

### Settings Dialog (`settings.py`)

Configuration interface for API credentials:

- **Connection Testing**: Background validation
- **Secure Storage**: Local credential persistence
- **User-friendly Interface**: Clear status indicators

### Commands (`commands.py`)

Command-line interface registration:

- `3decision`: Open the main tool
- `3decision search <query>`: Direct search command

## Development Setup

### Prerequisites

- ChimeraX 1.10.1 or later
- Python 3.9+ (comes with ChimeraX)
- Access to a 3decision server for testing

### Testing Without ChimeraX

You can test the core components outside ChimeraX:

```bash
cd /path/to/chimerax-plugin
python test_plugin.py
```

This will verify:
- Module imports
- API client creation
- Configuration handling

### Development Installation

For development, install the plugin in development mode:

```bash
# Method 1: Using the install script
./install.sh

# Method 2: Direct ChimeraX installation
chimerax --nogui --cmd "toolshed install '/path/to/chimerax-plugin'"

# Method 3: Development installation (if you have chimerax python access)
python setup.py develop
```

### Plugin Testing in ChimeraX

1. Start ChimeraX
2. Open the Log panel: **Tools → General → Log**
3. Load the plugin: **Tools → Structure Analysis → 3decision**
4. Configure settings with test credentials
5. Test search and loading functionality

## API Integration

### Endpoints Used

The plugin integrates with these 3decision API endpoints:

- `GET /auth/api/login` - Authentication
- `GET /search/{query}` - Search submission  
- `GET /queues/basicSearch/jobs/{id}` - Result polling
- `POST /graphql` - Structure details (GraphQL)
- `POST /exports/structure` - PDB export request
- `GET /exports/structure/{id}` - PDB download
- `GET /projects` - Project listing
- `GET /projects/{id}/structures/matrix` - Project structures

### Authentication Flow

1. User configures API key in settings
2. Plugin calls `/auth/api/login` with API key
3. Server returns access token
4. Token used for all subsequent requests
5. Token refresh handled automatically on 401/403 errors

### Search Workflow

1. Submit search query to `/search/{query}`
2. Get job ID from response
3. Poll `/queues/basicSearch/jobs/{id}` until complete
4. Extract structure IDs from results
5. Fetch detailed info via GraphQL
6. Display results in table

## Code Style and Conventions

### Python Style

- Follow PEP 8 style guidelines
- Use type hints where appropriate
- Comprehensive docstrings for classes and functions
- Clear variable and function names

### ChimeraX Integration

- Use ChimeraX logging system for user messages
- Follow ChimeraX tool development patterns
- Handle threading properly with Qt signals
- Clean up resources in tool deletion

### Error Handling

- Log errors at appropriate levels
- Provide user-friendly error messages
- Handle network timeouts gracefully
- Validate user input

## Common Development Tasks

### Adding New API Endpoints

1. Add method to `ThreeDecisionAPIClient` class
2. Include proper error handling and logging
3. Update documentation with new endpoint
4. Add tests if applicable

### Modifying the User Interface

1. Update the GUI layout in `gui.py`
2. Connect new widgets to appropriate handlers
3. Update threading if network calls are involved
4. Test responsiveness

### Adding New Commands

1. Add command function to `commands.py`
2. Register with ChimeraX command system
3. Update help documentation
4. Test command-line interface

## Debugging

### Enabling Debug Logging

The plugin uses ChimeraX's logging system. Debug messages appear in the Log panel.

### Common Issues

1. **Import Errors**: Check ChimeraX Python environment
2. **Network Issues**: Verify server accessibility and credentials
3. **Threading Issues**: Use proper Qt signal/slot connections
4. **Memory Leaks**: Clean up threads and temporary files

### Debugging Tools

- ChimeraX Log panel for runtime messages
- Python debugger (pdb) for step-through debugging
- Network monitoring tools for API issues
- ChimeraX developer documentation

## Testing

### Unit Testing

The `test_plugin.py` script provides basic component testing:

```bash
python test_plugin.py
```

### Integration Testing

1. Install plugin in ChimeraX
2. Configure with test server
3. Test all major workflows:
   - Authentication
   - Search functionality  
   - Structure loading
   - Project browsing
   - Error handling

### Performance Testing

- Test with large result sets
- Monitor memory usage during bulk loading
- Verify thread cleanup
- Test network timeout handling

## Deployment

### Building for Distribution

1. Ensure all files are included in bundle
2. Test installation on clean ChimeraX instance
3. Verify documentation is complete
4. Update version numbers consistently

### ChimeraX Toolshed

For distribution via ChimeraX Toolshed:

1. Ensure `bundle_info.xml` is complete
2. Include proper dependencies
3. Test on multiple platforms if possible
4. Follow ChimeraX packaging guidelines

## Contributing

### Code Contributions

1. Fork the repository
2. Create feature branch
3. Make changes with tests
4. Submit pull request with description

### Documentation

- Update user documentation for new features
- Keep development documentation current
- Include code comments for complex logic

### Bug Reports

Include:
- ChimeraX version
- Plugin version
- Steps to reproduce
- Error messages
- Log output

## References

- [ChimeraX Developer Documentation](https://www.rbvi.ucsf.edu/chimerax/docs/devel/index.html)
- [ChimeraX Plugin Development](https://www.rbvi.ucsf.edu/chimerax/docs/devel/tutorials/tutorial.html)
- [Qt for Python Documentation](https://doc.qt.io/qtforpython/)
- [3decision API Documentation](https://your-server.com/api/docs)

## License

This project is licensed under the MIT License - see the LICENSE file for details.
