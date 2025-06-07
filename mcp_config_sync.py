import json
import os
from pathlib import Path
import logging
from datetime import datetime
import argparse
import sys
import time
import signal
import threading
from abc import ABC, abstractmethod
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ConfigFormatHandler(ABC):
    """Abstract base class for handling different MCP configuration formats."""
    
    @abstractmethod
    def detect_format(self, config_data: dict) -> bool:
        """Detect if this handler can process the given configuration format."""
        pass
    
    @abstractmethod
    def extract_mcp_config(self, config_data: dict) -> dict:
        """Extract MCP configuration from the app-specific format."""
        pass
    
    @abstractmethod
    def merge_mcp_config(self, existing_config: dict, mcp_config: dict) -> dict:
        """Merge MCP configuration back into the app-specific format."""
        pass
    
    @abstractmethod
    def get_format_name(self) -> str:
        """Get the name of this configuration format."""
        pass

class ClaudeDesktopHandler(ConfigFormatHandler):
    """Handler for Claude Desktop's mcpServers configuration format."""
    
    def detect_format(self, config_data: dict) -> bool:
        return 'mcpServers' in config_data
    
    def extract_mcp_config(self, config_data: dict) -> dict:
        """Convert Claude Desktop's mcpServers to normalized MCP config."""
        mcp_servers = config_data.get('mcpServers', {})
        
        # Create a normalized representation
        normalized_config = {
            'format': 'claude_desktop',
            'servers': mcp_servers
        }
        
        return normalized_config
    
    def merge_mcp_config(self, existing_config: dict, mcp_config: dict) -> dict:
        """Merge MCP config back into Claude Desktop format."""
        updated_config = existing_config.copy()
        
        # If the MCP config is in normalized format, extract servers
        if isinstance(mcp_config, dict) and 'servers' in mcp_config:
            updated_config['mcpServers'] = mcp_config['servers']
        elif isinstance(mcp_config, dict) and 'mcpServers' in mcp_config:
            updated_config['mcpServers'] = mcp_config['mcpServers']
        else:
            # Handle legacy format by wrapping in mcpServers
            updated_config['mcpServers'] = mcp_config
        
        return updated_config
    
    def get_format_name(self) -> str:
        return "Claude Desktop (mcpServers)"

class StandardMCPHandler(ConfigFormatHandler):
    """Handler for the standard MCP configuration format used by other apps."""
    
    def detect_format(self, config_data: dict) -> bool:
        return 'mcp' in config_data
    
    def extract_mcp_config(self, config_data: dict) -> dict:
        """Extract MCP configuration from standard format."""
        return config_data.get('mcp', {})
    
    def merge_mcp_config(self, existing_config: dict, mcp_config: dict) -> dict:
        """Merge MCP configuration into standard format."""
        updated_config = existing_config.copy()
        updated_config['mcp'] = mcp_config
        return updated_config
    
    def get_format_name(self) -> str:
        return "Standard MCP"

class VSCodeHandler(ConfigFormatHandler):
    """Handler for VSCode's settings.json mcp.servers configuration format."""
    
    def detect_format(self, config_data: dict) -> bool:
        return 'mcp' in config_data and isinstance(config_data['mcp'], dict) and 'servers' in config_data['mcp']
    
    def extract_mcp_config(self, config_data: dict) -> dict:
        """Extract MCP configuration from VSCode settings format."""
        mcp_section = config_data.get('mcp', {})
        servers = mcp_section.get('servers', {})
        
        # Create a normalized representation similar to Claude Desktop
        normalized_config = {
            'format': 'vscode',
            'servers': servers,
            'inputs': mcp_section.get('inputs', [])
        }
        
        return normalized_config
    
    def merge_mcp_config(self, existing_config: dict, mcp_config: dict) -> dict:
        """Merge MCP config back into VSCode settings format."""
        updated_config = existing_config.copy()
        
        # Initialize mcp section if it doesn't exist
        if 'mcp' not in updated_config:
            updated_config['mcp'] = {}
        
        # Handle different input formats
        if isinstance(mcp_config, dict) and 'servers' in mcp_config:
            # Normalized format from VSCode or Claude Desktop
            updated_config['mcp']['servers'] = mcp_config['servers']
            if 'inputs' in mcp_config:
                updated_config['mcp']['inputs'] = mcp_config['inputs']
        elif isinstance(mcp_config, dict) and 'mcpServers' in mcp_config:
            # Claude Desktop format
            updated_config['mcp']['servers'] = mcp_config['mcpServers']
        else:
            # Legacy format - wrap servers in VSCode structure
            updated_config['mcp']['servers'] = mcp_config
            
        # Ensure inputs exists
        if 'inputs' not in updated_config['mcp']:
            updated_config['mcp']['inputs'] = []
        
        return updated_config
    
    def get_format_name(self) -> str:
        return "VSCode (mcp.servers)"

