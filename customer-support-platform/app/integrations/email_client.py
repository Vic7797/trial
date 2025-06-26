"""Email client for sending and polling emails."""
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional
import imaplib
import email
from datetime import datetime
from fastapi import HTTPException, status

from app.config import settings

class EmailClient:
    """Async email client for sending and receiving emails."""

    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD
        self.imap_host = settings.IMAP_HOST
        self.imap_port = settings.IMAP_PORT
        self.from_email = settings.FROM_EMAIL


    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """Send an email using SMTP."""
        try:
            message = MIMEMultipart('alternative')
            message['Subject'] = subject
            message['From'] = self.from_email
            message['To'] = to_email

            # Add text part
            if text_content:
                message.attach(MIMEText(text_content, 'plain'))
            
            # Add HTML part
            message.attach(MIMEText(html_content, 'html'))

            # Send email
            async with aiosmtplib.SMTP(
                hostname=self.smtp_host,
                port=self.smtp_port,
                use_tls=True
            ) as smtp:
                await smtp.login(self.smtp_username, self.smtp_password)
                await smtp.send_message(message)
            
            return True
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to send email: {str(e)}"
            )


    async def poll_emails(self, folder: str = "INBOX") -> List[Dict[str, Any]]:
        """Poll emails from IMAP server."""
        try:
            # Connect to IMAP server
            mail = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
            mail.login(self.smtp_username, self.smtp_password)
            mail.select(folder)

            # Search for all unread emails
            _, message_numbers = mail.search(None, 'UNSEEN')
            email_list = []

            for num in message_numbers[0].split():
                _, msg = mail.fetch(num, '(RFC822)')
                email_body = msg[0][1]
                email_message = email.message_from_bytes(email_body)

                # Parse email
                email_data = {
                    'id': num.decode(),
                    'from': email_message['from'],
                    'to': email_message['to'],
                    'subject': email_message['subject'],
                    'date': email_message['date'],
                    'body': self._get_email_body(email_message),
                    'attachments': self._get_attachments(email_message)
                }
                email_list.append(email_data)

            mail.close()
            mail.logout()

            return email_list
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to poll emails: {str(e)}"
            )


    def _get_email_body(self, email_message: email.message.Message) -> str:
        """Extract email body from message."""
        body = ""
        if email_message.is_multipart():
            for part in email_message.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode()
                    break
                elif part.get_content_type() == "text/html":
                    body = part.get_payload(decode=True).decode()
        else:
            body = email_message.get_payload(decode=True).decode()
        return body


    def _get_attachments(self, email_message: email.message.Message) -> List[Dict[str, Any]]:
        """Extract attachments from email message."""
        attachments = []
        for part in email_message.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            if part.get('Content-Disposition') is None:
                continue

            filename = part.get_filename()
            if filename:
                attachments.append({
                    'filename': filename,
                    'content': part.get_payload(decode=True),
                    'content_type': part.get_content_type()
                })
        return attachments


# Initialize global email client
email_client = EmailClient()
