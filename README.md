# Email Triage Automation

This repository contains an email triage automation system that uses AI to categorize emails and send notifications via Telegram. The system is designed to be run automatically using GitHub Actions.

## Features

- 🤖 AI-powered email categorization using OpenRouter or Google Gemini
- 📊 Google Sheets integration for logging and tracking emails
- 📱 Telegram notifications for important emails
- 📚 Digest functionality for periodic email summaries
- ⏰ Automatic daily execution using GitHub Actions

## Prerequisites

### 1. GitHub Repository

1. Create a new GitHub repository
2. Add the following files to your repository:
   - `email_triage.py` - Main email triage script
   - `requirements.txt` - Python dependencies
   - `.github/workflows/email-triage.yml` - GitHub Actions workflow

### 2. Google Cloud Platform (GCP) Setup

1. Create a GCP project
2. Enable the Gmail API and Google Sheets API
3. Create OAuth 2.0 Client IDs credentials
4. Download the `credentials.json` file
5. Run the script locally once to generate `token.json`

### 3. OpenRouter API Key

1. Sign up for an OpenRouter account
2. Create a new API key

### 4. Telegram Bot

1. Create a new Telegram bot using @BotFather
2. Get your bot token
3. Create a new channel or group
4. Add your bot to the channel/group
5. Get your chat ID

## Configuration

### GitHub Secrets

Add the following secrets to your GitHub repository:

1. **GOOGLE_CREDENTIALS** - Content of `credentials.json` (base64 encoded)
2. **GOOGLE_TOKEN** - Content of `token.json` (base64 encoded)
3. **OPENROUTER_API_KEY** - Your OpenRouter API key
4. **GOOGLE_API_KEY** - Your Google Cloud API key (for Gemini)
5. **TELEGRAM_BOT_TOKEN** - Your Telegram bot token
6. **TELEGRAM_CHAT_ID** - Your Telegram chat ID

### Environment Variables

The following environment variables are configured in the workflow:

```
OPENROUTER_API_KEY=${{ secrets.OPENROUTER_API_KEY }}
GOOGLE_API_KEY=${{ secrets.GOOGLE_API_KEY }}
TELEGRAM_BOT_TOKEN=${{ secrets.TELEGRAM_BOT_TOKEN }}
TELEGRAM_CHAT_ID=${{ secrets.TELEGRAM_CHAT_ID }}
```

## Usage

### Automatic Execution

The workflow is configured to run automatically:

1. **Daily at 09:00 AM IST (03:30 AM UTC)**
2. **On push to main branch**
3. **On pull request to main branch**

### Manual Execution

You can also run the workflow manually:

1. Go to the "Actions" tab of your repository
2. Select the "Email Triage Automation" workflow
3. Click "Run workflow"
4. Choose the branch (main)
5. Click "Run workflow" button

## Workflow Details

The GitHub Actions workflow performs the following steps:

1. **Checkout repository** - Downloads the code from your repository
2. **Set up Python** - Installs Python 3.10
3. **Install dependencies** - Installs required Python packages
4. **Configure Google Cloud Credentials** - Creates `credentials.json` and `token.json`
5. **Create .env file** - Creates the environment variables file
6. **Run Email Triage** - Executes the `email_triage.py` script
7. **Cleanup credentials** - Removes sensitive files (runs always, even if previous steps fail)

## Categories

The system categorizes emails into the following categories:

- **Job-Application**: Job offers, interview invitations, recruitment-related emails
- **Rejection**: Job rejections, declined applications
- **Article-Tech**: Technical articles, tech news, programming tutorials, software updates
- **Article-Career**: Career advice, professional development, industry insights
- **Important-Alert**: Urgent notifications, security alerts, time-sensitive information
- **Newsletter**: Regular newsletters, marketing emails, updates
- **Spam**: Promotional content, unsolicited emails, low-value content

## Local Development

To run the script locally:

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Create a `.env` file with your API keys and tokens
4. Run the script: `python email_triage.py`

## Troubleshooting

### Common Issues

1. **Authentication Errors**: Ensure your `credentials.json` and `token.json` are valid and properly formatted.
2. **API Rate Limits**: The script includes retry logic for rate limit errors.
3. **Telegram Notifications**: Verify your bot token and chat ID are correct.
4. **Google Sheets Access**: Ensure your Google Sheets API key and sheet ID are valid.

### Logs

Check the GitHub Actions logs for detailed information about each workflow run.

## License

MIT License
