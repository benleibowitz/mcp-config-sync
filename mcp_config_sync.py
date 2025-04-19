import json
import os
from pathlib import Path
import logging
from datetime import datetime
import argparse
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MCPConfigSynchronizer:
    """Synchronizes MCP configuration across multiple application config files."""
    
    CONFIG_FILES = {
        'Cursor': Path.home() / '.cursor' / 'mcp.json',
        'Windsurf': Path.home() / '.codeium' / 'windsurf' / 'mcp_config.json',
        'Roocode-VSCode': Path.home() / 'Library' / 'Application Support' / 'Code' / 'User' / 
                  'globalStorage' / 'rooveterinaryinc.roo-cline' / 'settings' / 'cline_mcp_settings.json',
        'Roocode-Windsurf': Path.home() / 'Library' / 'Application Support' / 'Windsurf - Next' / 'User' /
                  'globalStorage' / 'rooveterinaryinc.roo-cline' / 'settings' / 'mcp_settings.json',
        'Claude': Path.home() / 'Library' / 'Application Support' / 'Claude' / 'claude_desktop_config.json'
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
                
                # Merge with new MCP config
                updated_config = self.merge_configs(existing_config, {'mcp': self.config})
                
                # Write updated config
                with open(config_path, 'w') as f:
                    json.dump(updated_config, f, indent=2)
                
                # Record result
                action = 'updated' if file_existed else 'created'
                logger.info(f"Successfully {action} config for {app_name} at {config_path}")
                results[app_name] = {
                    'success': True, 
                    'path': config_path,
                    'action': action,
                    'size': config_path.stat().st_size
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
                
            mcp_config = config.get('mcp', {})
            
            # Check if all fields in the reference config exist with the same values in the app config
            # This allows app configs to have additional fields that aren't in the reference
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
                    'mismatched_keys': mismatched_keys
                }
                all_in_sync = False
            else:
                validation_results[app_name] = {'in_sync': True}
                
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
        
        mcp_config = source_config.get('mcp')
        if not mcp_config:
            logger.error(f"No MCP configuration found in {source_path}")
            return False
        
        logger.info(f"Loaded reference MCP configuration from {source_name}")
        
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
    args = parser.parse_args()
    
    synchronizer = MCPConfigSynchronizer()
    
    if args.source:
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