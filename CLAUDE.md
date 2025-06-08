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

### GUI Application Implementation Plan (Planned)

**Goal**: Create a beautiful, elegant, and intuitive desktop UI for managing multiple MCP configurations with real-time synchronization and visual feedback.

#### Technology Stack (Recommended)

**Frontend**: **Tauri + React + TypeScript**
- Native desktop performance with web technologies
- Cross-platform (macOS/Linux/Windows) compatibility
- Secure communication with Python backend via IPC
- Modern React ecosystem for rapid development
- Smaller bundle size than Electron

**Backend Integration**: **FastAPI REST API**
- Lightweight wrapper around existing Python classes
- WebSocket support for real-time status updates
- JSON serialization for configuration data
- Preserves all existing CLI functionality

#### UI Architecture & Components

```
src/
├── components/
│   ├── AppStatusCard.tsx       # Individual app sync status display
│   ├── ConfigEditor.tsx        # JSON config editor with validation
│   ├── SyncControls.tsx        # Manual sync triggers and options
│   ├── RealTimeMonitor.tsx     # Live file watching status
│   ├── ServerManager.tsx       # Add/edit/remove MCP servers
│   └── DestructiveOpDialog.tsx # Safety confirmation dialogs
├── pages/
│   ├── Dashboard.tsx           # Main overview screen
│   ├── ServerManagement.tsx    # Detailed server configuration
│   └── Settings.tsx            # Daemon & sync preferences
├── services/
│   ├── api.ts                  # Backend communication layer
│   ├── websocket.ts            # Real-time updates handler
│   └── validation.ts           # Client-side config validation
└── types/
    └── mcp.ts                  # TypeScript data models
```

#### Key User Interface Screens

**Dashboard View**:
- Real-time sync status grid for all 6 supported applications
- Visual indicators (✅/⚠️/❌) for each app's sync state
- Current MCP servers list with quick actions
- One-click sync operations with progress feedback
- Import/export functionality with format validation

**Server Management View**:
- Form-based MCP server configuration
- Real-time validation with error highlighting
- Test connection functionality before saving
- Environment variables and arguments management
- Preview of generated configuration for each app format

**Settings Panel**:
- Daemon configuration (watch apps, debounce delay)
- Auto-start service management integration
- Backup and restore preferences
- Logging and debugging options

#### Data Models & API Design

**REST Endpoints**:
```typescript
// Core sync operations  
GET    /api/status           // Current sync status across all apps
POST   /api/sync             // Manual sync trigger (all apps)
POST   /api/sync/{app}       // Sync from specific application

// Server management
GET    /api/servers          // List current MCP servers
POST   /api/servers          // Add new MCP server
PUT    /api/servers/{id}     // Update existing server
DELETE /api/servers/{id}     # Remove server configuration

// Configuration operations
GET    /api/config           // Current normalized MCP config
PUT    /api/config           // Update entire configuration
POST   /api/import/{app}     // Import config from specific app
GET    /api/export           // Export current config as JSON

// Real-time monitoring
WS     /ws/sync              // Live sync events and status updates
WS     /ws/validation        // Configuration validation results
```

**TypeScript Data Models**:
```typescript
interface MCPServer {
  id: string;
  name: string;
  command: string;
  args?: string[];
  env?: Record<string, string>;
  enabled: boolean;
  description?: string;
}

interface AppStatus {
  name: string;
  path: string;
  exists: boolean;
  inSync: boolean;
  lastModified?: string;
  size?: number;
  format: string;
  errors?: string[];
  handler: string;
}

interface SyncStatus {
  timestamp: string;
  status: 'success' | 'partial' | 'failed';
  appsInSync: number;
  totalApps: number;
  apps: AppStatus[];
  source?: string;
  destructiveOperations?: DestructiveOperation[];
}

interface DestructiveOperation {
  appName: string;
  existingServers: string[];
  serversToRemove: string[];
  remainingServers: string[];
}
```

#### Backend Integration Strategy

**FastAPI Wrapper** (`ui_api_server.py`):
```python
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from mcp_config_sync import MCPConfigSynchronizer, MCPSyncDaemon
import asyncio
import json
from typing import List, Dict, Any

app = FastAPI(title="MCP Config Sync API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["tauri://localhost"])

# Singleton instances
synchronizer = MCPConfigSynchronizer()
daemon = None
active_connections: List[WebSocket] = []

@app.get("/api/status")
async def get_sync_status() -> Dict[str, Any]:
    """Get current sync status and validation results."""
    all_in_sync, validation_results = synchronizer.validate_configs()
    
    return {
        "timestamp": datetime.now().isoformat(),
        "allInSync": all_in_sync,
        "apps": [
            {
                "name": app_name,
                "path": str(path),
                "exists": path.exists(),
                "inSync": validation_results.get(app_name, {}).get("in_sync", False),
                "format": validation_results.get(app_name, {}).get("format", "Unknown"),
                "reason": validation_results.get(app_name, {}).get("reason"),
                "size": path.stat().st_size if path.exists() else 0
            }
            for app_name, path in synchronizer.CONFIG_FILES.items()
        ]
    }

@app.websocket("/ws/sync")
async def websocket_sync_updates(websocket: WebSocket):
    """Real-time sync status updates via WebSocket."""
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            # Send periodic status updates
            status = await get_sync_status()
            await websocket.send_json(status)
            await asyncio.sleep(2)  # Update every 2 seconds
    except Exception:
        pass
    finally:
        active_connections.remove(websocket)
```

