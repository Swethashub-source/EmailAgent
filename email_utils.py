"""
Email utilities for Email Triage Agent.

Helper functions for email parsing, link building, and formatting.
"""

import base64
from urllib.parse import quote
from datetime import datetime


def build_gmail_link(message_id, email_address):
    """
    Build a Gmail message link that opens the correct account.
    
    Important: Uses authuser parameter to direct to the correct account
    when user is logged into multiple Gmail accounts.
    
    Args:
        message_id: Gmail message ID
        email_address: Email address to set as authuser
    
    Returns:
        URL string to open message in Gmail
    """
    authuser = email_address or "0"
    return f"https://mail.google.com/mail/?authuser={quote(authuser)}#inbox/{message_id}"


def extract_email_body(payload):
    """
    Extract text body from Gmail message payload.
    
    Gmail messages can have complex structures with multiple parts.
    This function prioritizes text/plain, then text/html.
    
    Args:
        payload: Gmail message payload dictionary
    
    Returns:
        Email body text, or empty string if not found
    """
    body = ""
    
    # Handle multipart messages
    if 'parts' in payload:
        for part in payload['parts']:
            mime_type = part.get('mimeType', '')
            
            # Prefer plain text
            if mime_type == 'text/plain':
                body_data = part['body'].get('data', '')
                if body_data:
                    body = base64.urlsafe_b64decode(body_data).decode('utf-8')
                    break
            
            # Fallback to HTML
            elif mime_type == 'text/html':
                body_data = part['body'].get('data', '')
                if body_data:
                    body = base64.urlsafe_b64decode(body_data).decode('utf-8')
    
    # Handle simple messages
    else:
        body_data = payload['body'].get('data', '')
        if body_data:
            body = base64.urlsafe_b64decode(body_data).decode('utf-8')
    
    return body


def get_header(headers, header_name, default='Unknown'):
    """
    Extract a specific header from email headers list.
    
    Args:
        headers: List of header dicts with 'name' and 'value' keys
        header_name: Header name to find (case-sensitive)
        default: Default value if header not found
    
    Returns:
        Header value or default
    """
    headers_dict = {h['name']: h['value'] for h in headers}
    return headers_dict.get(header_name, default)


def format_links(links):
    """
    Format links list as semicolon-separated string.
    
    Args:
        links: List of URL strings
    
    Returns:
        Semicolon-separated string or 'None'
    """
    return '; '.join(links) if links else 'None'


def get_current_date():
    """Get today's date in YYYY-MM-DD format."""
    return datetime.now().strftime('%Y-%m-%d')


def get_current_timestamp():
    """Get current timestamp in ISO format."""
    return datetime.now().isoformat()


def print_account_header(email_address, message="Processing"):
    """Print a formatted section header for account processing."""
    separator = '=' * 70
    print(f"\n{separator}")
    print(f"{message} account: {email_address}")
    print(f"{separator}")


def print_progress(icon, message):
    """Print a formatted progress message."""
    print(f"  {icon} {message}")
