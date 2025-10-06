import requests
import json
import time
import logging
from datetime import datetime
import os
import argparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MetaUpdChecker:
    def __init__(self, config_file='config.json', games_file='games.json'):
        self.config = self.load_config(config_file)
        self.games = self.load_games(games_file)
        self.last_versions = {}
        self.load_previous_versions()
        
    def load_config(self, config_file):
        """Load configuration from JSON file"""
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                
            # Ensure all required fields are present
            required_fields = ['discord_webhook_url', 'meta_access_token', 'check_interval']
            for field in required_fields:
                if field not in config:
                    if field == 'check_interval':
                        config[field] = 3600  # Default to 1 hour
                    else:
                        config[field] = f"YOUR_{field.upper()}_HERE"
                    logging.warning(f"Missing {field} in config, using default: {config[field]}")
            
            return config
        except FileNotFoundError:
            logging.error(f"Config file {config_file} not found!")
            # Create default config if doesn't exist
            default_config = {
                "discord_webhook_url": "YOUR_DISCORD_WEBHOOK_URL_HERE",
                "meta_access_token": "YOUR_META_ACCESS_TOKEN_HERE", 
                "check_interval": 3600
            }
            with open(config_file, 'w') as f:
                json.dump(default_config, f, indent=4)
            logging.info(f"Created default {config_file}. Please update it with your credentials.")
            return default_config
        except json.JSONDecodeError:
            logging.error(f"Invalid JSON in {config_file}!")
            raise
    
    def load_games(self, games_file):
        """Load games data from JSON file"""
        try:
            with open(games_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logging.error(f"Games file {games_file} not found!")
            raise
        except json.JSONDecodeError:
            logging.error(f"Invalid JSON in {games_file}!")
            raise

    def load_previous_versions(self):
        """Load previous versions from file"""
        try:
            with open('versions.json', 'r') as f:
                self.last_versions = json.load(f)
        except FileNotFoundError:
            logging.info("No previous versions found. Starting fresh.")
            self.last_versions = {}

    def save_versions(self):
        """Save current versions to file"""
        with open('versions.json', 'w') as f:
            json.dump(self.last_versions, f, indent=4)

    def get_app_info(self, appid):
        """Get app information from Meta API"""
        url = f"https://graph.oculus.com/apps/{appid}"
        params = {
            'access_token': self.config.get('meta_access_token', ''),
            'fields': 'id,name,version_name,version_code,release_date,updated_time'
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                logging.error(f"API Error for appid {appid}: {response.status_code}")
                return None
        except requests.RequestException as e:
            logging.error(f"Request failed for appid {appid}: {e}")
            return None
    
    def send_discord_webhook(self, app_data, old_version=None):
        """Send update notification to Discord webhook"""
        webhook_url = self.config.get('discord_webhook_url')
        if not webhook_url or webhook_url == "YOUR_DISCORD_WEBHOOK_URL_HERE":
            logging.error("No valid Discord webhook URL configured!")
            return False
        
        app_name = app_data.get('name', 'Unknown App')
        current_version = app_data.get('version_name', 'Unknown')
        version_code = app_data.get('version_code', 'Unknown')
        update_time = app_data.get('updated_time', '')
        
        # Format the embed message
        embed = {
            "title": f"🚀 {app_name} Update Detected!",
            "color": 0x00ff00,
            "fields": [
                {
                    "name": "App ID",
                    "value": app_data.get('id', 'Unknown'),
                    "inline": True
                },
                {
                    "name": "Current Version",
                    "value": current_version,
                    "inline": True
                },
                {
                    "name": "Version Code",
                    "value": str(version_code),
                    "inline": True
                }
            ],
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {
                "text": "Meta Update Checker"
            }
        }
        
        # Add previous version if available
        if old_version:
            embed["fields"].append({
                "name": "Previous Version",
                "value": old_version,
                "inline": True
            })
        
        payload = {
            "embeds": [embed],
            "username": "Meta Update Bot",
            "avatar_url": "https://cdn-icons-png.flaticon.com/512/5968/5968764.png"
        }
        
        try:
            response = requests.post(webhook_url, json=payload, timeout=10)
            if response.status_code in [200, 204]:
                logging.info(f"Discord notification sent for {app_name}")
                return True
            else:
                logging.error(f"Discord webhook failed: {response.status_code}")
                return False
        except requests.RequestException as e:
            logging.error(f"Failed to send Discord webhook: {e}")
            return False
    
    def check_updates(self):
        """Check all games for updates"""
        logging.info("Starting update check...")
        updates_detected = 0
        
        for game in self.games['games']:
            appid = game['appid']
            app_name = game.get('name', 'Unknown')
            
            logging.info(f"Checking {app_name} (ID: {appid})")
            
            app_info = self.get_app_info(appid)
            if app_info:
                current_version = app_info.get('version_name')
                stored_version = self.last_versions.get(appid)
                
                if current_version:
                    if stored_version and stored_version != current_version:
                        logging.info(f"Update detected for {app_name}: {stored_version} -> {current_version}")
                        if self.send_discord_webhook(app_info, stored_version):
                            updates_detected += 1
                    
                    # Update stored version
                    self.last_versions[appid] = current_version
                else:
                    logging.warning(f"Could not get version for {app_name}")
                
                # Small delay to avoid rate limiting
                time.sleep(1)
        
        # Save versions after check
        self.save_versions()
        logging.info(f"Update check completed. Detected {updates_detected} updates.")
        return updates_detected
    
    def run(self):
        """Main loop"""
        check_interval = self.config.get('check_interval', 3600)
        logging.info(f"Meta Update Checker started! Check interval: {check_interval} seconds")
        
        # Initial check to populate versions
        self.check_updates()
        
        # Main loop
        while True:
            try:
                self.check_updates()
                sleep_time = check_interval
                logging.info(f"Waiting {sleep_time} seconds until next check...")
                time.sleep(sleep_time)
            except KeyboardInterrupt:
                logging.info("Update checker stopped by user")
                break
            except Exception as e:
                logging.error(f"Unexpected error: {e}")
                time.sleep(60)  # Wait 1 minute before retrying

    def run_single(self):
        """Run a single check and exit"""
        logging.info("Running single update check...")
        updates = self.check_updates()
        logging.info("Single check completed!")
        return updates

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--single-run', action='store_true', help='Run once and exit')
    args = parser.parse_args()
    
    checker = MetaUpdChecker()
    
    if args.single_run:
        checker.run_single()
    else:
        checker.run()
