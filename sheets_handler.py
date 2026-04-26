"""
Google Sheets handler for Email Triage Agent.

Manages Google Sheets API interactions for logging triage results.
Creates and manages worksheets per email category.
"""

import gspread
from google.auth.transport.requests import Request

from config import Config


class SheetsHandler:
    """Handles all Google Sheets interactions."""
    
    def __init__(self, creds, email_address):
        """
        Initialize Sheets handler.
        
        Args:
            creds: Google credentials from Gmail authentication
            email_address: Email account to get the associated sheet ID
        """
        self.creds = creds
        self.email_address = email_address
        self.sheet_id = Config.get_account_sheet_id(email_address)
        
        if not self.sheet_id:
            raise ValueError(f"No Sheet ID configured for {email_address}")
        
        self.sheet = self._connect()
    
    def _connect(self):
        """Connect to Google Sheet."""
        if self.creds.expired and self.creds.refresh_token:
            self.creds.refresh(Request())
        
        gc = gspread.authorize(self.creds)
        return gc.open_by_key(self.sheet_id)
    
    def setup_category_worksheets(self):
        """
        Create worksheets for each email category if they don't exist.
        
        Headers: Date | Sender | Subject | Summary | Links | Gmail Link | Timestamp
        """
        for category in Config.CATEGORIES.keys():
            try:
                self.sheet.worksheet(category)
            except gspread.WorksheetNotFound:
                ws = self.sheet.add_worksheet(title=category, rows=1000, cols=7)
                ws.append_row([
                    'Date', 'Sender', 'Subject', 'Summary', 'Links', 'Gmail Link', 'Timestamp'
                ])
                print(f"  ✨ Created worksheet: {category}")
    
    def log_email(self, category, date, sender, subject, summary, links, gmail_link, timestamp):
        """
        Log a processed email to the appropriate category worksheet.
        
        Args:
            category: Email category
            date: Date in YYYY-MM-DD format
            sender: Email sender
            subject: Email subject
            summary: AI-generated summary
            links: Semicolon-separated URLs
            gmail_link: Link to email in Gmail
            timestamp: ISO timestamp
        """
        try:
            ws = self.sheet.worksheet(category)
            ws.append_row([date, sender, subject, summary, links, gmail_link, timestamp])
            print(f"  📝 Logged to sheet: {category}")
        except gspread.WorksheetNotFound:
            print(f"  ⚠️ Worksheet not found: {category}")
        except Exception as e:
            print(f"  ❌ Error logging to sheet: {e}")
            raise
    
    def ensure_tracker_worksheet(self):
        """Create or get the digest tracker worksheet."""
        try:
            return self.sheet.worksheet('Digest_Tracker')
        except gspread.WorksheetNotFound:
            ws = self.sheet.add_worksheet(title='Digest_Tracker', rows=100, cols=3)
            ws.append_row(['Category', 'Last_Digest_Date', 'Email_Count'])
            return ws
