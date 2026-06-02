import base64
import os
from email.mime.text import MIMEText

CREDENTIALS_PATH = "config/credentials.json"
TOKEN_PATH = "config/gmail_token.json"
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
_NOT_CONFIGURED = ("Gmail is not configured. Add config/credentials.json and authorize — "
                   "see docs/gmail-setup.md.")


def is_configured():
    return os.path.exists(CREDENTIALS_PATH) or os.path.exists(TOKEN_PATH)


def email_status():
    return "Gmail is configured." if is_configured() else _NOT_CONFIGURED


def format_message(to, subject, body):
    """Build a Gmail API 'raw' message dict (pure; used by send/draft)."""
    msg = MIMEText(body)
    msg["to"] = to
    msg["subject"] = subject
    return {"raw": base64.urlsafe_b64encode(msg.as_bytes()).decode()}


def _service():
    """Build an authed Gmail service, or None if unavailable. Never raises."""
    if not is_configured():
        return None
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        creds = None
        if os.path.exists(TOKEN_PATH):
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            elif os.path.exists(CREDENTIALS_PATH):
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
                creds = flow.run_local_server(port=0)
            else:
                return None
            with open(TOKEN_PATH, "w") as f:
                f.write(creds.to_json())
        return build("gmail", "v1", credentials=creds)
    except Exception as e:
        print(f"[email] service unavailable: {e}")
        return None


def email_check(n=5):
    svc = _service()
    if not svc:
        return _NOT_CONFIGURED
    try:
        res = svc.users().messages().list(userId="me", maxResults=n, labelIds=["INBOX"]).execute()
        msgs = res.get("messages", [])
        out = []
        for m in msgs:
            full = svc.users().messages().get(userId="me", id=m["id"], format="metadata",
                                              metadataHeaders=["From", "Subject"]).execute()
            hdrs = {h["name"]: h["value"] for h in full.get("payload", {}).get("headers", [])}
            out.append(f"{hdrs.get('From','?')}: {hdrs.get('Subject','(no subject)')}")
        return out or "Inbox is empty."
    except Exception as e:
        return f"Could not check email: {e}"


def email_search(query):
    svc = _service()
    if not svc:
        return _NOT_CONFIGURED
    try:
        res = svc.users().messages().list(userId="me", q=query, maxResults=5).execute()
        return f"{len(res.get('messages', []))} message(s) match '{query}'."
    except Exception as e:
        return f"Could not search email: {e}"


def email_draft(to, subject, body):
    svc = _service()
    if not svc:
        return _NOT_CONFIGURED
    try:
        svc.users().drafts().create(userId="me", body={"message": format_message(to, subject, body)}).execute()
        return f"Draft to {to} saved."
    except Exception as e:
        return f"Could not draft email: {e}"


def email_send(to, subject, body):
    svc = _service()
    if not svc:
        return _NOT_CONFIGURED
    try:
        svc.users().messages().send(userId="me", body=format_message(to, subject, body)).execute()
        return f"Email sent to {to}."
    except Exception as e:
        return f"Could not send email: {e}"
