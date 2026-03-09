import os
import base64
import json
from datetime import datetime, timedelta
import gspread
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import google.generativeai as genai
from openai import OpenAI
from dotenv import load_dotenv
import time
import asyncio
import telegram  # For Telegram Bot

# Explicitly specify path to .env file to fix dotenv issue
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=dotenv_path)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
SHEET_ID = os.getenv("SHEET_ID")

# Choose which AI to use
USE_OPENROUTER = True  # Set to False to use Google Gemini

# Initialize OpenRouter if needed
if USE_OPENROUTER:
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY not found in environment variables")
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )
    AI_MODEL = "google/gemini-2.0-flash-001"
else:
    if not GOOGLE_API_KEY:
        raise RuntimeError("GOOGLE_API_KEY not found in environment variables")
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel("models/gemini-2.0-flash")

# Initialize Telegram Bot
telegram_bot = None
if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
    telegram_bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

# === CONFIG ===
SCOPES = ['https://www.googleapis.com/auth/gmail.modify', 'https://www.googleapis.com/auth/spreadsheets']

# Enhanced categories with priority levels
CATEGORIES = {
    "Job-Application": {"priority": "high", "telegram_notify": True},
    "Rejection": {"priority": "medium", "telegram_notify": False},
    "Article-Tech": {"priority": "low", "telegram_notify": False, "digest_days": 5},
    "Article-Career": {"priority": "low", "telegram_notify": False, "digest_days": 5},
    "Important-Alert": {"priority": "high", "telegram_notify": True},
    "Newsletter": {"priority": "low", "telegram_notify": False, "digest_days": 5},
    "Spam": {"priority": "low", "telegram_notify": False}
}

# Escape Markdown special characters for Telegram
def escape_markdown(text):
    """Escape special characters for Telegram Markdown"""
    if not text:
        return ""
    # Characters that need escaping in Telegram MarkdownV2
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text

# Gmail service
def get_gmail_service():
    creds = None
    print("Starting get_gmail_service...")
    try:
        if os.path.exists('token.json'):
            print("token.json found, loading credentials...")
            with open('token.json', 'r', encoding='utf-8') as f:
                token_data = f.read()
                print(f"token.json size: {len(token_data)} bytes")
            
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
            print(f"Credentials valid: {creds.valid}")
            if creds.expired:
                print(f"Token expired at: {creds.expiry}")
                print(f"Refresh token available: {creds.refresh_token is not None}")
        
        if not creds or not creds.valid:
            print("Credentials invalid or expired, refreshing...")
            if creds and creds.expired and creds.refresh_token:
                try:
                    print("Attempting to refresh token...")
                    creds.refresh(Request())
                    print("Token refresh successful")
                    
                    with open('token.json', 'w', encoding='utf-8') as token:
                        token.write(creds.to_json())
                    print("Successfully updated token.json")
                except Exception as refresh_error:
                    print(f"Failed to refresh token: {refresh_error}")
                    raise
            else:
                print("No valid refresh token available")
                raise Exception("No valid refresh token available - please re-authenticate locally")
                
        print("Successfully obtained valid credentials")
        return build('gmail', 'v1', credentials=creds)
        
    except Exception as e:
        print(f"Error in get_gmail_service(): {type(e).__name__}: {e}")
        import traceback
        print(f"Stack trace: {traceback.format_exc()}")
        raise

# Sheets service
def get_sheets_service(creds):
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    gc = gspread.authorize(creds)
    return gc.open_by_key(SHEET_ID)

# Enhanced AI analysis
def analyze_email_openrouter(subject, body):
    full_text = f"Subject: {subject}\nBody: {body[:2000]}"
    categories_list = list(CATEGORIES.keys())
    prompt = f"""
    You are an expert email classifier acting as a personal assistant to a FullStack Developer with 2+ years of experience who wants to be upto date with current Technologies, news, and all other updates. Analyze the emails and categorize it accurately.

    Categories and their meanings:
    - Job-Application: Job offers, interview invitations, recruitment-related emails
    - Rejection: Job rejections, declined applications
    - Article-Tech: Technical articles, tech news, programming tutorials, software updates
    - Article-Career: Career advice, professional development, industry insights
    - Important-Alert: Urgent notifications, security alerts, time-sensitive information
    - Newsletter: Regular newsletters, marketing emails, updates
    - Spam: Promotional content, unsolicited emails, low-value content

    Respond ONLY in valid JSON format:
    {{
        "category": one of {categories_list},
        "summary": "A concise 1-2 sentence summary highlighting the most important information",
        "links": ["array of all URLs from the email body"],
        "confidence": "high/medium/low - your confidence in the categorization",
        "key_action": "Any action item or deadline mentioned (or null)"
    }}

    Email content:
    {full_text}
    """
    try:
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.2
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"    OpenRouter Error: {e}")
        return {"category": "Spam", "summary": f"OpenRouter error: {str(e)}", "links": [], "confidence": "low", "key_action": None}

