import os
import requests
import yaml
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Load configuration
script_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(script_dir, 'config.yaml')
with open(config_path, 'r') as config_file:
    config = yaml.safe_load(config_file)

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_OWNER = config['github']['owner']
GITHUB_REPO = config['github']['repo']
GITHUB_API_BASE = config['github']['api_base']
OBSIDIAN_VAULT_ROOT = config['obsidian']['vault_root']
SYNC_PATH = config['obsidian']['sync_path'].format(repo=GITHUB_REPO)
WHITELIST_FILENAME = config['whitelist']['filename'].format(repo=GITHUB_REPO)

# Calculate full paths
OBSIDIAN_SYNC_PATH = os.path.join(OBSIDIAN_VAULT_ROOT, SYNC_PATH)
WHITELIST_PATH = os.path.join(OBSIDIAN_SYNC_PATH, WHITELIST_FILENAME)

headers = {
    'Authorization': f'token {GITHUB_TOKEN}',
    'Accept': 'application/vnd.github.v3+json'
}

def get_repo_structure(path=''):
    url = f'{GITHUB_API_BASE}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{path}'
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def create_whitelist_note(repo_structure, repo_path=''):
    content = f"# Whitelist for {GITHUB_REPO}\n\n"
    for item in repo_structure:
        if item['type'] == 'file':
            content += f"- [ ] {os.path.join(repo_path, item['name']).replace(os.sep, '/')}\n"
        elif item['type'] == 'dir':
            content += f"\n## {item['name']}\n"
            sub_structure = get_repo_structure(item['path'])
            content += create_whitelist_note(sub_structure, item['path'])
    return content

def main():
    repo_structure = get_repo_structure()
    whitelist_content = create_whitelist_note(repo_structure)
    
    os.makedirs(os.path.dirname(WHITELIST_PATH), exist_ok=True)
    with open(WHITELIST_PATH, 'w') as f:
        f.write(whitelist_content)
    
    print(f"Whitelist note created at: {WHITELIST_PATH}")

if __name__ == '__main__':
    main()