from typing import List, Dict, Any, Optional
from uuid import UUID
import aiosmtplib
import email
import imaplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from fastapi import HTTPException, status

from app.config import settings
from app.core.redis import Cache
from app.services.ticket_service import TicketService


class EmailService:
    def __init__(self, db: Any):
        self.smtp_config = {
            "hostname": settings.SMTP_HOST,
            "port": settings.SMTP_PORT,
            "username": settings.SMTP_USERNAME,
            "password": settings.SMTP_PASSWORD,
            "use_tls": settings.SMTP_USE_TLS
        }
        self.imap_config = {
            "host": settings.IMAP_HOST,
            "port": settings.IMAP_PORT,
            "username": settings.IMAP_USERNAME,
            "password": settings.IMAP_PASSWORD,
            "use_ssl": settings.IMAP_USE_SSL
        }
        self.cache_prefix = "email:"

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None
    ) -> bool:
        """Send an email."""
        try:
            message = MIMEMultipart("alternative")
            message["From"] = settings.SMTP_FROM_EMAIL
            message["To"] = to_email
            message["Subject"] = subject

            # Add plain text body
            message.attach(MIMEText(body, "plain"))

            # Add HTML body if provided
            if html_body:
                message.attach(MIMEText(html_body, "html"))

            async with aiosmtplib.SMTP(
                hostname=self.smtp_config["hostname"],
                port=self.smtp_config["port"],
                use_tls=self.smtp_config["use_tls"]
            ) as smtp:
                await smtp.login(
                    self.smtp_config["username"],
                    self.smtp_config["password"]
                )
                await smtp.send_message(message)

            return True
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to send email: {str(e)}"
            )

    async def send_welcome_email(
        self,
        to_email: str,
        first_name: str,
        password: str
    ) -> bool:
        """Send welcome email with login credentials."""
        subject = "Welcome to Customer Support Platform"
        body = f"""
        Hello {first_name},

        Welcome to our Customer Support Platform! Here are your login credentials:

        Email: {to_email}
        Password: {password}

        Please log in and change your password immediately.

        Best regards,
        Customer Support Team
        """

        return await self.send_email(to_email, subject, body)

    async def poll_emails(self) -> List[Dict[str, Any]]:
        """Poll for new emails and create tickets."""
        try:
            # Connect to IMAP server
            mail = imaplib.IMAP4_SSL(
                self.imap_config["host"],
                self.imap_config["port"]
            )
            mail.login(
                self.imap_config["username"],
                self.imap_config["password"]
            )

            # Select inbox
            mail.select("INBOX")

            # Search for unread emails
            _, message_numbers = mail.search(None, "UNSEEN")

            new_tickets = []
            for num in message_numbers[0].split():
                # Fetch email message
                _, msg_data = mail.fetch(num, "(RFC822)")
                email_body = msg_data[0][1]
                email_message = email.message_from_bytes(email_body)

                # Process email
                ticket_data = await self._process_email(email_message)
                if ticket_data:
                    new_tickets.append(ticket_data)

                # Mark as read
                mail.store(num, "+FLAGS", "\\Seen")

            mail.close()
            mail.logout()

            return new_tickets
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Email polling failed: {str(e)}"
            )

    async def _process_email(
        self,
        email_message: email.message.Message
    ) -> Optional[Dict[str, Any]]:
        """Process email message and create ticket."""
        try:
            # Extract email data
            from_email = email_message["from"]
            subject = email_message["subject"]
            body = ""

            # Get email body
            if email_message.is_multipart():
                for part in email_message.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode()
                        break
            else:
                body = email_message.get_payload(decode=True).decode()

            # Create ticket
            ticket_service = TicketService()
            ticket = await ticket_service.create_ticket({
                "title": subject,
                "description": body,
                "source": "email",
                "customer_email": from_email
            })

            return {
                "ticket_id": ticket.id,
                "from_email": from_email,
                "subject": subject,
                "status": "created"
            }
        except Exception as e:
            # Log error but don't fail entire polling process
            print(f"Error processing email: {str(e)}")
            return None

    async def send_ticket_response(
        self,
        ticket_id: UUID,
        response: str,
        to_email: str
    ) -> bool:
        """Send ticket response back to customer."""
        try:
            subject = f"Re: Ticket #{ticket_id}"
            return await self.send_email(to_email, subject, response)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to send response: {str(e)}"
            )