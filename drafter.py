import os
import base64
import re

from datetime import datetime, timedelta, timezone
from dateutil import parser as date_parser
from email.utils import parseaddr
from dateutil import parser as date_parser



from datetime import timezone

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from crewai import Agent, Task, Crew
from langchain_openai import ChatOpenAI


# ============================================================
# CONFIG
# ============================================================
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/calendar.readonly'
]
LLM_MODEL = "gpt-4-turbo"   # or "gpt-3.5-turbo" for cheaper runs


# ============================================================
# AUTH HELPERS
# ============================================================
def get_credentials():
    """Authenticate once and return creds for Gmail + Calendar"""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds


def get_gmail_service(creds):
    return build('gmail', 'v1', credentials=creds)


def get_calendar_service(creds):
    return build('calendar', 'v3', credentials=creds)


# ============================================================
# GMAIL HELPERS
# ============================================================
def get_emails(service, max_results=3):
    """Retrieve recent emails"""
    results = service.users().messages().list(
        userId='me',
        maxResults=max_results,
        labelIds=['INBOX','CATEGORY_PERSONAL']
    ).execute()

    messages = results.get('messages', [])
    email_data = []

    for msg in messages:
        msg_data = service.users().messages().get(
            userId='me',
            id=msg['id'],
            format='full'
        ).execute()

        headers = {h['name']: h['value'] for h in msg_data['payload']['headers']}
        body = ""

        if 'parts' in msg_data['payload']:
            for part in msg_data['payload']['parts']:
                if part['mimeType'] == 'text/plain' and 'data' in part['body']:
                    body += base64.urlsafe_b64decode(
                        part['body']['data']).decode('utf-8')
        elif 'data' in msg_data['payload']['body']:
            body = base64.urlsafe_b64decode(
                msg_data['payload']['body']['data']).decode('utf-8')

        email_data.append({
            'id': msg['id'],
            'threadId': msg_data['threadId'],
            'subject': headers.get('Subject', 'No Subject'),
            'from': headers.get('From'),
            'body': body[:2000]  # truncate for LLM
        })

    return email_data


def create_draft(service, email_id, reply_content):
    """Create draft reply for an email"""
    message = service.users().messages().get(
        userId='me',
        id=email_id,
        format='metadata'
    ).execute()

    headers = message['payload']['headers']
    subject = next((h['value']
                   for h in headers if h['name'] == 'Subject'), '')
    from_email = next((h['value']
                      for h in headers if h['name'] == 'From'), '')

    _, reply_to = parseaddr(from_email)

    message_body = (
        f"To: {reply_to}\r\n"
        f"Subject: Re: {subject}\r\n"
        f"\r\n{reply_content}"
    )

    raw_message = base64.urlsafe_b64encode(
        message_body.encode('utf-8')).decode('utf-8')
    draft = {
        'message': {
            'threadId': message['threadId'],
            'raw': raw_message
        }
    }

    service.users().drafts().create(
        userId='me',
        body=draft
    ).execute()


def send_reply(service, email_id, reply_content):
    """Send a direct reply to an email"""
    message = service.users().messages().get(
        userId='me',
        id=email_id,
        format='metadata'
    ).execute()

    headers = message['payload']['headers']
    subject = next((h['value']
                   for h in headers if h['name'] == 'Subject'), '')
    from_email = next((h['value']
                      for h in headers if h['name'] == 'From'), '')

    _, reply_to = parseaddr(from_email)

    message_body = (
        f"To: {reply_to}\r\n"
        f"Subject: Re: {subject}\r\n"
        f"\r\n{reply_content}"
    )

    raw_message = base64.urlsafe_b64encode(
        message_body.encode('utf-8')).decode('utf-8')

    send_body = {
        'raw': raw_message,
        'threadId': message['threadId']
    }

    service.users().messages().send(
        userId='me',
        body=send_body
    ).execute()


# ============================================================
# CALENDAR HELPERS
# ============================================================


# Set your local timezone offset (example: Nepal +05:45)
LOCAL_OFFSET = timedelta(hours=5, minutes=45)
LOCAL_TZ = timezone(LOCAL_OFFSET)

