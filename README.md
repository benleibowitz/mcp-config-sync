# MCP Config Synchronizer

A powerful utility to synchronize Model Context Protocol (MCP) configurations across multiple applications with real-time automatic syncing capabilities.

## 🚀 Features

- **Multi-Format Support**: Handles different MCP configuration formats across applications
- **Real-Time Sync**: Automatic file watching with instant synchronization
- **Format Detection**: Automatically detects and converts between configuration formats
- **Conflict Resolution**: Intelligent handling of simultaneous changes with debouncing
- **Comprehensive Coverage**: Supports 6+ applications with different MCP implementations
- **Preservation**: Maintains application-specific settings while syncing MCP configs
- **🛡️ Safety Protection**: Prevents accidental loss of MCP servers with confirmation prompts

## 📱 Supported Applications

| Application | Configuration Format | File Location |
|-------------|---------------------|---------------|
| **Claude Desktop** | `mcpServers` | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| **VSCode** | `mcp.servers` | `~/Library/Application Support/Code/User/settings.json` |
| **Cursor** | `mcp.*` | `~/.cursor/mcp.json` |
| **Windsurf** | `mcp.*` | `~/.codeium/windsurf/mcp_config.json` |
| **Roocode (VSCode)** | `mcp.*` | `~/Library/Application Support/Code/User/globalStorage/rooveterinaryinc.roo-cline/settings/cline_mcp_settings.json` |
| **Roocode (Windsurf)** | `mcp.*` | `~/Library/Application Support/Windsurf - Next/User/globalStorage/rooveterinaryinc.roo-cline/settings/mcp_settings.json` |

## 🔧 Installation

1. Clone the repository:
```bash
git clone https://github.com/benleibowitz/mcp-config-sync.git
cd mcp-config-sync
```

2. Setup virtual environment and install dependencies:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

> **Note**: Virtual environment is required on macOS due to externally-managed-environment restrictions.

## 📖 Usage

**First, activate the virtual environment:**
```bash
source venv/bin/activate
```

### One-Time Synchronization

Apply the default configuration to all applications:
```bash
./mcp_config_sync.py
```

Sync from an existing application config:
```bash
./mcp_config_sync.py --source Claude
./mcp_config_sync.py --source VSCode
./mcp_config_sync.py --source Cursor
```

### 🤖 Automatic Real-Time Sync

**Continuous daemon mode** (watches all apps):
```bash
./mcp_config_sync.py --daemon
```

**Watch specific applications**:
```bash
./mcp_config_sync.py --daemon --watch Claude,VSCode,Cursor
```

**One-time watch with timeout**:
```bash
./mcp_config_sync.py --watch-once --timeout 30
```

**Custom debounce delay** (prevents rapid successive syncs):
```bash
./mcp_config_sync.py --daemon --debounce 5.0
```

### 🛡️ Safety Features

**Destructive operation protection** - warns when sync would remove existing MCP servers:
```bash
# Interactive confirmation (default behavior)
./mcp_config_sync.py --source empty_config.json

# Skip confirmation for automation
./mcp_config_sync.py --source empty_config.json --force
```

### Advanced Options

```bash
# Custom file path as source
./mcp_config_sync.py --source /path/to/custom/config.json

# View available applications
./mcp_config_sync.py --help
```

## 🏗️ How It Works

### Configuration Format Handling

The tool intelligently detects and converts between different MCP configuration formats:

1. **Claude Desktop Format**:
   ```json
   {
     "mcpServers": {
       "server-name": { "command": "...", "args": [...] }
     }
   }
   ```

2. **VSCode Format**:
   ```json
   {
     "other-settings": "...",
     "mcp": {
       "inputs": [],
       "servers": {
         "server-name": { "command": "...", "args": [...] }
       }
     }
   }
   ```

3. **Standard MCP Format**:
   ```json
   {
     "mcp": {
       "server_endpoint": "...",
       "servers": { ... }
     }
   }
   ```

### Automatic Sync Process

1. **File Monitoring**: Watches configuration file directories
2. **Change Detection**: Identifies which application's config changed
3. **Format Recognition**: Determines source configuration format
4. **Debounced Sync**: Waits for edits to complete (2-second default)
5. **Cross-Format Conversion**: Converts to each app's expected format
6. **Conflict Avoidance**: Prevents sync loops from self-triggered changes

## 🛠️ Improvements from Original Fork

This fork includes significant enhancements over the original:

### 🔥 Major New Features
- **Real-time file watching** with automatic synchronization
- **VSCode settings.json support** with format detection
- **Multi-format configuration handling** (4 different formats)
- **Intelligent conflict resolution** and debouncing
- **Daemon mode** for continuous monitoring

### 🧠 Enhanced Architecture
- **Format-specific handlers** for clean separation of concerns
- **Automatic format detection** and normalization
- **Extensible design** for easy addition of new applications
- **Robust error handling** and logging

### 🎯 Better User Experience
- **Comprehensive CLI options** for different use cases
- **Detailed reporting** with format information
- **Settings preservation** (no more overwriting app-specific configs)
- **Cross-platform compatibility** improvements

### 🔒 Reliability Improvements
- **Graceful error handling** for missing/corrupted files
- **Signal handling** for clean daemon shutdown
- **Thread-safe operations** for concurrent file access
- **Validation enhancements** for format-aware comparison
- **🛡️ Destructive operation protection** with user confirmation prompts

## 📋 Requirements

- **Python 3.7+**
- Dependencies listed in `requirements.txt`
- **macOS/Linux/Windows** (cross-platform)

## 🚦 Exit Codes

- `0`: Success
- `1`: Synchronization failed or validation errors

## 📄 License

MIT License