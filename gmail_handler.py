"""
Gmail API handler for Email Triage Agent.

Manages Gmail authentication, message retrieval, and label operations.
Handles per-account OAuth token management.
"""

import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from config import Config


class GmailHandler:
    """Handles all Gmail API interactions."""
    
    def __init__(self, email_address):
        """
        Initialize Gmail handler for a specific email account.
        
        Args:
            email_address: Gmail address to authenticate
        """
        self.email_address = email_address
        self.token_file = f"token_{email_address}.json"
        self.service = None
    
    def authenticate(self):
        """
        Authenticate with Gmail API.
        
        On first run, opens browser for OAuth consent.
        Subsequent runs use cached token; refresh happens automatically.
        
        Returns:
            Gmail API service object
        """
        creds = self._load_or_refresh_credentials()
        self.service = build('gmail', 'v1', credentials=creds)
        return self.service
    
    def _load_or_refresh_credentials(self):
        """Load cached credentials or refresh them if expired."""
        creds = None
        
        # Load from cache if exists
        if os.path.exists(self.token_file):
            print(f"  📂 Loading cached token for {self.email_address}")
            creds = Credentials.from_authorized_user_file(self.token_file, Config.GMAIL_SCOPES)
        
        # Refresh if expired or doesn't exist
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print(f"  🔄 Refreshing token for {self.email_address}")
                creds.refresh(Request())
            else:
                print(f"  🌐 Opening browser for OAuth consent ({self.email_address})")
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json',
                    Config.GMAIL_SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # Save token
            with open(self.token_file, 'w', encoding='utf-8') as f:
                f.write(creds.to_json())
            print(f"  ✅ Token saved: {self.token_file}")
        
        return creds
    
    def get_unread_messages(self, days=7, max_results=100):
        """
        Fetch unread messages from the last N days.
        
        Args:
            days: Look back this many days (default: 7)
            max_results: Maximum messages to fetch (default: 100)
        
        Returns:
            List of message IDs
        """
        from datetime import datetime, timedelta
        
        query = f'is:unread after:{(datetime.now() - timedelta(days=days)).strftime("%Y/%m/%d")}'
        
        try:
            results = self.service.users().messages().list(
                userId=self.email_address,
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            print(f"  📬 Found {len(messages)} unread messages")
            return messages
        
        except Exception as e:
            print(f"  ❌ Error fetching messages: {e}")
            raise
    
    def get_message(self, message_id):
        """
        Fetch full message details.
        
        Args:
            message_id: Gmail message ID
        
        Returns:
            Message data dictionary
        """
        return self.service.users().messages().get(
            userId=self.email_address,
            id=message_id
        ).execute()
    
    def ensure_label(self, label_name):
        """
        Get or create a Gmail label.
        
        Args:
            label_name: Name of the label
        
        Returns:
            Label ID
        """
        # Check if label exists
        labels = self.service.users().labels().list(userId=self.email_address).execute()
        for label in labels.get('labels', []):
            if label.get('name') == label_name:
                return label.get('id')
        
        # Create new label
        created = self.service.users().labels().create(
            userId=self.email_address,
            body={
                "name": label_name,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
            }
        ).execute()
        print(f"  ✨ Created label: {label_name}")
        return created.get('id')
    
    def modify_labels(self, message_id, add_label_ids=None, remove_label_ids=None, dry_run=False):
        """
        Add or remove labels from a message.
        
        Args:
            message_id: Gmail message ID
            add_label_ids: List of label IDs to add
            remove_label_ids: List of label IDs to remove
            dry_run: If True, only print intended changes without modifying
        """
        add_label_ids = add_label_ids or []
        remove_label_ids = remove_label_ids or []
        
        if dry_run:
            labels_str = f"add={add_label_ids or '[]'} remove={remove_label_ids or '[]'}"
            print(f"  [DRY-RUN] Label changes: {labels_str}")
            return
        
        self.service.users().messages().modify(
            userId=self.email_address,
            id=message_id,
            body={
                "addLabelIds": add_label_ids,
                "removeLabelIds": remove_label_ids
            }
        ).execute()
    
    def archive_old_labeled_messages(self, label_name, label_id, days=30, dry_run=False):
        """
        Archive old messages with a specific label by removing them from Inbox.
        
        Args:
            label_name: Name of the label (for display)
            label_id: ID of the label
            days: Archive messages older than N days
            dry_run: If True, only print intended changes
        
        Returns:
            Number of archived messages
        """
        query = f'label:"{label_name}" older_than:{days}d in:inbox'
        archived_count = 0
        next_page_token = None
        
        print(f"\n  🗂️ Archiving emails older than {days} days with label '{label_name}'")
        
        while True:
            try:
                response = self.service.users().messages().list(
                    userId=self.email_address,
                    q=query,
                    maxResults=100,
                    pageToken=next_page_token
                ).execute()
            except Exception as e:
                print(f"  ❌ Error archiving messages: {e}")
                break
            
            messages = response.get('messages', [])
            if not messages:
                break
            
            for msg in messages:
                self.modify_labels(
                    msg['id'],
                    remove_label_ids=['INBOX'],
                    dry_run=dry_run
                )
                archived_count += 1
            
            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break
        
        print(f"  ✅ Archived {archived_count} messages")
        return archived_count