class LegacyMCPHandler(ConfigFormatHandler):
    """Handler for legacy/empty configurations that need to be initialized."""
    
    def detect_format(self, config_data: dict) -> bool:
        # This handler accepts any config that doesn't match other formats
        return True
    
    def extract_mcp_config(self, config_data: dict) -> dict:
        """Return empty MCP config for legacy/empty configurations."""
        return {}
    
    def merge_mcp_config(self, existing_config: dict, mcp_config: dict) -> dict:
        """Merge MCP configuration using standard format."""
        updated_config = existing_config.copy()
        updated_config['mcp'] = mcp_config
        return updated_config
    
    def get_format_name(self) -> str:
        return "Legacy/Empty"

class MCPConfigWatcher(FileSystemEventHandler):
    """File system event handler for watching MCP configuration changes."""
    
    def __init__(self, synchronizer, debounce_delay=2.0):
        super().__init__()
        self.synchronizer = synchronizer
        self.debounce_delay = debounce_delay
        self.pending_syncs = {}
        self.lock = threading.Lock()
        
    def on_modified(self, event):
        if event.is_directory:
            return
            
        file_path = Path(event.src_path)
        
        # Check if this is one of our monitored config files
        source_app = None
        for app_name, config_path in self.synchronizer.CONFIG_FILES.items():
            try:
                if file_path.exists() and config_path.exists() and file_path.samefile(config_path):
                    source_app = app_name
                    break
            except (OSError, FileNotFoundError):
                # File might have been deleted or moved, skip
                continue
        
        if source_app:
            # Check if this change was caused by our own sync operation
            if self._is_sync_in_progress(source_app):
                logger.debug(f"Ignoring self-triggered change in {source_app} config")
                return
                
            logger.info(f"Detected external change in {source_app} config: {file_path}")
            self._schedule_sync(source_app, file_path)
    
    def _is_sync_in_progress(self, app_name):
        """Check if a sync operation is currently in progress for this app."""
        # Simple check - if there's a pending sync, assume we might be in the middle of it
        with self.lock:
            return app_name in self.pending_syncs
    
    def _schedule_sync(self, source_app, file_path):
        """Schedule a sync with debouncing to avoid rapid successive syncs."""
        with self.lock:
            # Cancel any existing timer for this app
            if source_app in self.pending_syncs:
                self.pending_syncs[source_app].cancel()
            
            # Schedule new sync
            timer = threading.Timer(
                self.debounce_delay, 
                self._execute_sync, 
                args=(source_app, file_path)
            )
            timer.start()
            self.pending_syncs[source_app] = timer
    
    def _execute_sync(self, source_app, file_path):
        """Execute the actual sync operation."""
        try:
            logger.info(f"Starting automatic sync from {source_app}")
            success = self.synchronizer.sync_from_file(source_app)
            
            if success:
                logger.info(f"Automatic sync from {source_app} completed successfully")
            else:
                logger.error(f"Automatic sync from {source_app} failed")
                
        except Exception as e:
            logger.error(f"Error during automatic sync from {source_app}: {e}")
        finally:
            # Clean up the timer reference
            with self.lock:
                self.pending_syncs.pop(source_app, None)

