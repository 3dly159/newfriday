# Gmail Setup for Friday

Friday's email tools work once you connect a Google account. One-time setup:

1. Go to https://console.cloud.google.com/ → create a project (any name).
2. APIs & Services → Library → enable **Gmail API**.
3. APIs & Services → OAuth consent screen → External → add yourself as a test user.
4. APIs & Services → Credentials → Create Credentials → **OAuth client ID** →
   Application type **Desktop app**. Download the JSON.
5. Save it as `config/credentials.json` in this project.
6. Next time Friday uses an email tool, a browser window opens for you to authorize;
   the token is saved to `config/gmail_token.json`. Done.

Until then, every email tool simply replies that Gmail isn't configured — nothing breaks.
