import os
import requests
import base64
import yaml
import logging
from datetime import datetime
from dotenv import load_dotenv

# Set up logging
log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'github_sync.log')
logging.basicConfig(filename=log_file_path, level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Function to log and print messages
def log_and_print(message, level=logging.INFO):
    logging.log(level, message)
    print(message)

# Load environment variables from .env file
load_dotenv()

# Load configuration
script_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(script_dir, 'config.yaml')
with open(config_path, 'r') as config_file:
    config = yaml.safe_load(config_file)

# Configuration
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_OWNER = config['github']['owner']
GITHUB_REPO = config['github']['repo']
GITHUB_API_BASE = config['github']['api_base']
OBSIDIAN_VAULT_ROOT = config['obsidian']['vault_root']
SYNC_PATH = config['obsidian']['sync_path'].format(repo=GITHUB_REPO)
WHITELIST_FILENAME = config['whitelist']['filename'].format(repo=GITHUB_REPO)

# Calculate full paths
OBSIDIAN_SYNC_PATH = os.path.normpath(os.path.join(OBSIDIAN_VAULT_ROOT, SYNC_PATH))
WHITELIST_PATH = os.path.normpath(os.path.join(OBSIDIAN_SYNC_PATH, WHITELIST_FILENAME))

# Ensure the token is available
if not GITHUB_TOKEN:
    log_and_print("GITHUB_TOKEN not found in environment variables. Please check your .env file.", logging.ERROR)
    raise ValueError("GITHUB_TOKEN not found in environment variables. Please check your .env file.")

# Headers for authentication
headers = {
    'Authorization': f'token {GITHUB_TOKEN}',
    'Accept': 'application/vnd.github.v3+json'
}

def get_repo_contents(path=''):
    url = f'{GITHUB_API_BASE}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{path}'
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def create_obsidian_note(file_path, content, last_updated):
    # Change the extension to .md
    md_file_path = os.path.splitext(file_path)[0] + '.md'
    abs_path = os.path.normpath(os.path.join(OBSIDIAN_SYNC_PATH, md_file_path))
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)

    with open(abs_path, 'w', encoding='utf-8') as file:
        file.write(f"---\n")
        file.write(f"original_file: {file_path}\n")
        file.write(f"last_updated: {last_updated}\n")
        file.write(f"---\n\n")
        file.write(f"# {os.path.basename(file_path)}\n\n")
        file.write("```" + get_language_from_extension(file_path) + "\n")
        file.write(content)
        file.write("\n```")

    log_and_print(f"Note created: {abs_path}")

def get_language_from_extension(file_path):
    extension = os.path.splitext(file_path)[1].lower()
    language_map = {
        '.js': 'javascript',
        '.py': 'python',
        '.html': 'html',
        '.css': 'css',
        # Add more mappings as needed
    }
    return language_map.get(extension, '')

def get_whitelist():
    whitelist = set()
    if os.path.exists(WHITELIST_PATH):
        with open(WHITELIST_PATH, 'r') as f:
            for line in f:
                if line.strip().startswith('- [x]'):
                    whitelist.add(line.split(']', 1)[1].strip())
    return whitelist

def process_github_directory(whitelist, path=''):
    contents = get_repo_contents(path)
    for item in contents:
        try:
            relative_path = item['path']
            if item['type'] == 'dir':
                process_github_directory(whitelist, relative_path)
            elif item['type'] == 'file':
                if relative_path in whitelist:
                    file_content = get_file_content(item['url'])
                    last_updated = get_last_commit_date(relative_path)
                    create_obsidian_note(relative_path, file_content, last_updated)
                    log_and_print(f"Processed: {relative_path}")
                else:
                    log_and_print(f"Skipped (not in whitelist): {relative_path}")
        except Exception as e:
            log_and_print(f"Error processing {item['path']}: {str(e)}", logging.ERROR)

def get_file_content(url):
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    content = response.json()['content']
    return base64.b64decode(content).decode('utf-8')

def get_last_commit_date(file_path):
    url = f'{GITHUB_API_BASE}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/commits'
    params = {'path': file_path}
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    commits = response.json()
    if commits:
        last_commit_date = commits[0]['commit']['committer']['date']
        return datetime.strptime(last_commit_date, "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d %H:%M:%S")
    return "Unknown"

# Main execution
if __name__ == '__main__':
    log_and_print("Starting GitHub to Obsidian sync process")
    log_and_print(f"Obsidian Sync Path: {OBSIDIAN_SYNC_PATH}")
    log_and_print(f"Whitelist Path: {WHITELIST_PATH}")

    # Get the whitelist
    whitelist = get_whitelist()
    log_and_print("Whitelist contents:")
    for item in whitelist:
        log_and_print(f"  - {item}")
   
    # Process the GitHub directory
    process_github_directory(whitelist)
    log_and_print(f"Repository synchronization complete. Files saved to: {OBSIDIAN_SYNC_PATH}")