class MCPSyncDaemon:
    """Daemon for running continuous MCP configuration synchronization."""
    
    def __init__(self, synchronizer, watch_apps=None, debounce_delay=2.0):
        self.synchronizer = synchronizer
        self.watch_apps = watch_apps or list(synchronizer.CONFIG_FILES.keys())
        self.debounce_delay = debounce_delay
        self.observer = Observer()
        self.event_handler = MCPConfigWatcher(synchronizer, debounce_delay)
        self.running = False
        
    def start(self):
        """Start the file watching daemon."""
        logger.info("Starting MCP Config Sync Daemon")
        logger.info(f"Watching apps: {', '.join(self.watch_apps)}")
        logger.info(f"Debounce delay: {self.debounce_delay}s")
        
        # Setup file watchers for each monitored app
        watched_paths = set()
        for app_name in self.watch_apps:
            if app_name in self.synchronizer.CONFIG_FILES:
                config_path = self.synchronizer.CONFIG_FILES[app_name]
                
                # Watch the parent directory since the file might not exist yet
                watch_dir = config_path.parent
                if watch_dir not in watched_paths:
                    self.observer.schedule(
                        self.event_handler, 
                        str(watch_dir), 
                        recursive=False
                    )
                    watched_paths.add(watch_dir)
                    logger.info(f"Watching directory: {watch_dir}")
        
        # Start the observer
        self.observer.start()
        self.running = True
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info("Daemon started. Press Ctrl+C to stop.")
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()
    
    def stop(self):
        """Stop the file watching daemon."""
        if self.running:
            logger.info("Stopping MCP Config Sync Daemon")
            self.running = False
            self.observer.stop()
            self.observer.join()
            logger.info("Daemon stopped")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False

