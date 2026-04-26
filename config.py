"""
Configuration management for Email Triage Agent.

Loads and validates environment variables from .env file.
Manages per-account settings for multiple Gmail accounts.
"""

import os
from dotenv import load_dotenv

# Load .env file
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=dotenv_path)


class Config:
    """Central configuration management."""
    
    # OpenRouter API
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    AI_MODEL = "google/gemini-2.0-flash-001"
    
    # Email accounts
    EMAIL_ACCOUNTS = [e.strip() for e in os.getenv("EMAIL_ACCOUNTS", "").split(",") if e.strip()]
    
    # Google Sheets (per-account)
    SHEET_IDS = [e.strip() for e in os.getenv("SHEET_IDS", "").split(",") if e.strip()]
    
    # Telegram (per-account or single for all)
    TELEGRAM_BOT_TOKENS = [e.strip() for e in os.getenv("TELEGRAM_BOT_TOKENS", "").split(",") if e.strip()]
    _chat_id_env = os.getenv("TELEGRAM_CHAT_ID")
    TELEGRAM_CHAT_IDS = [e.strip() for e in _chat_id_env.split(",") if e.strip()]
    
    # Triage settings
    TRIAGE_LABEL_NAME = os.getenv("TRIAGE_LABEL_NAME", "EmailTriage")
    DEFAULT_CLEANUP_DAYS = int(os.getenv("TRIAGE_ARCHIVE_DAYS", "30"))
    
    # Gmail API scopes
    GMAIL_SCOPES = [
        'https://www.googleapis.com/auth/gmail.modify',
        'https://www.googleapis.com/auth/spreadsheets'
    ]
    
    # Email categories
    CATEGORIES = {
        "Job-Application": {"priority": "high", "telegram_notify": True},
        "Rejection": {"priority": "medium", "telegram_notify": False},
        "Article-Tech": {"priority": "low", "telegram_notify": False},
        "Article-Career": {"priority": "low", "telegram_notify": False},
        "Important-Alert": {"priority": "high", "telegram_notify": True},
        "Newsletter": {"priority": "low", "telegram_notify": False},
        "Spam": {"priority": "low", "telegram_notify": False}
    }
    
    @classmethod
    def get_account_sheet_id(cls, email_address):
        """Get Google Sheet ID for an email account."""
        try:
            idx = cls.EMAIL_ACCOUNTS.index(email_address)
            return cls.SHEET_IDS[idx] if idx < len(cls.SHEET_IDS) else None
        except (ValueError, IndexError):
            return None
    
    @classmethod
    def get_account_telegram_config(cls, email_address):
        """Get Telegram bot token and chat ID for an email account."""
        try:
            idx = cls.EMAIL_ACCOUNTS.index(email_address)
            if idx < len(cls.TELEGRAM_BOT_TOKENS):
                # Use single ID for all if only one is provided, otherwise index into list
                chat_id = cls.TELEGRAM_CHAT_IDS[0] if len(cls.TELEGRAM_CHAT_IDS) == 1 else None
                
                if chat_id:
                    return {
                        "token": cls.TELEGRAM_BOT_TOKENS[idx],
                        "chat_id": chat_id
                    }
        except (ValueError, IndexError):
            pass
        return None
    
    @classmethod
    def validate(cls):
        """Validate all required configuration is present."""
        errors = []
        
        if not cls.OPENROUTER_API_KEY:
            errors.append("❌ Missing OPENROUTER_API_KEY")
        
        if not cls.EMAIL_ACCOUNTS:
            errors.append("❌ Missing EMAIL_ACCOUNTS (comma-separated list)")
        
        if not cls.SHEET_IDS:
            errors.append("❌ Missing SHEET_IDS (comma-separated list, one per account)")
        
        if not cls.TELEGRAM_BOT_TOKENS:
            errors.append("❌ Missing TELEGRAM_BOT_TOKENS (comma-separated list, one per account)")
        
        if not cls.TELEGRAM_CHAT_IDS:
            errors.append("❌ Missing TELEGRAM_CHAT_IDS (comma-separated list, one per account)")
        
        if len(cls.EMAIL_ACCOUNTS) != len(cls.SHEET_IDS):
            errors.append(f"❌ EMAIL_ACCOUNTS ({len(cls.EMAIL_ACCOUNTS)}) and SHEET_IDS ({len(cls.SHEET_IDS)}) counts don't match")
        
        if len(cls.EMAIL_ACCOUNTS) != len(cls.TELEGRAM_BOT_TOKENS):
            errors.append(f"❌ EMAIL_ACCOUNTS ({len(cls.EMAIL_ACCOUNTS)}) and TELEGRAM_BOT_TOKENS ({len(cls.TELEGRAM_BOT_TOKENS)}) counts don't match")
        
        if len(cls.TELEGRAM_CHAT_IDS) > 1 and len(cls.EMAIL_ACCOUNTS) != len(cls.TELEGRAM_CHAT_IDS):
            errors.append(f"❌ EMAIL_ACCOUNTS ({len(cls.EMAIL_ACCOUNTS)}) and TELEGRAM_CHAT_IDS ({len(cls.TELEGRAM_CHAT_IDS)}) counts don't match")
        
        if errors:
            for error in errors:
                print(error)
            return False
        
        return True
