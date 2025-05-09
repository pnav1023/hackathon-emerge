#!/usr/bin/env python3
import os
import requests
import datetime
import json
from dotenv import load_dotenv
from anthropic import Anthropic

# Load environment variables
load_dotenv(override=True)

# GitHub API configuration
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

# GitHub API headers
headers = {
    'Authorization': f'token {GITHUB_TOKEN}',
    'Accept': 'application/vnd.github.v3+json'
}

# Calculate date one week ago
one_week_ago = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime('%Y-%m-%dT%H:%M:%SZ')

def get_user_info():
    """Get authenticated user information"""
    url = 'https://api.github.com/user'
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Error fetching user info: {response.status_code}")
        print(response.text)
        return None
    return response.json()

def get_user_commits_in_repos():
    """Get repositories where the authenticated user has made commits"""
    user_info = get_user_info()
    if not user_info:
        return []
    
    user_login = user_info['login']
    url = f'https://api.github.com/search/commits?q=author:{user_login}+author-date:>{one_week_ago}'
    repos_with_commits = set()
    page = 1
    
    while True:
        response = requests.get(
            f'{url}&page={page}&per_page=100', 
            headers={**headers, 'Accept': 'application/vnd.github.cloak-preview+json'}
        )
        
        if response.status_code != 200:
            print(f"Error fetching commits: {response.status_code}")
            print(response.text)
            break
        
        data = response.json()
        if not data.get('items'):
            break
            
        for item in data['items']:
            repo_url = item['repository']['url']
            repo_owner = repo_url.split('/')[-2]
            repo_name = repo_url.split('/')[-1]
            repos_with_commits.add((repo_owner, repo_name))
        
        if page * 100 >= data.get('total_count', 0):
            break
            
        page += 1
    
    return list(repos_with_commits)

def get_user_commits(repo_owner, repo_name, since_date):
    """Get all commits for a specific repository since the given date"""
    url = f'https://api.github.com/repos/{repo_owner}/{repo_name}/commits'
    params = {'since': since_date}
    
    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        print(f"Error fetching commits for {repo_owner}/{repo_name}: {response.status_code}")
        print(response.text)
        return []
    
    commits = response.json()
    return commits

def format_commit_data(repos_with_commits):
    """Format commit data for LLM processing"""
    formatted_data = []
    
    for repo_data in repos_with_commits:
        repo_name = repo_data['repo_name']
        commits = repo_data['commits']
        
        if not commits:
            continue
            
        formatted_data.append(f"Repository: {repo_name}")
        
        for commit in commits:
            commit_sha = commit['sha'][:7]
            commit_date = commit['commit']['author']['date']
            commit_message = commit['commit']['message']
            formatted_data.append(f"  - [{commit_sha}] {commit_date}: {commit_message}")
        
        formatted_data.append("")
    
    return "\n".join(formatted_data)

def generate_basic_summary(commit_data):
    """Generate a basic summary of commits without using an LLM"""
    if not commit_data.strip():
        return "No commits found in the past week."
    
    lines = commit_data.strip().split('\n')
    current_repo = None
    summary_parts = []
    repo_commits = {}
    
    for line in lines:
        if line.startswith('Repository:'):
            current_repo = line.replace('Repository:', '').strip()
            repo_commits[current_repo] = []
        elif line.strip() and line.startswith('  - '):
            if current_repo:
                commit_info = line.strip()[4:]  # Remove the '  - ' prefix
                repo_commits[current_repo].append(commit_info)
    
    for repo, commits in repo_commits.items():
        summary_parts.append(f"# {repo}")
        
        # Group commits by message to consolidate similar work
        commit_messages = {}
        for commit in commits:
            # Extract commit message from the format [sha] date: message
            parts = commit.split(':', 1)
            if len(parts) > 1:
                message = parts[1].strip()
                sha_date = parts[0].strip()
                if message in commit_messages:
                    commit_messages[message].append(sha_date)
                else:
                    commit_messages[message] = [sha_date]
        
        # Add each unique commit message
        for message, sha_dates in commit_messages.items():
            summary_parts.append(f"- {message}")
        
        summary_parts.append("")
    
    return '\n'.join(summary_parts)

def generate_summary_with_anthropic(commit_data):
    """Generate a summary of commits using Anthropic's Claude"""
    # First try to generate a basic summary without using the API
    basic_summary = generate_basic_summary(commit_data)
    
    # If Anthropic API is not available or has credit issues, return the basic summary
    if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY.startswith('your_') or 'ANTHROPIC_API_KEY' in ANTHROPIC_API_KEY:
        print("Anthropic API key not properly configured. Using basic summary.")
        return basic_summary
    
    # Configure Anthropic client
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    
    prompt = f"""
    Here are my GitHub commits from the past week:
    
    {commit_data}
    
    Please provide a concise, bulleted summary of what I did for each repository. 
    Focus on the actual work accomplished rather than just listing commit messages. 
    Group related commits together into meaningful accomplishments.
    Format the output as follows:
    
    # Repository Name
    - Accomplishment 1 (with technical details)
    - Accomplishment 2 (with technical details)
    
    # Another Repository Name
    - Accomplishment 1 (with technical details)
    - Accomplishment 2 (with technical details)
    """
    
    try:
        # Try with a smaller model that might have more free credits
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=4000,
            temperature=0,
            system="You are a helpful assistant that summarizes GitHub commits into meaningful work accomplishments.",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return response.content[0].text
    except Exception as e:
        print(f"Error generating summary with Anthropic: {e}")
        print("Falling back to basic summary.")
        return basic_summary

def main():
    # Check for required environment variables
    if not GITHUB_TOKEN:
        print("Error: GITHUB_TOKEN environment variable not set")
        return
    
    if not ANTHROPIC_API_KEY:
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        return
    
    print("Fetching repositories where you have made commits...")
    user_repos_with_commits = get_user_commits_in_repos()
    
    repos_with_commits = []
    for repo_owner, repo_name in user_repos_with_commits:
        print(f"Fetching commits for {repo_owner}/{repo_name}...")
        commits = get_user_commits(repo_owner, repo_name, one_week_ago)
        
        if commits:
            repos_with_commits.append({
                'repo_name': f"{repo_owner}/{repo_name}",
                'commits': commits
            })
    
    if not repos_with_commits:
        print("No commits found in the past week.")
        return
    
    commit_data = format_commit_data(repos_with_commits)
    
    print("\nGenerating summary with Anthropic...")
    summary = generate_summary_with_anthropic(commit_data)
    
    print("\n" + "=" * 50)
    print("WEEKLY COMMIT SUMMARY")
    print("=" * 50)
    print(summary)

if __name__ == "__main__":
    main()