class MCPConfigSynchronizer:
    """Synchronizes MCP configuration across multiple application config files."""
    
    CONFIG_FILES = {
        'Cursor': Path.home() / '.cursor' / 'mcp.json',
        'Windsurf': Path.home() / '.codeium' / 'windsurf' / 'mcp_config.json',
        'Roocode-VSCode': Path.home() / 'Library' / 'Application Support' / 'Code' / 'User' / 
                  'globalStorage' / 'rooveterinaryinc.roo-cline' / 'settings' / 'cline_mcp_settings.json',
        'Roocode-Windsurf': Path.home() / 'Library' / 'Application Support' / 'Windsurf - Next' / 'User' /
                  'globalStorage' / 'rooveterinaryinc.roo-cline' / 'settings' / 'mcp_settings.json',
        'Claude': Path.home() / 'Library' / 'Application Support' / 'Claude' / 'claude_desktop_config.json',
        'VSCode': Path.home() / 'Library' / 'Application Support' / 'Code' / 'User' / 'settings.json'
    }
    
    # Configuration format handlers (order matters - most specific first)
    FORMAT_HANDLERS = [
        ClaudeDesktopHandler(),
        VSCodeHandler(),
        StandardMCPHandler(),
        LegacyMCPHandler()  # Fallback handler
    ]
    
    # Map applications to their preferred handlers
    APP_HANDLERS = {
        'Claude': ClaudeDesktopHandler(),
        'VSCode': VSCodeHandler(),
        'Cursor': StandardMCPHandler(),
        'Windsurf': StandardMCPHandler(),
        'Roocode-VSCode': StandardMCPHandler(),
        'Roocode-Windsurf': StandardMCPHandler()
    }
    
    DEFAULT_MCP_CONFIG = {
        'mcp_version': '1.0.0',
        'server_endpoint': 'http://localhost:8000/mcp',
        'auth': {
            'enabled': True,
            'method': 'jwt',
            'secret_key': 'your-secret-key-here'
        },
        'context_sources': {
            'vector_db': {
                'enabled': True,
                'type': 'pinecone',
                'endpoint': 'http://localhost:6333'
            },
            'structured_db': {
                'enabled': False,
                'type': 'postgresql',
                'connection_string': 'postgresql://user:password@localhost:5432/dbname'
            }
        },
        'performance': {
            'max_concurrent_requests': 100,
            'cache_ttl': 3600
        }
    }
    
    def __init__(self):
        self.config = self.DEFAULT_MCP_CONFIG.copy()
        self.sync_results = {}
    
    def detect_config_format(self, config_data: dict) -> ConfigFormatHandler:
        """Detect the appropriate format handler for the given configuration."""
        for handler in self.FORMAT_HANDLERS:
            if handler.detect_format(config_data):
                return handler
        # Should never reach here due to LegacyMCPHandler fallback
        return LegacyMCPHandler()
    
    def get_app_handler(self, app_name: str) -> ConfigFormatHandler:
        """Get the appropriate format handler for a specific application."""
        return self.APP_HANDLERS.get(app_name, StandardMCPHandler())
    
    def ensure_directories(self):
        """Ensure all parent directories for config files exist."""
        for config_path in self.CONFIG_FILES.values():
            config_path.parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"Ensured directory exists: {config_path.parent}")
    
    def load_existing_config(self, config_path):
        """Load existing configuration from a file if it exists."""
        try:
            if config_path.exists():
                with open(config_path, 'r') as f:
                    return json.load(f)
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse config at {config_path}: {e}")
            # Return None to indicate a parsing error, not just an empty config
            return None
        except Exception as e:
            logger.error(f"Error loading config at {config_path}: {e}")
            return None
    
    def merge_configs(self, existing_config, new_config):
        """Merge existing config with new config, preserving existing values where applicable."""
        def deep_merge(d1, d2):
            for key, value in d2.items():
                if isinstance(value, dict) and key in d1:
                    d1[key] = deep_merge(d1.get(key, {}), value)
                else:
                    d1[key] = value
            return d1
        
        return deep_merge(existing_config.copy(), new_config)
    
    def update_configs(self, custom_config=None):
        """Update all configuration files with the specified MCP configuration."""
        self.ensure_directories()
        
        if custom_config:
            self.config = self.merge_configs(self.config, custom_config)
        
        results = {}
        for app_name, config_path in self.CONFIG_FILES.items():
            try:
                # Load existing config to preserve any app-specific settings
                existing_config = self.load_existing_config(config_path)
                
                # If parsing failed, skip this config
                if existing_config is None:
                    logger.error(f"Skipping update for {app_name} due to parsing error")
                    results[app_name] = {
                        'success': False, 
                        'path': config_path,
                        'error': 'Failed to parse existing config',
                        'action': 'skipped'
                    }
                    continue
                
                # Get file status before update
                file_existed = config_path.exists()
                
                # Get the appropriate handler for this app
                handler = self.get_app_handler(app_name)
                
                # Merge with new MCP config using format-specific handler
                updated_config = handler.merge_mcp_config(existing_config, self.config)
                
                # Write updated config
                with open(config_path, 'w') as f:
                    json.dump(updated_config, f, indent=2)
                
                # Record result
                action = 'updated' if file_existed else 'created'
                logger.info(f"Successfully {action} config for {app_name} at {config_path} using {handler.get_format_name()} format")
                results[app_name] = {
                    'success': True, 
                    'path': config_path,
                    'action': action,
                    'size': config_path.stat().st_size,
                    'format': handler.get_format_name()
                }
                
            except Exception as e:
                logger.error(f"Failed to update config for {app_name} at {config_path}: {e}")
                results[app_name] = {
                    'success': False, 
                    'path': config_path,
                    'error': str(e),
                    'action': 'failed'
                }
        
        return results
    
    def validate_configs(self, reference_config=None):
        """Validate that all configuration files are in sync and properly formatted."""
        if reference_config is None:
            reference_config = self.config
        
        all_in_sync = True
        validation_results = {}
        
        for app_name, config_path in self.CONFIG_FILES.items():
            if not config_path.exists():
                logger.warning(f"Config file missing for {app_name} at {config_path}")
                validation_results[app_name] = {'in_sync': False, 'reason': 'missing'}
                all_in_sync = False
                continue
                
            config = self.load_existing_config(config_path)
            if config is None:
                logger.warning(f"Config file for {app_name} at {config_path} could not be parsed")
                validation_results[app_name] = {'in_sync': False, 'reason': 'parse_error'}
                all_in_sync = False
                continue
            
            # Use format-specific handler to extract MCP config for comparison
            handler = self.detect_config_format(config)
            mcp_config = handler.extract_mcp_config(config)
            
            # For Claude Desktop format, we need to compare the servers structure
            if isinstance(handler, ClaudeDesktopHandler):
                # Extract servers from both configurations for comparison
                ref_servers = reference_config.get('servers', {}) if isinstance(reference_config, dict) and 'servers' in reference_config else {}
                app_servers = mcp_config.get('servers', {}) if isinstance(mcp_config, dict) and 'servers' in mcp_config else {}
                
                # If reference config is in legacy format, we can't do meaningful comparison
                if not ref_servers and reference_config:
                    logger.info(f"Skipping validation for {app_name} - reference config is in legacy format, app uses Claude Desktop format")
                    validation_results[app_name] = {'in_sync': True, 'reason': 'format_mismatch_skip'}
                    continue
                
                # Compare server configurations
                is_in_sync = app_servers == ref_servers
                if not is_in_sync:
                    mismatched_keys = ['servers (content mismatch)']
                else:
                    mismatched_keys = []
            else:
                # Standard validation for other formats
                is_in_sync = True
                mismatched_keys = []
                
                def check_nested_dict(ref_dict, app_dict, path=""):
                    nonlocal is_in_sync, mismatched_keys
                    for key, ref_value in ref_dict.items():
                        if key not in app_dict:
                            is_in_sync = False
                            mismatched_keys.append(f"{path}{key} (missing)")
                            continue
                            
                        app_value = app_dict[key]
                        if isinstance(ref_value, dict) and isinstance(app_value, dict):
                            check_nested_dict(ref_value, app_value, f"{path}{key}.")
                        elif ref_value != app_value:
                            is_in_sync = False
                            mismatched_keys.append(f"{path}{key} (value mismatch)")
                
                check_nested_dict(reference_config, mcp_config)
            
            if not is_in_sync:
                logger.warning(f"Config mismatch detected for {app_name} at {config_path}")
                validation_results[app_name] = {
                    'in_sync': False, 
                    'reason': 'mismatch',
                    'mismatched_keys': mismatched_keys,
                    'format': handler.get_format_name()
                }
                all_in_sync = False
            else:
                validation_results[app_name] = {
                    'in_sync': True,
                    'format': handler.get_format_name()
                }
                
        if all_in_sync:
            logger.info("All configuration files are in sync with the reference configuration")
        
        return all_in_sync, validation_results
    
    def print_report(self, sync_results, validation_results, source=None):
        """Print a detailed report of the synchronization operation."""
        # Determine overall status
        all_success = all(result.get('success', False) for result in sync_results.values())
        all_in_sync = all(result.get('in_sync', False) for result in validation_results.values())
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        overall_status = "SUCCESS" if all_success and all_in_sync else "PARTIAL_SUCCESS" if all_success else "FAILED"
        
        # Count successful configurations
        success_count = sum(1 for result in sync_results.values() if result.get('success', False))
        total_count = len(sync_results)
        
        # Get server endpoint for reference
        server_endpoint = self.config.get('server_endpoint', 'Unknown')
        
        # Print report header
        print("\n" + "=" * 80)
        print(f"MCP CONFIGURATION SYNCHRONIZATION REPORT - {timestamp}")
        print("=" * 80)
        print(f"Status: {overall_status}")
        if source:
            print(f"Source: {source}")
        print(f"Apps Configured: {success_count}/{total_count}")
        print(f"Server Endpoint: {server_endpoint}")
        print("-" * 80)
        print("DETAILS:")
        
        # Print details for each app
        for app_name, result in sync_results.items():
            success = result.get('success', False)
            status_icon = "✓" if success else "✗"
            
            print(f"{status_icon} {app_name}:")
            print(f"   Path: {result['path']}")
            
            if success:
                print(f"   Action: {result['action']}")
                print(f"   Size: {result['size']} bytes")
                
                # Add validation status if available
                validation = validation_results.get(app_name, {})
                if validation:
                    in_sync = validation.get('in_sync', False)
                    sync_icon = "✓" if in_sync else "✗"
                    
                    if in_sync:
                        sync_status = "in_sync"
                    else:
                        reason = validation.get('reason', 'unknown')
                        sync_status = f"out_of_sync ({reason})"
                        
                        # Add detailed mismatch information if available
                        if reason == 'mismatch' and 'mismatched_keys' in validation:
                            mismatched_keys = validation['mismatched_keys']
                            if len(mismatched_keys) > 0:
                                print(f"   Validation: {sync_icon} {sync_status}")
                                print(f"   Mismatched keys:")
                                for key in mismatched_keys[:5]:  # Show first 5 mismatches to avoid overwhelming
                                    print(f"      - {key}")
                                if len(mismatched_keys) > 5:
                                    print(f"      - ...and {len(mismatched_keys) - 5} more")
                                continue
                    
                    print(f"   Validation: {sync_icon} {sync_status}")
            else:
                print(f"   Action: {result.get('action', 'failed')}")
                print(f"   Error: {result.get('error', 'Unknown error')}")
            
            print()
        
        print("=" * 80)
        return overall_status
    
    def sync_from_file(self, app_name_or_path):
        """Synchronize MCP configuration from a specified source file."""
        # Determine source file path
        source_path = None
        source_name = None
        
        if app_name_or_path in self.CONFIG_FILES:
            source_name = app_name_or_path
            source_path = self.CONFIG_FILES[app_name_or_path]
        else:
            # Treat as direct file path
            source_path = Path(app_name_or_path)
            source_name = str(source_path)
        
        if not source_path.exists():
            logger.error(f"Source file does not exist: {source_path}")
            return False
        
        # Load configuration from source
        source_config = self.load_existing_config(source_path)
        if source_config is None:
            logger.error(f"Failed to parse source configuration at {source_path}")
            return False
        
        # Detect format and extract MCP configuration using appropriate handler
        handler = self.detect_config_format(source_config)
        mcp_config = handler.extract_mcp_config(source_config)
        
        if not mcp_config:
            logger.error(f"No MCP configuration found in {source_path}")
            return False
        
        logger.info(f"Loaded reference MCP configuration from {source_name} using {handler.get_format_name()} format")
        
        # Update config with the loaded MCP configuration
        self.config = mcp_config
        
        # Apply to all configs
        sync_results = self.update_configs()
        
        # Validate configs
        all_in_sync, validation_results = self.validate_configs()
        
        # Generate report
        status = self.print_report(sync_results, validation_results, source=source_name)
        
        if status == "SUCCESS":
            logger.info(f"MCP configuration synchronization from source completed successfully")
            return True
        else:
            logger.error(f"MCP configuration synchronization from source completed with issues")
            return False

