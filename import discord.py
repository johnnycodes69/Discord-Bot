import discord
import os.path
import base64
import json

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Discord bot token and channel ID
DISCORD_TOKEN = 'PUT TOKEN HERE'
CHANNEL_ID = 'PUT CHANNEL HERE'

# Gmail API setup
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_gmail_service():
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
    service = build('gmail', 'v1', credentials=creds)
    return service

def fetch_unread_emails(service):
    results = service.users().messages().list(userId='me', labelIds=['INBOX'], q='is:unread').execute()
    messages = results.get('messages', [])
    return messages

def get_email_details(service, msg_id):
    msg = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
    payload = msg['payload']
    headers = payload['headers']
    subject = next(header['value'] for header in headers if header['name'] == 'Subject')
    from_email = next(header['value'] for header in headers if header['name'] == 'From')
    parts = payload.get('parts', [])
    body = ""
    if parts:
        body = base64.urlsafe_b64decode(parts[0]['body']['data']).decode('utf-8')
    return from_email, subject, body

async def send_to_discord(channel, content):
    if len(content) > 2000:
        content = content[:1900] + "\n`This message is more than 2000 chars so I cannot post the entire message. Sorry.`"
    await channel.send(content)

async def main():
    intents = discord.Intents.default()
    intents.messages = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f'Logged in as {client.user}')
        channel = client.get_channel(CHANNEL_ID)
        gmail_service = get_gmail_service()
        messages = fetch_unread_emails(gmail_service)
        for msg in messages:
            from_email, subject, body = get_email_details(gmail_service, msg['id'])
            content = f"From: {from_email}\nTitle: {subject}\nBody: {body}"
            await send_to_discord(channel, content)
            service.users().messages().modify(userId='me', id=msg['id'], body={'removeLabelIds': ['UNREAD']}).execute()

    client.run(DISCORD_TOKEN)

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
