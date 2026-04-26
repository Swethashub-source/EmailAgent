# Email Triage Automation

A **modular, extensible** email triage system that uses AI (OpenRouter/Gemini) to automatically categorize and organize emails across multiple Gmail accounts with per-account Google Sheets logging and Telegram notifications.

## Features

- 🤖 **AI-Powered Categorization**: Uses OpenRouter API (Google Gemini model) to analyze and categorize emails
- 📊 **Google Sheets Integration**: Logs all processed emails with details like category, sender, subject, and summary
- 📱 **Telegram Notifications**: Sends instant alerts for high-priority emails
- ⭐ **Smart Label Actions**: Stars important emails and labels others with `EmailTriage`
- 🗂 **Monthly Auto-Archive**: Archives `EmailTriage` inbox emails older than 30 days
- 👥 **Multi-Account Support**: Process multiple Gmail accounts with separate sheets and notifications
- 🔧 **Easy to Extend**: Modular design makes it simple to add features or integrate new services
- 📚 **Well-Documented**: Comprehensive code documentation and developer guide
- ⏰ **Automated Execution**: Runs daily using GitHub Actions

## How It Works

1. **Email Collection**: Fetches unread emails from Gmail using Google API
2. **AI Analysis**: Sends email content to OpenRouter API for categorization and summarization
3. **Logging**: Stores results in Google Sheets with appropriate categories
4. **Notifications**: Sends Telegram alerts for high-priority emails
5. **Smart Labeling**:
   - Important categories → starred + Telegram alert
   - Other categories → labeled with `EmailTriage`
6. **Mark as Read**: Automatically marks processed emails as read
7. **Auto-Archive**: Old `EmailTriage` messages removed from Inbox monthly

## Categories

- **Job-Application**: Job offers, interview invitations, recruitment-related emails (🔴 high priority)
- **Rejection**: Job rejections, declined applications (🟡 medium priority)
- **Article-Tech**: Technical articles, tech news, programming tutorials (🟢 low priority)
- **Article-Career**: Career advice, professional development, industry insights (🟢 low priority)
- **Important-Alert**: Urgent notifications, security alerts (🔴 high priority)
- **Newsletter**: Regular newsletters, marketing emails (🟢 low priority)
- **Spam**: Promotional content, unsolicited emails (🟢 low priority)

## Project Architecture

The project is organized into **focused, reusable modules**:

| Module                 | Purpose                                       |
| ---------------------- | --------------------------------------------- |
| `config.py`            | Configuration loading and validation          |
| `gmail_handler.py`     | Gmail API wrapper (fetch, label, archive)     |
| `sheets_handler.py`    | Google Sheets API wrapper (log emails)        |
| `ai_classifier.py`     | Email classification using OpenRouter AI      |
| `telegram_notifier.py` | Telegram bot notifications                    |
| `email_utils.py`       | Helper functions (parsing, formatting, links) |
| `email_triage.py`      | Main orchestrator (coordinates all modules)   |

This modular design makes it **easy to**:

- Add new notification services (Slack, Discord, etc.)
- Integrate different AI models
- Support additional email providers
- Write unit tests
- Understand and maintain the codebase

**For developers:** See [DEVELOPMENT.md](DEVELOPMENT.md) for a detailed guide to extending and contributing.

## Technologies Used

- **Python 3.8+**: Main programming language
- **Gmail API**: Email collection and management
- **Google Sheets API**: Data logging
- **OpenRouter API**: AI analysis (Google Gemini)
- **Telegram Bot API**: Notifications
- **GitHub Actions**: Automation

## Setup

### Prerequisites

