# hackathon-emerge

Vibe coding dev tool

Use cases:

- Gives you breakdown for what you did for the day so you can submit your timesheet with relevant notes
- Gives you breakdown for what you did for the day PER CLIENT, so you can give relevant updates during standup
  - Also breakdown for status of tickets and in depth description of what you did from a technical perspective

Necessary integrations and why:

- GitHub for commits (per repo)
- Clickup for:
  - 1. pulling the tickets that you have
  - 2. inserting notes for what you did into a personal "Dev Doc" within the project directory
- Harvest
  - 1. pulling what you did for each project and how long it took
  - 2. (potentially) inserting time section for changes you made automatically

Steps:

1. Pull commits, throw that into an llm, get a bulleted list of what you did in an email
2. Organize that bulleted list based on clickup items and throw that into a personal clickup doc which is titled Pranav's Dev docs. Within each item it should tell you whether you should update the status of that ticket and what status you should update it too. Also it should title every section as "Updates for XX/YY standup"
3. Add direct harvest integration. First have step 2) pull data from harvest and use the notes for each entry in the time sheet as information for the clickup dev doc

## Commit Summary Script

### Setup

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file based on `.env.example` with your GitHub Personal Access Token and Anthropic API Key

### Usage

Run the script to get a summary of your commits from the past week:

```
python commit_summary.py
```

The script will:
1. Fetch only repositories where you have made commits in the past week
2. Get your commits from the past week for each repository
3. Process the commits with Anthropic's Claude LLM
4. Output a bulleted list of what you did per repository

### Proxy Support

The script supports proxies through environment variables:

- `HTTP_PROXY`: HTTP proxy URL (e.g., http://proxy.example.com:8080)
- `HTTPS_PROXY`: HTTPS proxy URL (e.g., https://proxy.example.com:8080)

These can be set in your environment or added to the `.env` file.
