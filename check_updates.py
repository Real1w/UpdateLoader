name: Meta Quest Update Checker

on:
  schedule:
    # Runs every 30 minutes
    - cron: '*/30 * * * *'
  workflow_dispatch: # Allows manual trigger

jobs:
  check-updates:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout repository
        uses: actions/checkout@v3
        
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
          
      - name: Install dependencies
        run: |
          pip install requests
          
      - name: Check for updates
        env:
          DISCORD_WEBHOOK: ${{ secrets.DISCORD_WEBHOOK }}
        run: python check_updates.py
        
      - name: Commit updated versions
        run: |
          git config --local user.email "github-actions[bot]@users.noreply.github.com"
          git config --local user.name "github-actions[bot]"
          git add versions.json
          git diff --quiet && git diff --staged --quiet || git commit -m "Update app versions"
          
      - name: Push changes
        uses: ad-m/github-push-action@master
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          branch: ${{ github.ref }}


---
# FILE: check_updates.py

import requests
import json
import os
from datetime import datetime

APP_IDS = [
    "1234567890123456",
    "2345678901234567",
    "3456789012345678",
]

DISCORD_WEBHOOK = os.getenv('DISCORD_WEBHOOK')
VERSIONS_FILE = 'versions.json'

def load_versions():
    """Load stored versions from file"""
    if os.path.exists(VERSIONS_FILE):
        with open(VERSIONS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_versions(versions):
    """Save versions to file"""
    with open(VERSIONS_FILE, 'w') as f:
        json.dump(versions, f, indent=2)

def get_app_info(app_id):
    """Fetch app information from Meta's API"""
    try:
        url = f"https://graph.oculus.com/graphql"
        
        headers = {
            'Content-Type': 'application/json',
        }
        
        query = {
            "query": f"""
            query {{
              node(id: "{app_id}") {{
                ... on Application {{
                  id
                  displayName
                  latest_supported_binary {{
                    version
                    version_code
                  }}
                }}
              }}
            }}
            """
        }
        
        response = requests.post(url, json=query, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if 'data' in data and 'node' in data['data']:
            node = data['data']['node']
            if node and 'displayName' in node:
                return {
                    'name': node['displayName'],
                    'version': node.get('latest_supported_binary', {}).get('version', 'Unknown'),
                    'version_code': node.get('latest_supported_binary', {}).get('version_code', 'Unknown')
                }
    except Exception as e:
        print(f"Error fetching app {app_id}: {str(e)}")
    
    return None

def send_discord_notification(app_id, app_name, old_version, new_version):
    """Send update notification to Discord webhook"""
    if not DISCORD_WEBHOOK:
        print("No Discord webhook configured")
        return
    
    embed = {
        "embeds": [{
            "title": "Meta App Update Checker",
            "description": f"**{app_name}** has been updated!",
            "color": 3447003,  
            "fields": [
                {
                    "name": "App ID",
                    "value": f"`{app_id}`",
                    "inline": False
                },
                {
                    "name": "Previous Version",
                    "value": f"`{old_version}`",
                    "inline": True
                },
                {
                    "name": "New Version",
                    "value": f"`{new_version}`",
                    "inline": True
                }
            ],
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {
                "text": "Meta Quest Update Checker"
            }
        }]
    }
    
    try:
        response = requests.post(DISCORD_WEBHOOK, json=embed, timeout=10)
        response.raise_for_status()
        print(f"Discord notification sent for {app_name}")
    except Exception as e:
        print(f"Error sending Discord notification: {str(e)}")

def main():
    print("Starting Meta Quest update check...")
    
    stored_versions = load_versions()
    current_versions = {}
    
    for app_id in APP_IDS:
        print(f"Checking app {app_id}...")
        
        app_info = get_app_info(app_id)
        
        if app_info:
            app_name = app_info['name']
            current_version = app_info['version']
            version_code = app_info['version_code']
            
            print(f"Found: {app_name} - Version {current_version}")
            
            current_versions[app_id] = {
                'name': app_name,
                'version': current_version,
                'version_code': version_code,
                'last_checked': datetime.utcnow().isoformat()
            }
            
            if app_id in stored_versions:
                old_version = stored_versions[app_id].get('version', 'Unknown')
                if old_version != current_version:
                    print(f"Update detected: {old_version} -> {current_version}")
                    send_discord_notification(app_id, app_name, old_version, current_version)
            else:
                print(f"First time tracking {app_name}")
                send_discord_notification(app_id, app_name, "N/A", current_version)
        else:
            print(f"Could not fetch info for app {app_id}")
    
    save_versions(current_versions)
    print("Update check complete!")

if __name__ == "__main__":
    main()


---
# FILE: versions.json

{}