- Python 3.8+ installed
- Gmail account(s) with IMAP/API access enabled
- [OpenRouter API key](https://openrouter.ai/) (free tier available)
- [Google OAuth credentials](https://console.cloud.google.com/)
- [Google Sheet created](https://sheets.google.com) for each account
- [Telegram Bot](https://t.me/BotFather) for each account (optional)

### Installation

1. **Clone the repository**

   ```bash
   git clone <repo-url>
   cd EmailAgent
   ```

2. **Install dependencies**

   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Set up Google OAuth credentials**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project
   - Enable Gmail API and Google Sheets API
   - Create an OAuth 2.0 Desktop application credential
   - Download the JSON file and save as `credentials.json`

4. **Create your `.env` file**

   ```bash
   cp .env.example .env
   ```

5. **Configure `.env` with your accounts**

   ```env
   OPENROUTER_API_KEY='your-api-key-here'
   EMAIL_ACCOUNTS='your-email@gmail.com, second-email@gmail.com'
   SHEET_IDS='sheet-id-1, sheet-id-2'
   TELEGRAM_BOT_TOKENS='bot-token-1, bot-token-2'
   TELEGRAM_CHAT_ID='chat-id-1'
   TRIAGE_LABEL_NAME='EmailTriage'
   TRIAGE_ARCHIVE_DAYS='30'
   ```

   **How to get these values:**
   - **SHEET_IDS**: Create a Google Sheet, copy the ID from the URL
   - **TELEGRAM_BOT_TOKENS**: Create bot with @BotFather, get token
   - **TELEGRAM_CHAT_ID**: Message your bot, run `python -c "import json; print(json.dumps({'update_id': 123, 'message': {'chat': {'id': 'YOUR_CHAT_ID'}}}))"`

6. **Run the triage**

   ```bash
   python email_triage.py
   ```

   First run will open browser windows for OAuth authentication (once per account).

## Usage

### Basic Usage

```bash
python email_triage.py
```

Processes all configured accounts with default settings:

- Finds unread emails from last 7 days
- Archives triaged emails older than 30 days

### Dry Run (Preview Mode)

```bash
python email_triage.py --dry-run
```

Shows what would happen without making any actual changes (useful for testing).

### Custom Cleanup Period

```bash
python email_triage.py --cleanup-days 45
```

Archives triaged emails older than 45 days (instead of default 30).

### Multi-Account Setup

When you run `python email_triage.py` with multiple accounts in `EMAIL_ACCOUNTS`:

1. **First run**: The script will open a browser window for each account to request OAuth consent
2. **Token storage**: Each account's token is saved as `token_<email>.json` (e.g., `token_a@gmail.com.json`)
3. **Subsequent runs**: Use the saved tokens; refresh happens automatically if they expire
4. **Per-account sheets**: Each account logs to its own Google Sheet (configured by `SHEET_IDS`)
5. **Per-account notifications**: Each account sends to its own Telegram chat (configured by `TELEGRAM_BOT_TOKENS` and `TELEGRAM_CHAT_IDS`)
6. **Security**: All tokens and configurations are per-account and stored securely in `.env`

## Automation with GitHub Actions

To run this automatically every day:

1. **Push to GitHub** with your `.env` file in `.gitignore`

2. **Create `.github/workflows/email-triage.yml`**:

   ```yaml
   name: Email Triage
   on:
     schedule:
       - cron: "0 8 * * *" # Run at 8 AM UTC daily

   jobs:
     triage:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v3
         - uses: actions/setup-python@v4
           with:
             python-version: "3.11"
         - run: pip install -r requirements.txt
         - run: python email_triage.py
           env:
             GOOGLE_CREDENTIALS: ${{ secrets.GOOGLE_CREDENTIALS }}
             OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
             EMAIL_ACCOUNTS: ${{ secrets.EMAIL_ACCOUNTS }}
             SHEET_IDS: ${{ secrets.SHEET_IDS }}
             TELEGRAM_BOT_TOKENS: ${{ secrets.TELEGRAM_BOT_TOKENS }}
             TELEGRAM_CHAT_IDS: ${{ secrets.TELEGRAM_CHAT_IDS }}
   ```

3. **Add GitHub Secrets**:
   - `GOOGLE_CREDENTIALS`: Content of your `credentials.json` file
   - `OPENROUTER_API_KEY`: Your OpenRouter API key
   - `EMAIL_ACCOUNTS`: Your comma-separated email list
   - `SHEET_IDS`: Your comma-separated Google Sheet IDs
   - `TELEGRAM_BOT_TOKENS`: Your comma-separated Telegram bot tokens
   - `TELEGRAM_CHAT_IDS`: Your comma-separated Telegram chat IDs

## Customization

### Changing Email Categories

Edit `config.py` to add, remove, or modify categories:

```python
CATEGORIES = {
    "Your-New-Category": {
        "priority": "high",
        "telegram_notify": True  # Send Telegram for this category
    },
    ...
}
```

### Integrating a New Notification Service

1. Create a new notifier module (e.g., `slack_notifier.py`)
2. Implement the notification logic
3. Use it in `email_triage.py` alongside `TelegramNotifier`

See [DEVELOPMENT.md](DEVELOPMENT.md) for detailed examples.

### Modifying Email Processing Logic

Edit the `EmailTriageProcessor._process_message()` method in `email_triage.py` to:

- Add attachment handling
- Change label behavior
- Add custom filtering

## Troubleshooting

| Problem                  | Solution                                                         |
| ------------------------ | ---------------------------------------------------------------- |
| `PermissionError: [403]` | Share the Google Sheet with your account and grant Editor access |
| `No emails processed`    | Check that your account has unread emails from the last 7 days   |
| `Token expired`          | Delete the corresponding `token_<email>.json` file and re-run    |
| `"Quota Exceeded"`       | Wait before running again; API rate limits have been hit         |
| Invalid JSON from AI     | The AI response was malformed; it falls back to "Spam" category  |

## Contributing

Want to improve this project? See [DEVELOPMENT.md](DEVELOPMENT.md) for:

- Architecture deep dive
- Common workflows
- Testing strategies
- Code style guide

## License

MIT License - Feel free to use and modify for your needs.

## Support

For issues or questions:

1. Check [DEVELOPMENT.md](DEVELOPMENT.md) for common problems
2. Review the code comments and docstrings
3. Test with `--dry-run` flag to debug
