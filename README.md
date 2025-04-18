# MCP Config Synchronizer

A utility to synchronize Model Context Protocol (MCP) configurations across multiple applications.

## Overview

This tool ensures that MCP configurations are consistent across different applications that support the Model Context Protocol, such as:

- Cursor
- Codeium Windsurf
- Roocode (VSCode and Windsurf versions)
- Claude Desktop

The tool supports:

- Updating all configurations with a standard config
- Reading a configuration from one app and applying it to all others
- Validating that all configurations are in sync
- Detailed reporting of sync operations

## Usage

### Basic Usage

Apply the default configuration to all applications:

```bash
python mcp_config_sync.py
```

### Sync from an Existing Config

To use one application's config as the source of truth:

```bash
python mcp_config_sync.py --source Cursor
```

Supported source names:
- Cursor
- Windsurf
- Roocode-VSCode
- Roocode-Windsurf
- Claude

You can also specify a custom file path:

```bash
python mcp_config_sync.py --source /path/to/your/config.json
```

## Configuration

The script looks for MCP configuration files in these default locations:

- Cursor: `~/.cursor/mcp.json`
- Windsurf: `~/.codeium/windsurf/mcp_config.json`
- Roocode-VSCode: `~/Library/Application Support/Code/User/globalStorage/rooveterinaryinc.roo-cline/settings/cline_mcp_settings.json`
- Roocode-Windsurf: `~/Library/Application Support/Windsurf - Next/User/globalStorage/rooveterinaryinc.roo-cline/settings/mcp_settings.json`
- Claude: `~/Library/Application Support/Claude/claude_desktop_config.json`

## How It Works

The tool:

1. Loads configurations from each application
2. Preserves application-specific settings
3. Updates the MCP section in each config file
4. Validates that all configs are in sync
5. Generates a detailed report

## Requirements

- Python 3.6+
- No external dependencies

## License

MIT 