def extract_datetime_from_text(text):
    """Extract the first datetime from text, normalize AM/PM, ignore timezone"""
    try:
        # Normalize lowercase am/pm
        text = text.replace("am", "AM").replace("pm", "PM")
        dt = date_parser.parse(text, fuzzy=True, default=datetime.now())
        dt = dt.replace(tzinfo=LOCAL_TZ)  # make timezone-aware
        return dt
    except Exception:
        return None


def check_calendar_availability(calendar_service, start_time, duration_minutes=60):
    """Check if a time slot is free in Google Calendar (ignoring other timezones)"""
    end_time = start_time + timedelta(minutes=duration_minutes)

    # Convert to RFC3339 string with local timezone
    start_iso = start_time.isoformat()
    end_iso = end_time.isoformat()

    events_result = calendar_service.events().list(
        calendarId='primary',
        timeMin=start_iso,
        timeMax=end_iso,
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    events = events_result.get('items', [])
    if events:
        return "That time seems to be booked in my calendar, but I will get back to you with confirmation asap."
    else:
        return "That time seems to be available in my calendar, but I will get back to you with confirmation asap."




# ============================================================
# LLM + AGENTS
# ============================================================
llm = ChatOpenAI(model=LLM_MODEL, temperature=0.3)

urgency_analyst = Agent(
    role='Senior Email Analyst',
    goal="Identify emails requiring urgent replies",
    backstory="Expert at triaging urgent matters",
    verbose=True,
    llm=llm
)

draft_specialist = Agent(
    role='Executive Communications Specialist',
    goal="Write professional, concise urgent replies",
    backstory="Crafts executive-level communications",
    verbose=True,
    llm=llm
)


# ============================================================
# MAIN WORKFLOW
# ============================================================
if __name__ == "__main__":
    creds = get_credentials()
    gmail_service = get_gmail_service(creds)
    calendar_service = get_calendar_service(creds)

    emails = get_emails(gmail_service, max_results=3)
    print(f"Found {len(emails)} emails to process")

    for email in emails:
        print(f"\nProcessing email: {email['subject']}")

        # Step 1: Handle date/time inquiry → immediate reply
        dt = extract_datetime_from_text(email['body'])
        if dt:
            print(f"  - Detected datetime inquiry: {dt}")
            availability_reply = check_calendar_availability(calendar_service, dt)
            try:
                send_reply(gmail_service, email['id'], availability_reply)
                print("  - Reply (calendar availability) sent successfully")
            except Exception as e:
                print(f"  - Error sending reply: {str(e)}")
            continue  # skip urgency if date inquiry handled

        # Step 2: Urgency workflow → draft only
        urgency_task = Task(
            description=(
                f"Analyze this email for urgency:\n\n"
                f"FROM: {email['from']}\n"
                f"SUBJECT: {email['subject']}\n"
                f"CONTENT:\n{email['body']}\n\n"
                "Respond with exactly one word: either 'urgent' or 'not urgent'."
            ),
            agent=urgency_analyst,
            expected_output="Either 'urgent' or 'not urgent'"
        )

        urgency_crew = Crew(agents=[urgency_analyst], tasks=[urgency_task])
        urgency_result = urgency_crew.kickoff()
        urgency_text = urgency_result.raw.strip().lower()

        if urgency_text.startswith("urgent"):
            print("  - Urgent email detected")

            draft_task = Task(
                description=(
                    f"Write a professional draft response for this urgent email:\n\n"
                    f"Original email content:\n{email['body']}\n\n"
                    "Guidelines:\n"
                    "- Acknowledge receipt and show empathy\n"
                    "- Keep response under 3 sentences\n"
                    "- Offer immediate next steps if needed\n"
                    "- Maintain professional tone"
                ),
                agent=draft_specialist,
                expected_output="A concise email draft text (body only)"
            )

            draft_crew = Crew(agents=[draft_specialist], tasks=[draft_task])
            draft_content = draft_crew.kickoff()

            try:
                create_draft(gmail_service, email['id'], draft_content)
                print("  - Draft created successfully")
            except Exception as e:
                print(f"  - Error creating draft: {str(e)}")
        else:
            print("  - Not urgent, skipping")

    print("\nProcessing complete. Check your Gmail inbox + drafts.")