def analyze_email_gemini(subject, body):
    full_text = f"Subject: {subject}\nBody: {body[:2000]}"
    categories_list = list(CATEGORIES.keys())
    prompt = f"""
    Analyze this email and respond ONLY in valid JSON format.
    {{
        "category": one of {categories_list},
        "summary": 1-2 sentence summary of key points,
        "links": array of up to 3 URLs from the body (or empty array)
    }}
    Email content:
    {full_text}
    """
    time.sleep(2)
    response = model.generate_content(prompt)
    try:
        return json.loads(response.text)
    except json.JSONDecodeError:
        return {"category": "Spam", "summary": "Failed to parse Gemini response", "links": []}

def analyze_email(subject, body):
    if USE_OPENROUTER:
        return analyze_email_openrouter(subject, body)
    else:
        return analyze_email_gemini(subject, body)

# Send Telegram notification
def send_telegram_notification(category, subject, summary, gmail_link):
    if not telegram_bot:
        print("  ⚠ Telegram not configured (missing bot token or chat ID)")
        return False
    try:
        message_text = f"""
📧 *Important Email Alert*
*Category:* {category}
*Subject:* {subject}
*Summary:* {summary}
[View Email]({gmail_link})
"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            telegram_bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=message_text,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
        )
        loop.close()
        print(f"  ✓ Telegram notification sent (Message ID: {result.message_id})")
        return True
    except Exception as e:
        print(f"  ✗ Telegram error: {e}")
        return False

# Setup category-specific worksheets
def setup_category_worksheets(sheet):
    for category in CATEGORIES.keys():
        try:
            sheet.worksheet(category)
        except gspread.WorksheetNotFound:
            worksheet = sheet.add_worksheet(title=category, rows=1000, cols=7)
            worksheet.append_row(['Date', 'Sender', 'Subject', 'Summary', 'Links', 'Gmail Link', 'Timestamp'])
    return sheet

# Get or create digest tracker
def get_digest_tracker(sheet):
    try:
        return sheet.worksheet('Digest_Tracker')
    except gspread.WorksheetNotFound:
        tracker = sheet.add_worksheet(title='Digest_Tracker', rows=100, cols=3)
        tracker.append_row(['Category', 'Last_Digest_Date', 'Email_Count'])
        return tracker

# ──────────────────────────────────────────────────────────────
# FIXED & ROBUST DIGEST FUNCTION
# ──────────────────────────────────────────────────────────────
def check_and_send_digests(sheet):
    if not telegram_bot:
        print("  ⚠ Telegram not configured, skipping digests")
        return

    today = datetime.now()
    digest_categories = [cat for cat, config in CATEGORIES.items() if 'digest_days' in config]

    for category in digest_categories:
        config = CATEGORIES[category]
        digest_days = config['digest_days']
        tracker = get_digest_tracker(sheet)

        # Get last digest date
        records = tracker.get_all_records()
        last_digest = None
        row_to_update = None
        for idx, record in enumerate(records, 2):
            if record.get('Category') == category:
                if record.get('Last_Digest_Date'):
                    try:
                        last_digest = datetime.fromisoformat(record['Last_Digest_Date'])
                    except:
                        pass
                row_to_update = idx
                break

        if not (last_digest is None or (today - last_digest).days >= digest_days):
            continue

        print(f"\n📚 Preparing {category} digest...")

        try:
            worksheet = sheet.worksheet(category)
            all_values = worksheet.get_all_values()
            if len(all_values) <= 1:
                print(f"  ⚠ No emails in {category}")
                continue

            header_row = all_values[0]
            all_records = [dict(zip(header_row, row)) for row in all_values[1:]]

            cutoff = today - timedelta(days=digest_days)
            recent_articles = [
                r for r in all_records
                if r.get('Timestamp') and datetime.fromisoformat(r['Timestamp']) > cutoff
            ]

            if not recent_articles:
                print(f"  ⚠ No recent articles in {category}")
                continue

            # ── Build parts with proper Markdown escaping ──
            header = f"""
