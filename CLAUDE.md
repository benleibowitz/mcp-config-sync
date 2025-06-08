# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MCP Config Synchronizer is a Python utility that synchronizes Model Context Protocol (MCP) configurations across multiple applications (Claude Desktop, VSCode, Cursor, Windsurf, Roocode) with real-time automatic syncing capabilities. The tool handles different configuration formats and provides daemon mode for continuous monitoring.

## Common Commands

```bash
# Setup - Install dependencies in virtual environment (required)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Basic synchronization with default config
source venv/bin/activate && python3 mcp_config_sync.py

# Sync from existing application config as source
source venv/bin/activate && python3 mcp_config_sync.py --source Claude
source venv/bin/activate && python3 mcp_config_sync.py --source VSCode

# Real-time daemon mode (continuous monitoring)
source venv/bin/activate && python3 mcp_config_sync.py --daemon

# Watch specific applications only
source venv/bin/activate && python3 mcp_config_sync.py --daemon --watch Claude,VSCode,Cursor

# One-time watch with timeout
source venv/bin/activate && python3 mcp_config_sync.py --watch-once --timeout 30

# Safety features - destructive operation protection
source venv/bin/activate && python3 mcp_config_sync.py --source Claude --force
```

## Architecture

### Core Components

- **MCPConfigSynchronizer**: Main orchestrator class handling configuration detection, format conversion, and synchronization across applications
- **ConfigFormatHandler**: Abstract base class with format-specific implementations:
  - `ClaudeDesktopHandler`: Handles Claude's `mcpServers` format
  - `VSCodeHandler`: Handles VSCode's `mcp.servers` in settings.json
  - `StandardMCPHandler`: Handles standard `mcp.*` format for other apps
  - `LegacyMCPHandler`: Fallback for empty/uninitialized configs

### File Watching System

- **MCPSyncDaemon**: Manages continuous file monitoring using watchdog
- **MCPConfigWatcher**: FileSystemEventHandler with debouncing and conflict resolution
- Monitors parent directories of config files to detect changes
- Implements 2-second debounce delay to prevent rapid successive syncs

### Configuration Mapping

Applications map to specific file paths and format handlers:
- Claude Desktop: `~/Library/Application Support/Claude/claude_desktop_config.json` (mcpServers format)
- VSCode: `~/Library/Application Support/Code/User/settings.json` (mcp.servers format)
- Cursor, Windsurf, Roocode variants: Various paths using standard MCP format

### Format Detection and Conversion

The system automatically detects configuration formats and converts between them:
1. Loads source configuration file
2. Detects format using handler priority order
3. Extracts normalized MCP configuration
4. Applies target format using destination app's handler
5. Preserves non-MCP settings in target files

Key design principle: Format handlers abstract the complexity of different configuration schemas while maintaining application-specific settings.

### Validation System

The synchronizer includes a comprehensive validation system that ensures configurations remain in sync:
1. **Cross-Format Validation**: Compares MCP configurations across different application formats
2. **Metadata Exclusion**: Skips format-specific metadata fields (like `format`) during validation since these legitimately differ between applications
3. **Conflict Detection**: Identifies configuration mismatches and provides detailed reporting
4. **Sync Verification**: Post-synchronization validation ensures all applications have consistent MCP configurations

## Development Notes

### Known Issues Fixed

- **Validation Bug (Fixed)**: The validation system was incorrectly flagging `format` metadata fields as mismatches. This was fixed by excluding the `format` field from validation comparisons since it contains legitimate format identifiers that differ between applications.

- **Destructive Operations (Fixed)**: Added comprehensive safety protection to prevent accidental loss of MCP servers. The system now detects when sync operations would remove existing servers and prompts for user confirmation with detailed information about what will be lost.

### Environment Setup

The project requires a Python virtual environment due to macOS externally-managed-environment restrictions:
- Virtual environment is required for dependency installation
- All commands must be run with the virtual environment activated
- Dependencies are managed via `requirements.txt` (currently: `watchdog>=3.0.0`)

