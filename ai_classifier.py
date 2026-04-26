"""
AI Email Classifier for Email Triage Agent.

Uses OpenRouter API with Google Gemini model to classify and summarize emails.
"""

import json
from openai import OpenAI

from config import Config


class AIClassifier:
    """Handles AI email classification and summarization."""
    
    def __init__(self):
        """Initialize AI classifier with OpenRouter."""
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=Config.OPENROUTER_API_KEY,
        )
    
    def classify_email(self, subject, body):
        """
        Classify and summarize an email using AI.
        
        Args:
            subject: Email subject
            body: Email body (will be truncated to 2000 chars)
        
        Returns:
            Dictionary with keys:
            - category: Email category from CATEGORIES
            - summary: 1-2 sentence summary
            - links: List of URLs found in email
            - confidence: high/medium/low
            - key_action: Any action item or deadline
        """
        # Build email text for AI
        email_text = f"Subject: {subject}\nBody: {body[:2000]}"
        categories_list = list(Config.CATEGORIES.keys())
        
        # Build classification prompt
        prompt = f"""You are an expert email classifier acting as a personal assistant.
Analyze the following email and categorize it accurately.

Categories and their meanings:
- Job-Application: Job offers, interview invitations, recruitment-related emails
- Rejection: Job rejections, declined applications
- Article-Tech: Technical articles, tech news, programming tutorials, software updates
- Article-Career: Career advice, professional development, industry insights
- Important-Alert: Urgent notifications, security alerts, time-sensitive information
- Newsletter: Regular newsletters, marketing emails, updates
- Spam: Promotional content, unsolicited emails, low-value content

Respond ONLY in valid JSON format with:
{{
    "category": one of {categories_list},
    "summary": "A concise 1-2 sentence summary of the most important information",
    "links": ["list", "of", "URLs"],
    "confidence": "high/medium/low",
    "key_action": "Any action item or deadline, or null"
}}

Email content:
{email_text}
"""
        
        try:
            response = self.client.chat.completions.create(
                model=Config.AI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.2
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
        
        except json.JSONDecodeError:
            print(f"  ❌ AI returned invalid JSON, defaulting to Spam")
            return self._default_fallback_response("Invalid AI response format")
        
        except Exception as e:
            print(f"  ❌ AI classification error: {e}")
            return self._default_fallback_response(str(e))
    
    @staticmethod
    def _default_fallback_response(error_msg):
        """Return a safe fallback classification when AI fails."""
        return {
            "category": "Spam",
            "summary": f"AI error: {error_msg}",
            "links": [],
            "confidence": "low",
            "key_action": None
        }