def main():
    """Main function to synchronize MCP configurations."""
    parser = argparse.ArgumentParser(description="Synchronize MCP configuration across multiple applications")
    parser.add_argument('--source', type=str, help="Source app or file path to sync from")
    parser.add_argument('--daemon', action='store_true', help="Run in daemon mode to continuously watch for changes")
    parser.add_argument('--watch', type=str, help="Comma-separated list of apps to watch (default: all)")
    parser.add_argument('--debounce', type=float, default=2.0, help="Debounce delay in seconds (default: 2.0)")
    parser.add_argument('--watch-once', action='store_true', help="Watch for changes once, then exit")
    parser.add_argument('--timeout', type=int, help="Timeout in seconds for --watch-once mode")
    args = parser.parse_args()
    
    synchronizer = MCPConfigSynchronizer()
    
    # Parse watch apps if specified
    watch_apps = None
    if args.watch:
        watch_apps = [app.strip() for app in args.watch.split(',')]
        # Validate app names
        invalid_apps = [app for app in watch_apps if app not in synchronizer.CONFIG_FILES]
        if invalid_apps:
            logger.error(f"Invalid app names: {', '.join(invalid_apps)}")
            logger.error(f"Valid apps: {', '.join(synchronizer.CONFIG_FILES.keys())}")
            sys.exit(1)
    
    if args.daemon or args.watch_once:
        # Run in daemon/watch mode
        daemon = MCPSyncDaemon(synchronizer, watch_apps, args.debounce)
        
        if args.watch_once:
            # Watch once with optional timeout
            logger.info("Starting one-time watch mode")
            if args.timeout:
                logger.info(f"Will timeout after {args.timeout} seconds")
            
            try:
                daemon.observer.start()
                start_time = time.time()
                
                while True:
                    time.sleep(0.1)
                    if args.timeout and (time.time() - start_time) >= args.timeout:
                        logger.info("Timeout reached, exiting watch mode")
                        break
            except KeyboardInterrupt:
                logger.info("Watch mode interrupted by user")
            finally:
                daemon.observer.stop()
                daemon.observer.join()
        else:
            # Run as continuous daemon
            daemon.start()
        
        sys.exit(0)
    
    elif args.source:
        # Sync from specified source
        success = synchronizer.sync_from_file(args.source)
        if success:
            logger.info("MCP configuration synchronization completed successfully")
            sys.exit(0)
        else:
            logger.error("MCP configuration synchronization failed")
            sys.exit(1)
    else:
        # Use default config with custom overrides
        custom_config = {
            'server_endpoint': 'https://mcp.example.com:8443/mcp',
            'auth': {
                'secret_key': 'new-secret-key-12345'
            },
            'context_sources': {
                'vector_db': {
                    'type': 'weaviate',
                    'endpoint': 'http://weaviate:8080'
                }
            }
        }
        
        # Update configurations
        sync_results = synchronizer.update_configs(custom_config)
        
        # Validate configurations
        all_in_sync, validation_results = synchronizer.validate_configs()
        
        # Print report
        status = synchronizer.print_report(sync_results, validation_results)
        
        if status == "SUCCESS":
            logger.info("MCP configuration synchronization completed successfully")
            sys.exit(0)
        else:
            logger.error("MCP configuration synchronization failed due to mismatches")
            sys.exit(1)

if __name__ == "__main__":
    main()