"""
Telegram Notifier for Email Triage Agent.

Sends important email alerts via Telegram for configured accounts.
"""

import asyncio
import telegram

from config import Config


class TelegramNotifier:
    """Handles Telegram notifications."""
    
    def __init__(self, email_address):
        """
        Initialize notifier for a specific email account.
        
        Args:
            email_address: Email account to get Telegram config for
        """
        self.email_address = email_address
        self.config = Config.get_account_telegram_config(email_address)
    
    def is_configured(self):
        """Check if Telegram is configured for this account."""
        return self.config is not None

    async def _send_message_async(self, message):
        """Send a Telegram message in a dedicated async bot session."""
        async with telegram.Bot(token=self.config["token"]) as bot:
            return await bot.send_message(
                chat_id=self.config["chat_id"],
                text=message,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
    
    def _escape_markdown(self, text):
        """Helper to escape special markdown characters for Telegram Markdown V1."""
        if not text:
            return ""
        # Escape characters that have special meaning in Telegram Markdown V1
        # * _ [ `
        chars_to_escape = ['*', '_', '[', '`']
        for char in chars_to_escape:
            text = text.replace(char, f"\\{char}")
        return text

    def send_alert(self, category, subject, summary, gmail_link):
        """
        Send an email alert to Telegram.
        
        Args:
            category: Email category
            subject: Email subject
            summary: Email summary
            gmail_link: Link to email in Gmail
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.is_configured():
            print(f"  ⚠️  Telegram not configured for {self.email_address}")
            return False
        
        try:
            # Escape content to prevent Telegram parsing errors (e.g. from '[' or '_')
            clean_category = self._escape_markdown(category)
            clean_subject = self._escape_markdown(subject)
            clean_summary = self._escape_markdown(summary)

            message = f"""📧 *Important Email Alert*
*Category:* {clean_category}
*Subject:* {clean_subject}
*Summary:* {clean_summary}
[View Email]({gmail_link})
"""

            # Use a fresh event loop and bot session per send to avoid
            # "Event loop is closed" issues when processing many messages.
            result = asyncio.run(self._send_message_async(message))
            
            print(f"  ✅ Telegram sent (ID: {result.message_id})")
            return True
        
        except Exception as e:
            print(f"  ❌ Telegram error: {e}")
            return False
