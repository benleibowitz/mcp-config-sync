import json
import os
from pathlib import Path
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MCPConfigSynchronizer:
    """Synchronizes MCP configuration across multiple application config files."""
    
    CONFIG_FILES = {
        'Cursor': Path.home() / '.cursor' / 'mcp.json',
        'Windsurf': Path.home() / '.codeium' / 'windsurf' / 'mcp_config.json',
        'Roocode': Path.home() / 'Library' / 'Application Support' / 'Code' / 'User' / 
                  'globalStorage' / 'rooveterinaryinc.roo-cline' / 'settings' / 'cline_mcp_settings.json',
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
            return {}
        except Exception as e:
            logger.error(f"Error loading config at {config_path}: {e}")
            return {}
    
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
        self.sync_results = {}
        
        if custom_config:
            self.config = self.merge_configs(self.config, custom_config)
        
        for app_name, config_path in self.CONFIG_FILES.items():
            try:
                # Track if file existed before
                file_existed = config_path.exists()
                
                # Load existing config to preserve any app-specific settings
                existing_config = self.load_existing_config(config_path)
                
                # Merge with new MCP config
                updated_config = self.merge_configs(existing_config, {'mcp': self.config})
                
                # Write updated config
                with open(config_path, 'w') as f:
                    json.dump(updated_config, f, indent=2)
                
                self.sync_results[app_name] = {
                    'status': 'success',
                    'path': str(config_path),
                    'action': 'updated' if file_existed else 'created',
                    'size': os.path.getsize(config_path)
                }
                
                logger.info(f"Successfully updated config for {app_name} at {config_path}")
                
            except Exception as e:
                self.sync_results[app_name] = {
                    'status': 'failed',
                    'path': str(config_path),
                    'error': str(e)
                }
                logger.error(f"Failed to update config for {app_name} at {config_path}: {e}")
    
    def sync_from_file(self, app_name_or_path):
        """Loads MCP config from a specific file and syncs it to all other config files.
        
        Args:
            app_name_or_path: Either an app name (key in CONFIG_FILES) or a direct path
                             to a config file.
        
        Returns:
            bool: True if synchronization was successful, False otherwise.
        """
        self.sync_results = {}
        source_path = None
        source_name = "Unknown"
        
        # Determine the source file path
        if app_name_or_path in self.CONFIG_FILES:
            source_path = self.CONFIG_FILES[app_name_or_path]
            source_name = app_name_or_path
        else:
            try:
                source_path = Path(app_name_or_path)
                source_name = f"Custom ({source_path})"
            except:
                logger.error(f"Invalid source: {app_name_or_path}")
                return False
        
        # Check if source file exists
        if not source_path.exists():
            logger.error(f"Source file does not exist: {source_path}")
            return False
        
        try:
            # Load the source config
            source_config = self.load_existing_config(source_path)
            mcp_config = source_config.get('mcp', {})
            
            if not mcp_config:
                logger.error(f"No MCP configuration found in {source_path}")
                return False
            
            logger.info(f"Loaded reference MCP configuration from {source_name}")
            
            # Set as our reference and update all configs
            self.config = mcp_config
            
            # Update all configs (including the source, which should remain unchanged)
            self.update_configs()
            
            # Validate all configs
            is_valid = self.validate_configs()
            
            # Generate and print report
            report = self.generate_report()
            # Add source info to report
            report['source'] = source_name
            self.print_report(report)
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Failed to sync from {source_path}: {e}")
            return False
    
    def validate_configs(self, reference_config=None):
        """Validate that all configuration files are in sync and properly formatted.
        
        Args:
            reference_config: Optional reference configuration to use for validation.
                             If None, uses the current in-memory config.
        """
        validation_results = {}
        
        # Use the in-memory config as the reference if not explicitly provided
        if reference_config is None:
            reference_config = self.config
        
        for app_name, config_path in self.CONFIG_FILES.items():
            if not config_path.exists():
                validation_results[app_name] = {'status': 'missing'}
                logger.warning(f"Config file missing for {app_name} at {config_path}")
                continue
                
            config = self.load_existing_config(config_path)
            mcp_config = config.get('mcp', {})
            
            if mcp_config == reference_config:
                validation_results[app_name] = {'status': 'in_sync'}
            else:
                validation_results[app_name] = {'status': 'out_of_sync'}
                logger.warning(f"Config mismatch detected for {app_name} at {config_path}")
        
        # Update sync results with validation information
        for app_name, result in validation_results.items():
            if app_name in self.sync_results:
                self.sync_results[app_name]['validation'] = result['status']
        
        all_in_sync = all(r['status'] == 'in_sync' for r in validation_results.values())
        
        if all_in_sync:
            logger.info("All configuration files are in sync with the reference configuration")
        
        return all_in_sync
    
    def generate_report(self):
        """Generate a detailed report of the synchronization results."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        report = {
            'timestamp': timestamp,
            'overall_status': 'success' if all(r.get('status') == 'success' for r in self.sync_results.values()) else 'partial_failure',
            'apps_configured': len([r for r in self.sync_results.values() if r.get('status') == 'success']),
            'total_apps': len(self.CONFIG_FILES),
            'server_endpoint': self.config.get('server_endpoint'),
            'results': self.sync_results
        }
        
        return report
    
    def print_report(self, report):
        """Print a formatted report to the console."""
        print("\n" + "="*80)
        print(f"MCP CONFIGURATION SYNCHRONIZATION REPORT - {report['timestamp']}")
        print("="*80)
        print(f"Status: {report['overall_status'].upper()}")
        
        # Print source if available
        if 'source' in report:
            print(f"Source: {report['source']}")
            
        print(f"Apps Configured: {report['apps_configured']}/{report['total_apps']}")
        print(f"Server Endpoint: {report['server_endpoint']}")
        print("-"*80)
        print("DETAILS:")
        
        for app_name, result in report['results'].items():
            status_symbol = "✓" if result.get('status') == 'success' else "✗"
            print(f"{status_symbol} {app_name}:")
            print(f"   Path: {result.get('path')}")
            
            if result.get('status') == 'success':
                print(f"   Action: {result.get('action')}")
                print(f"   Size: {result.get('size')} bytes")
                validation = result.get('validation', 'unknown')
                validation_symbol = "✓" if validation == 'in_sync' else "✗"
                print(f"   Validation: {validation_symbol} {validation}")
            else:
                print(f"   Error: {result.get('error')}")
                
            print()
            
        print("="*80)

def main():
    """Main function to synchronize MCP configurations."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Synchronize MCP configuration across multiple applications')
    parser.add_argument('--source', help='Source app name or config file path to sync from')
    args = parser.parse_args()
    
    synchronizer = MCPConfigSynchronizer()
    
    if args.source:
        # Sync from the specified source
        if synchronizer.sync_from_file(args.source):
            logger.info("MCP configuration synchronization from source completed successfully")
        else:
            logger.error("MCP configuration synchronization from source failed")
    else:
        # Default behavior - update with custom config
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
        synchronizer.update_configs(custom_config)
        
        # Validate configurations
        sync_successful = synchronizer.validate_configs()
        
        # Generate and print detailed report
        report = synchronizer.generate_report()
        synchronizer.print_report(report)
        
        if sync_successful:
            logger.info("MCP configuration synchronization completed successfully")
        else:
            logger.error("MCP configuration synchronization failed due to mismatches")

if __name__ == "__main__":
    main()