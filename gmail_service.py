"""
JARVIS Gmail Service
Gmail API + OAuth2 integration for sending and reading emails.
Professional HTML email templates with clean typography.

Setup:
1. Go to https://console.cloud.google.com
2. Create a project → Enable Gmail API
3. Create OAuth 2.0 Client ID (Desktop app)
4. Download JSON → save as 'credentials.json' in this folder
5. First run opens browser for auth → saves token.json automatically
"""

import base64
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv
from loguru import logger

load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
]

TOKEN_PATH = os.path.join(os.path.dirname(__file__), "token.json")
CREDENTIALS_PATH = os.path.join(os.path.dirname(__file__), "credentials.json")

# Pending draft for draft → confirm → send safety pattern
_pending_draft = None


def _get_gmail_service():
    """Authenticate and return Gmail API service.
    First run opens browser for OAuth consent. Subsequent runs use saved token."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None

    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_PATH):
                raise FileNotFoundError(
                    "Gmail not set up yet. Download credentials.json from "
                    "Google Cloud Console (APIs → Credentials → OAuth 2.0 Client IDs) "
                    "and save it in the voice-agent folder."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())
        logger.info("📧 Gmail: OAuth token saved.")

    return build("gmail", "v1", credentials=creds)


def _get_sender_email() -> str:
    """Get the authenticated user's email address."""
    try:
        service = _get_gmail_service()
        profile = service.users().getProfile(userId="me").execute()
        return profile.get("emailAddress", "")
    except Exception:
        return ""


def _build_html_email(body_text: str, subject: str) -> str:
    """Build a professional HTML email with clean fonts and styling."""
    sender_name = os.getenv("GMAIL_SENDER_NAME", "")
    body_html = body_text.replace("\n", "<br>")

    signature = ""
    if sender_name:
        signature = f"""
        <tr>
          <td style="padding:20px 32px 24px; border-top:1px solid #e2e8f0;">
            <p style="margin:0; font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif; font-size:14px; color:#4a5568; font-weight:600;">
              {sender_name}
            </p>
          </td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0; padding:0; background-color:#f7f8fc; -webkit-font-smoothing:antialiased;">
  <table width="100%" cellpadding="0" cellspacing="0" role="presentation"
         style="background-color:#f7f8fc; padding:40px 16px;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" role="presentation"
               style="background-color:#ffffff; border-radius:12px; overflow:hidden;
                      box-shadow:0 4px 16px rgba(0,0,0,0.06); max-width:600px; width:100%;">

          <!-- Header -->
          <tr>
            <td style="background:linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
                        padding:28px 32px;">
              <h1 style="margin:0; font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;
                          font-size:20px; font-weight:600; color:#ffffff;
                          letter-spacing:0.3px; line-height:1.4;">
                {subject}
              </h1>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:32px 32px 28px;
                        font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;
                        font-size:15px; line-height:1.75; color:#2d3748;">
              {body_html}
            </td>
          </tr>

          <!-- Signature -->
          {signature}

          <!-- Footer -->
          <tr>
            <td style="padding:16px 32px; background-color:#f7f8fc;
                        font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;
                        font-size:11px; color:#a0aec0; text-align:center;">
              Sent via JARVIS Neural OS
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def draft_email(to_email: str, subject: str, body: str, cc_email: str = None) -> dict:
    """Create an email draft in memory (not sent yet).
    Returns draft details for user to confirm before sending."""
    global _pending_draft

    html_body = _build_html_email(body, subject)

    msg = MIMEMultipart("alternative")
    msg["To"] = to_email
    msg["Subject"] = subject
    if cc_email:
        msg["Cc"] = cc_email

    # Plain text fallback
    msg.attach(MIMEText(body, "plain"))
    # Rich HTML version
    msg.attach(MIMEText(html_body, "html"))

    _pending_draft = {
        "message": msg,
        "to_email": to_email,
        "cc_email": cc_email,
        "subject": subject,
        "body_preview": body[:300],
    }

    logger.info(f"📧 Email drafted → To: {to_email}, CC: {cc_email}, Subject: {subject}")
    return _pending_draft


def confirm_and_send() -> str:
    """Send the pending draft email via Gmail API.
    Must call draft_email() first."""
    global _pending_draft

    if not _pending_draft:
        return "No email draft pending. Please draft an email first."

    try:
        service = _get_gmail_service()

        raw = base64.urlsafe_b64encode(
            _pending_draft["message"].as_bytes()
        ).decode("utf-8")

        service.users().messages().send(
            userId="me",
            body={"raw": raw},
        ).execute()

        to = _pending_draft["to_email"]
        cc = _pending_draft.get("cc_email")
        subj = _pending_draft["subject"]

        result = f"Email sent successfully to {to}"
        if cc:
            result += f" (CC: {cc})"
        result += f" — Subject: {subj}"

        logger.info(f"📧 ✅ {result}")
        _pending_draft = None
        return result

    except Exception as e:
        logger.error(f"📧 ❌ Gmail send failed: {e}")
        return f"Failed to send email: {str(e)}"


def cancel_draft() -> str:
    """Cancel the pending email draft."""
    global _pending_draft

    if _pending_draft:
        subj = _pending_draft["subject"]
        _pending_draft = None
        return f"Email draft cancelled — was: {subj}"
    return "No draft to cancel."


def read_inbox(count: int = 5) -> list[dict]:
    """Read latest emails from inbox. Returns list of email summaries."""
    try:
        service = _get_gmail_service()

        results = service.users().messages().list(
            userId="me", labelIds=["INBOX"], maxResults=count
        ).execute()

        messages = results.get("messages", [])
        if not messages:
            return []

        emails = []
        for msg_meta in messages:
            msg = service.users().messages().get(
                userId="me",
                id=msg_meta["id"],
                format="metadata",
                metadataHeaders=["From", "Subject", "Date"],
            ).execute()

            headers = {
                h["name"]: h["value"]
                for h in msg.get("payload", {}).get("headers", [])
            }
            emails.append({
                "from": headers.get("From", "Unknown"),
                "subject": headers.get("Subject", "(no subject)"),
                "date": headers.get("Date", ""),
                "snippet": msg.get("snippet", ""),
            })

        logger.info(f"📧 Read {len(emails)} emails from inbox")
        return emails

    except Exception as e:
        logger.error(f"📧 Inbox read failed: {e}")
        return []


def get_pending_draft() -> dict | None:
    """Check if there's a pending email draft."""
    return _pending_draft