📚 *{category} Digest*
_{digest_days}-day summary ({len(recent_articles)} articles)_
"""

            parts = [header]
            current = ""

            for idx, article in enumerate(recent_articles, 1):
                subject = escape_markdown(article.get('Subject', 'No Subject')[:80])
                summary = escape_markdown(article.get('Summary', '')[:100])
                if len(summary) == 100:
                    summary += "..."

                part = f"\n*{idx}. {subject}*\n_{summary}_\n"

                # One link
                links = article.get('Links', '').strip()
                if links and links != 'None':
                    link_list = [l.strip() for l in links.split(';') if l.strip()]
                    if link_list:
                        part += f"🔗 {escape_markdown(link_list[0])}\n"

                # Gmail link
                gmail_link = article.get('Gmail Link', '').strip()
                if gmail_link.startswith('http'):
                    part += f"📧 [View in Gmail]({gmail_link})\n"

                # Split if too long
                if len(current) + len(part) > 3900:
                    parts.append(current.strip())
                    current = f"📚 *{category} Digest (continued)*\n"
                current += part

            if current:
                parts[-1] += f"\n\n_Generated on {today.strftime('%Y-%m-%d %H:%M')}_"  # add date to last part

            # ── Send ALL parts using ONE event loop ──
            async def send_all():
                for i, msg in enumerate(parts, 1):
                    try:
                        import requests

                        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                        payload = {
                            'chat_id': TELEGRAM_CHAT_ID,
                            'text': msg,
                            'parse_mode': 'Markdown',
                            'disable_web_page_preview': True
                        }

                        response = requests.post(url, json=payload)
                        response.raise_for_status()
                        print(f"  ✓ Digest part {i}/{len(parts)} sent")
                        time.sleep(0.5)  # Small delay between messages
                    except Exception as e:
                        print(f"  ✗ Failed to send part {i}: {e}")
            # Update tracker
            if row_to_update:
                tracker.update_cell(row_to_update, 2, today.isoformat())
                tracker.update_cell(row_to_update, 3, len(recent_articles))
            else:
                tracker.append_row([category, today.isoformat(), len(recent_articles)])

        except gspread.WorksheetNotFound:
            print(f"  ⚠ Worksheet not found for {category}")
        except Exception as e:
            print(f"  ✗ Error processing {category} digest: {e}")
# Main triage function
def run_triage():
    service = get_gmail_service()
    creds = service._http.credentials
    sheet = get_sheets_service(creds)

    setup_category_worksheets(sheet)

    print("\nChecking for pending digests...")
    check_and_send_digests(sheet)

    # Fetch unread emails
    query = 'is:unread after:' + (datetime.now() - timedelta(days=7)).strftime('%Y/%m/%d')

    def fetch_messages_with_retry(service, query, retries=3):
        for attempt in range(retries):
            try:
                return service.users().messages().list(
                    userId=EMAIL_ADDRESS,
                    q=query,
                    maxResults=1
                ).execute()
            except Exception as e:
                if attempt == retries - 1:
                    raise
                print(f"Gmail API error: {e}, retrying...")
                time.sleep(2)

    print(f"\n📧 Processing unread emails...")
    print(f"Query: {query}")
    results = fetch_messages_with_retry(service, query)
    messages = results.get('messages', [])

    for msg in messages:
        print(f"\nProcessing message ID: {msg['id']}")
        try:
            msg_data = service.users().messages().get(userId=EMAIL_ADDRESS, id=msg['id']).execute()
            headers = {h['name']: h['value'] for h in msg_data['payload']['headers']}
            sender = headers.get('From', 'Unknown')
            subject = headers.get('Subject', 'No Subject')
            print(f"  Subject: {subject}")

            # Decode body
            payload = msg_data['payload']
            body = ""
            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain':
                        body_data = part['body'].get('data', '')
                        body = base64.urlsafe_b64decode(body_data).decode('utf-8') if body_data else ''
                        break
            else:
                body_data = payload['body'].get('data', '')
                body = base64.urlsafe_b64decode(body_data).decode('utf-8') if body_data else ''

            # AI Analysis
            analysis = None
            for attempt in range(3):
                try:
                    analysis = analyze_email(subject, body)
                    break
                except Exception as e:
                    if "429" in str(e) and attempt < 2:
                        print(f"    Rate limit hit, waiting 30s...")
                        time.sleep(30)
                    else:
                        raise

            if not analysis:
                raise Exception("Failed to get AI analysis")

            category = analysis['category']
            summary = analysis['summary']
            links_str = '; '.join(analysis.get('links', [])) or 'None'
            gmail_link = f"https://mail.google.com/mail/u/0/#inbox/{msg['id']}"
            timestamp = datetime.now().isoformat()
            today_date = datetime.now().strftime('%Y-%m-%d')

            # Log to sheet
            print(f"  Category: {category}")
            worksheet = sheet.worksheet(category)
            worksheet.append_row([today_date, sender, subject, summary, links_str, gmail_link, timestamp])

            # Telegram notification for important categories
            if CATEGORIES.get(category, {}).get('telegram_notify', False):
                print(f"  📱 Sending Telegram notification...")
                send_telegram_notification(category, subject, summary, gmail_link)

            # Mark as read
            service.users().messages().modify(
                userId=EMAIL_ADDRESS,
                id=msg['id'],
                body={'removeLabelIds': ['UNREAD']}
            ).execute()

            print(f"  ✓ Processed and Logged: {subject}")
            time.sleep(1)

        except Exception as e:
            if "429" in str(e):
                print("  !! Quota Exceeded !! Stopping.")
                break
            print(f"  ✗ Error processing message {msg['id']}: {e}")

    print(f"\n✅ Triage complete! Processed {len(messages)} messages")

if __name__ == '__main__':
    run_triage()