### Testing Workflow

1. Activate virtual environment: `source venv/bin/activate`
2. Run synchronization from a source: `python3 mcp_config_sync.py --source Claude`
3. Verify success status and "in_sync" validation for all applications
4. Check configuration files are properly updated with consistent MCP data

### Safety Feature Testing

To test destructive operation protection:
1. Create a test config with MCP servers: `python3 mcp_config_sync.py --source Claude`
2. Create empty config file: `{"mcpServers": {}}`
3. Test warning system: `python3 mcp_config_sync.py --source empty_config.json`
4. Verify user prompt shows servers that will be removed
5. Test force bypass: `python3 mcp_config_sync.py --source empty_config.json --force`

### Command Line Options

- `--source <app_name_or_path>`: Sync from specific application or file path
- `--daemon`: Run in continuous monitoring mode
- `--watch <apps>`: Comma-separated list of apps to monitor (with --daemon)
- `--watch-once`: Monitor for changes once, then exit
- `--timeout <seconds>`: Timeout for --watch-once mode
- `--debounce <seconds>`: Delay before processing detected changes (default: 2.0)
- `--force`: Skip confirmation prompts for destructive operations

## Future Enhancements

### Cross-Platform Background Service Implementation (Planned)

**Goal**: Automatically start the MCP Config Synchronizer daemon at system startup/login without manual intervention.

**Implementation Strategy**: Hybrid approach combining built-in service installation with platform-specific scripts.

#### Platform-Specific Service Options

**macOS**:
1. **launchd** (Primary) - Native macOS service manager with plist configuration
2. **Login Items** (Fallback) - GUI-based auto-start mechanism

**Linux**:
1. **systemd** (Primary) - Modern Linux service manager with unit files
2. **cron @reboot** (Fallback) - Universal Linux option for startup scripts
3. **Desktop autostart** (Alternative) - ~/.config/autostart/ for desktop environments

**Windows**:
1. **Windows Service** (Primary) - Native Windows service with service wrapper
2. **Task Scheduler** (Fallback) - Built-in Windows scheduler
3. **Startup folder** (Simple) - User startup directory for basic auto-start

#### Implementation Approaches

**Option A: Multiple Install Scripts**
- `install-service-macos.sh` - macOS launchd service installation
- `install-service-linux.sh` - Linux systemd/cron service installation  
- `install-service-windows.bat` - Windows service/task scheduler installation
- Universal `install-service.py` - Platform detection and delegation

**Option B: Single Smart Installer**
- One `install-service.py` script with platform auto-detection
- Chooses optimal service method per platform
- Provides fallback options if primary method fails
- Handles service configuration and file generation

**Option C: Built-in Service Mode** (Recommended)
- Add `--install-service` flag to main script for service installation
- Add `--uninstall-service` flag for service removal
- Handles platform detection and service management internally
- Includes service status checking and management commands

#### Recommended Implementation Plan

**Phase 1**: Built-in service installation (`--install-service` flag)
- Detect platform (macOS/Linux/Windows)
- Generate appropriate service configuration files
- Install service using platform-native tools
- Provide status feedback and troubleshooting info

**Phase 2**: Platform-specific installation scripts
- Advanced users can use dedicated scripts for custom configurations
- Provides more granular control over service parameters
- Supports enterprise deployment scenarios

**Phase 3**: Service management commands
- `--service-status` - Check if service is running
- `--restart-service` - Restart the background service
- `--service-logs` - View service logs and diagnostics

#### Technical Considerations

- **Virtual Environment Handling**: Services must properly activate Python venv
- **Path Resolution**: Absolute paths required for service configurations
- **Logging**: Separate log files for background service operation
- **Error Recovery**: Automatic restart on crashes, with throttling
- **Permissions**: Handle elevated privileges where required
- **Configuration**: Service-specific config options (log levels, watch lists, etc.)