**Tauri Integration**:
- **IPC Commands**: Direct Python subprocess execution for CLI operations
- **File System Access**: Secure read/write to configuration directories
- **Process Management**: Start/stop daemon processes from UI
- **Native Notifications**: Desktop alerts for sync events and errors
- **System Tray**: Background operation with quick access menu

#### Visual Design System

**Color Palette**:
- **Primary**: Blue (#2563eb) - Trust, reliability, sync actions
- **Success**: Green (#16a34a) - Successful sync states
- **Warning**: Amber (#d97706) - Out of sync warnings, pending actions
- **Error**: Red (#dc2626) - Sync failures, validation errors
- **Neutral**: Gray scale (#f1f5f9 to #0f172a) - Backgrounds, secondary text

**Design Principles**:
- **Glass Morphism**: Subtle transparency with backdrop blur effects
- **Rounded Corners**: 8px border radius for modern, friendly appearance
- **Soft Shadows**: Layered drop shadows for depth and visual hierarchy
- **Smooth Animations**: 200ms ease-in-out transitions for state changes
- **Typography**: System fonts with clear size hierarchy and spacing

**Status Indicators**:
- ✅ Green checkmark: App in sync, all configurations match
- ⚠️ Amber warning: App out of sync, minor mismatches detected
- ❌ Red cross: App failed, parsing errors or missing files
- 🔄 Blue spinner: Sync operation in progress
- 📱 App icons: Visual distinction for each supported application

#### Implementation Roadmap

**Phase 1: Foundation (2-3 weeks)**
1. Setup Tauri + React + TypeScript project structure
2. Create FastAPI wrapper around existing MCPConfigSynchronizer
3. Implement basic dashboard with real-time app status grid
4. Add manual sync controls with progress feedback and error handling

**Phase 2: Core Features (3-4 weeks)**
1. Server management UI (add/edit/remove MCP servers with validation)
2. Real-time file watching integration via WebSocket connections
3. Import/export functionality with format validation and preview
4. Configuration validation with detailed error reporting and suggestions

**Phase 3: Advanced Features (2-3 weeks)**
1. Settings panel for daemon configuration and preferences
2. Native desktop notifications for sync events and conflicts
3. Auto-start service integration (leveraging existing service roadmap)
4. Backup and restore configurations with versioning

**Phase 4: Polish & Distribution (1-2 weeks)**
1. Performance optimization, error handling, and edge case testing
2. Cross-platform testing and platform-specific optimizations
3. Documentation, help system, and onboarding flow
4. Package for distribution (DMG for macOS, AppImage for Linux, MSI for Windows)

#### Key Value Propositions

**🎯 Intuitive Management**:
- Visual overview of all 6 supported applications at once
- Drag-and-drop server configuration with live validation feedback
- One-click sync operations with detailed progress and status reporting

**⚡ Real-Time Synchronization**:
- Live file watching with immediate UI updates and conflict detection
- WebSocket-based real-time status updates without polling
- Automatic backup before destructive operations with rollback capability

**🛡️ Safety & Reliability**:
- Comprehensive format validation preventing configuration corruption
- Detailed error reporting with recovery suggestions and troubleshooting
- Cross-platform service management for seamless background operation

**🔧 Enhanced Developer Experience**:
- JSON schema validation for MCP server configurations with inline errors
- Import/export between different application formats with preview
- Test server connections before applying changes to configurations
- Integration with existing CLI tools for power users

#### Technical Integration Notes

**Preserving CLI Functionality**:
- All existing command-line operations remain fully functional
- GUI acts as a frontend to the same underlying Python classes
- Users can switch between CLI and GUI workflows seamlessly
- Configuration changes are immediately reflected in both interfaces

**Security Considerations**:
- Tauri's secure IPC prevents unauthorized file system access
- API endpoints validate all input and sanitize file paths
- WebSocket connections are authenticated and rate-limited
- Configuration backups are encrypted and versioned locally

**Performance Optimizations**:
- Debounced file watching to prevent UI update storms
- Lazy loading of configuration data with caching strategies
- Efficient diff algorithms for large configuration comparisons
- Background validation with progressive UI updates

This GUI implementation plan builds upon the existing robust Python foundation while creating an accessible, modern interface that serves both technical and non-technical users. The phased approach ensures rapid iteration cycles and early user feedback integration.