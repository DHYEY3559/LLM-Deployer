# github_handler.py
import os
import subprocess
import time
import shutil
import requests
import stat

# Load environment variables
GITHUB_USER = os.getenv("GITHUB_USER")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

def run_command(command):
    """Runs a shell command and returns its output."""
    print(f"Running command: {' '.join(command)}")
    env = os.environ.copy()
    env["GITHUB_TOKEN"] = GITHUB_TOKEN
    
    result = subprocess.run(command, capture_output=True, text=True, env=env)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        raise Exception(f"Command failed: {' '.join(command)}\nError: {result.stderr}")
    print(f"Success: {result.stdout}")
    return result.stdout.strip()

def handle_remove_readonly(func, path, exc):
    """Error handler for Windows readonly file issues."""
    os.chmod(path, stat.S_IWRITE)
    func(path)

def safe_rmtree(path):
    """Safely remove a directory tree, handling Windows permission issues."""
    if not os.path.exists(path):
        return
    
    try:
        # On Windows, we need to handle readonly files
        if os.name == 'nt':
            shutil.rmtree(path, onerror=handle_remove_readonly)
        else:
            shutil.rmtree(path)
    except Exception as e:
        print(f"Warning: Could not fully delete {path}: {e}")
        # Try one more time after a delay
        time.sleep(2)
        try:
            if os.name == 'nt':
                shutil.rmtree(path, onerror=handle_remove_readonly)
            else:
                shutil.rmtree(path)
        except Exception as e2:
            print(f"Final warning: {path} may not be fully deleted: {e2}")

def enable_github_pages(repo_name):
    """Enable GitHub Pages using the GitHub API."""
    url = f"https://api.github.com/repos/{GITHUB_USER}/{repo_name}/pages"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    data = {
        "source": {
            "branch": "main",
            "path": "/"
        }
    }
    
    print(f"Enabling GitHub Pages for {repo_name}...")
    response = requests.post(url, json=data, headers=headers)
    
    if response.status_code == 201:
        print("GitHub Pages enabled successfully!")
        return True
    elif response.status_code == 409:
        print("GitHub Pages already enabled.")
        return True
    else:
        print(f"Failed to enable GitHub Pages. Status: {response.status_code}")
        print(f"Response: {response.text}")
        raise Exception(f"Failed to enable GitHub Pages: {response.text}")

def create_and_push_repo(task_id, generated_code):
    """Creates a new GitHub repo, adds files, and pushes them."""
    repo_name = task_id
    repo_path = f"/tmp/{repo_name}"

    # Clean up any existing directory
    safe_rmtree(repo_path)
    os.makedirs(repo_path)

    # 1. Create files locally
    with open(f"{repo_path}/index.html", "w", encoding='utf-8') as f:
        f.write(generated_code)
    
    with open(f"{repo_path}/LICENSE", "w") as f:
        f.write(get_mit_license())
        
    with open(f"{repo_path}/README.md", "w") as f:
        f.write(f"# {repo_name}\n\nThis project was auto-generated for the LLM Code Deployment project.")

    # 2. Create a public repository on GitHub first (it will be empty)
    try:
        run_command(["gh", "repo", "create", repo_name, "--public"])
    except Exception as e:
        if "already exists" not in str(e):
            raise e
        print(f"Repository {repo_name} already exists. Proceeding to push updates.")

    # 3. Initialize git locally, add files, commit, and push
    subprocess.run(["git", "init"], cwd=repo_path, check=True)
    subprocess.run(["git", "branch", "-M", "main"], cwd=repo_path, check=True)
    subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_path, check=True)
    
    repo_url_with_auth = f"https://{GITHUB_USER}:{GITHUB_TOKEN}@github.com/{GITHUB_USER}/{repo_name}.git"
    subprocess.run(["git", "remote", "add", "origin", repo_url_with_auth], cwd=repo_path, check=True)
    subprocess.run(["git", "push", "-u", "origin", "main"], cwd=repo_path, check=True)

    # 4. Get commit SHA and Pages URL BEFORE cleanup
    commit_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo_path).decode('utf-8').strip()
    repo_url = f"https://github.com/{GITHUB_USER}/{repo_name}"
    pages_url = f"https://{GITHUB_USER}.github.io/{repo_name}/"
    
    # 5. Clean up local directory
    safe_rmtree(repo_path)
    
    # 6. Enable GitHub Pages using the API (after cleanup to avoid locks)
    enable_github_pages(repo_name)
    
    return repo_url, commit_sha, pages_url

def update_repo(task_id, updated_code):
    """Clones an existing repo, updates a file, and pushes the changes."""
    repo_name = task_id
    repo_path = f"/tmp/{repo_name}"
    repo_url_with_auth = f"https://{GITHUB_USER}:{GITHUB_TOKEN}@github.com/{GITHUB_USER}/{repo_name}.git"

    safe_rmtree(repo_path)
    run_command(["git", "clone", repo_url_with_auth, repo_path])

    with open(f"{repo_path}/index.html", "w", encoding='utf-8') as f:
        f.write(updated_code)

    subprocess.run(["git", "add", "index.html"], cwd=repo_path, check=True)
    subprocess.run(["git", "commit", "-m", "Revise application based on new brief"], cwd=repo_path, check=True)
    subprocess.run(["git", "push", "origin", "main"], cwd=repo_path, check=True)

    commit_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo_path).decode('utf-8').strip()

    safe_rmtree(repo_path)
    
    return commit_sha

def get_existing_code(task_id):
    """Clones a repo and returns the content of index.html."""
    repo_name = task_id
    repo_path = f"/tmp/{repo_name}"
    repo_url_with_auth = f"https://{GITHUB_USER}:{GITHUB_TOKEN}@github.com/{GITHUB_USER}/{repo_name}.git"

    safe_rmtree(repo_path)
    run_command(["git", "clone", repo_url_with_auth, repo_path])

    try:
        with open(f"{repo_path}/index.html", "r", encoding='utf-8') as f:
            content = f.read()
        return content
    except FileNotFoundError:
        print(f"index.html not found in {repo_name}")
        return None
    finally:
        safe_rmtree(repo_path)

def get_mit_license():
    """Returns the text for the MIT License."""
    year = time.strftime("%Y")
    return f"""MIT License

Copyright (c) {year} {GITHUB_USER}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""