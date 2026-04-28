"""
Email Triage Agent - Main Entry Point

Orchestrates email processing for multiple Gmail accounts.
Classifies emails using AI, logs to Google Sheets, and sends Telegram alerts.

Usage:
    python email_triage.py                    # Run normal triage
    python email_triage.py --dry-run          # Simulate without changes
    python email_triage.py --cleanup-days 45  # Archive emails older than 45 days
"""

import argparse
import time

from config import Config
from gmail_handler import GmailHandler
from sheets_handler import SheetsHandler
from ai_classifier import AIClassifier
from telegram_notifier import TelegramNotifier
from email_utils import (
    build_gmail_link, extract_email_body, get_header,
    format_links, get_current_date, get_current_timestamp,
    print_account_header, print_progress
)



class EmailTriageProcessor:
    """Main processor for email triage."""
    
    def __init__(self, cleanup_days=30, dry_run=False):
        """
        Initialize processor.
        
        Args:
            cleanup_days: Days threshold for archiving old emails
            dry_run: If True, don't modify Gmail or Sheets
        """
        self.cleanup_days = cleanup_days
        self.dry_run = dry_run
        self.ai_classifier = AIClassifier()
    
    def process_account(self, email_address):
        """
        Process email triage for a single account.
        
        Args:
            email_address: Email account to process
        
        Returns:
            Number of processed messages
        """
        print_account_header(email_address)
        
        try:
            # Set up handlers
            gmail = GmailHandler(email_address)
            gmail.authenticate()
            
            sheets = SheetsHandler(gmail.service._http.credentials, email_address)
            sheets.setup_category_worksheets()
            
            notifier = TelegramNotifier(email_address)
            
            # Ensure triage label exists
            triage_label_id = gmail.ensure_label(Config.TRIAGE_LABEL_NAME)
            
            # Get unread messages
            messages = gmail.get_unread_messages()
            
            if not messages:
                print_progress("📬", "No unread messages found")
                return 0
            
            # Process each message
            processed_count = 0
            for msg in messages:
                try:
                    if not self._process_message(
                        gmail, sheets, notifier,
                        email_address, msg['id'], triage_label_id
                    ):
                        break
                    processed_count += 1
                    time.sleep(2)  # Rate limiting - increased from 1s
                
                except Exception as e:
                    print_progress("❌", f"Error processing message: {e}")
            
            # Archive old triaged emails
            gmail.archive_old_labeled_messages(
                Config.TRIAGE_LABEL_NAME,
                triage_label_id,
                days=self.cleanup_days,
                dry_run=self.dry_run
            )
            
            print_progress("✅", f"Processed {processed_count} messages")
            return processed_count
        
        except Exception as e:
            print_progress("❌", f"Account error: {e}")
            return 0
    
    def _process_message(self, gmail, sheets, notifier, email_address, message_id, triage_label_id):
        """
        Process a single email message.
        
        Returns:
            True to continue, False to stop (e.g., quota exceeded)
        """
        print_progress("📧", f"Processing message: {message_id}")
        
        try:
            # Fetch message
            msg_data = gmail.get_message(message_id)
            headers = msg_data['payload']['headers']
            
            sender = get_header(headers, 'From')
            subject = get_header(headers, 'Subject')
            body = extract_email_body(msg_data['payload'])
            
            # Classify with AI
            analysis = self.ai_classifier.classify_email(subject, body)
            if analysis is None:
                print_progress("⚠️", "AI returned None, stopping to prevent quota issues")
                return False
            
            category = analysis.get('category', 'Spam')
            summary = analysis.get('summary', 'Unable to classify')
            links = format_links(analysis.get('links', []))
            
            # Build Gmail link
            gmail_link = build_gmail_link(message_id, email_address)
            
            # Log to sheets
            sheets.log_email(
                category=category,
                date=get_current_date(),
                sender=sender,
                subject=subject,
                summary=summary,
                links=links,
                gmail_link=gmail_link,
                timestamp=get_current_timestamp()
            )
            
            # Handle based on importance
            if Config.CATEGORIES[category].get('telegram_notify', False):
                # Important: star and notify
                gmail.modify_labels(
                    message_id,
                    add_label_ids=['STARRED'],
                    dry_run=self.dry_run
                )
                notifier.send_alert(category, subject, summary, gmail_link)
            else:
                # Less important: just label
                gmail.modify_labels(
                    message_id,
                    add_label_ids=[triage_label_id],
                    dry_run=self.dry_run
                )
            
            # Mark as read
            gmail.modify_labels(
                message_id,
                remove_label_ids=['UNREAD'],
                dry_run=self.dry_run
            )
            
            print_progress("✅", f"{category}: {subject[:50]}")
            return True
        
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "rate" in error_str.lower():
                print_progress("⏸️", "Rate limited, stopping to prevent API abuse")
                return False
            if "504" in error_str or "timeout" in error_str.lower():
                print_progress("⏸️", "Service unavailable (504), stopping")
                return False
            print_progress("⚠️", f"Error: {e}")
            return True


def main():
    """Main entry point."""
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Email Triage Agent - Classify and organize emails with AI"
    )
    parser.add_argument(
        "--cleanup-days",
        type=int,
        default=Config.DEFAULT_CLEANUP_DAYS,
        help=f"Archive triaged emails older than N days (default: {Config.DEFAULT_CLEANUP_DAYS})"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate triage without modifying Gmail or Sheets"
    )
    args = parser.parse_args()
    
    # Validate configuration
    if not Config.validate():
        print("\n❌ Configuration validation failed. Please check your .env file.")
        return 1
    
    print(f"\n🔄 Starting Email Triage for {len(Config.EMAIL_ACCOUNTS)} account(s)")
    if args.dry_run:
        print("   ⚠️  DRY-RUN MODE: No changes will be made")
    
    # Process each account
    processor = EmailTriageProcessor(
        cleanup_days=args.cleanup_days,
        dry_run=args.dry_run
    )
    
    total_processed = 0
    for email_address in Config.EMAIL_ACCOUNTS:
        try:
            total_processed += processor.process_account(email_address)
        except Exception as e:
            print_progress("❌", f"Error processing {email_address}: {e}")
    
    # Summary
    print(f"\n{'='*70}")
    print(f"✅ Email Triage Complete!")
    print(f"   Total messages processed: {total_processed}")
    print(f"   Accounts: {len(Config.EMAIL_ACCOUNTS)}")
    print(f"{'='*70}\n")
    
    return 0


if __name__ == '__main__':
    exit(main())
