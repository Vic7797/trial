"""Notification service for handling various system notifications."""
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.organizations import Organization
from app.services.email_service import EmailService


class NotificationType(str, Enum):
    """Types of notifications."""
    TICKET_CREATED = "ticket_created"
    TICKET_RESOLVED = "ticket_resolved"
    USER_INVITED = "user_invited"
    USER_WELCOME = "user_welcome"
    PASSWORD_RESET = "password_reset"
    PLAN_EXPIRING = "plan_expiring"
    PLAN_EXPIRED = "plan_expired"


class NotificationService:
    """Service for handling system notifications."""

    def __init__(self, db: AsyncSession, email_service: EmailService):
        """Initialize with database session and email service."""
        self.db = db
        self.email_service = email_service

    async def _get_org_plan_info(self, org_id: UUID) -> Dict[str, Any]:
        """Get organization plan information."""
        result = await self.db.execute(
            select(Organization).where(Organization.id == org_id)
        )
        org = result.scalars().first()
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        return {
            "plan": org.plan,
            "expires_at": org.plan_expires_at,
            "name": org.name
        }

    async def send_notification(
        self,
        notification_type: NotificationType,
        recipient_id: UUID,
        data: Dict[str, Any]
    ) -> bool:
        """
        Send a notification based on type.
        
        Args:
            notification_type: Type of notification to send
            recipient_id: ID of the recipient user
            data: Notification data specific to the notification type
            
        Returns:
            bool: True if notification was sent successfully, False otherwise
        """
        try:
            frontend_url = settings.FRONTEND_URL
            
            if notification_type == NotificationType.USER_WELCOME:
                return await self._send_welcome_email(
                    email=data["email"],
                    username=data["username"],
                    password=data["password"],
                    login_url=data.get("login_url", 
                                     f"{frontend_url}/login")
                )
                
            if notification_type == NotificationType.PLAN_EXPIRING:
                return await self._send_plan_expiring_email(
                    email=data["email"],
                    days_left=data["days_left"],
                    plan_name=data["plan_name"],
                    renew_url=data.get("renew_url",
                                     f"{frontend_url}/billing")
                )
                
            if notification_type == NotificationType.PLAN_EXPIRED:
                return await self._send_plan_expired_email(
                    email=data["email"],
                    plan_name=data["plan_name"],
                    renew_url=data.get("renew_url",
                                     f"{frontend_url}/billing")
                )
                
            return False
        except Exception as e:
            print(f"Error sending notification: {str(e)}")
            return False

    async def _send_welcome_email(
        self,
        email: str,
        username: str,
        password: str,
        login_url: str
    ) -> bool:
        """
        Send welcome email with login credentials.
        
        Args:
            email: Recipient email address
            username: Username for the new account
            password: Temporary password
            login_url: URL for the login page
            
        Returns:
            bool: True if email was sent successfully
        """
        app_name = settings.APP_NAME
        subject = f"Welcome to {app_name}! Your Account Details"
        
        body = (
            f"<h2>Welcome to {app_name}!</h2>"
            "<p>Your account has been created successfully. "
            "Here are your login details:</p>"
            f"<p><strong>Email:</strong> {email}</p>"
            f"<p><strong>Password:</strong> {password}</p>"
            "<p>Please change your password after first login.</p>"
            f'<p><a href="{login_url}">Click here to login</a></p>'
            f"<p>Best regards,<br/>{app_name} Team</p>"
        )
        
        try:
            return await self.email_service.send_email(
                to_email=email,
                subject=subject,
                html_content=body
            )
        except Exception as e:
            print(f"Error sending welcome email: {str(e)}")
            return False

    async def _send_plan_expiring_email(
        self,
        email: str,
        days_left: int,
        plan_name: str,
        renew_url: str
    ) -> bool:
        """
        Send notification about expiring plan.
        
        Args:
            email: Recipient email address
            days_left: Number of days until plan expires
            plan_name: Name of the plan
            renew_url: URL to renew the plan
            
        Returns:
            bool: True if email was sent successfully
        """
        app_name = settings.APP_NAME
        days_text = f"{days_left} day{'s' if days_left > 1 else ''}"
        subject = f"Your {plan_name} plan expires in {days_text}"
        
        body = (
            f"<h2>Your {plan_name} plan is about to expire</h2>"
            f"<p>Your current plan will expire in {days_text}.</p>"
            "<p>To avoid any interruption in service, "
            "please renew your subscription.</p>"
            f'<p><a href="{renew_url}">Renew your plan now</a></p>'
            f"<p>Best regards,<br/>{app_name} Team</p>"
        )
        
        try:
            return await self.email_service.send_email(
                to_email=email,
                subject=subject,
                html_content=body
            )
        except Exception as e:
            print(f"Error sending plan expiring email: {str(e)}")
            return False

    async def _send_plan_expired_email(
        self,
        email: str,
        plan_name: str,
        renew_url: str
    ) -> bool:
        """
        Send notification about expired plan.
        
        Args:
            email: Recipient email address
            plan_name: Name of the expired plan
            renew_url: URL to renew the plan
            
        Returns:
            bool: True if email was sent successfully
        """
        app_name = settings.APP_NAME
        subject = f"Your {plan_name} plan has expired"
        
        body = (
            f"<h2>Your {plan_name} plan has expired</h2>"
            "<p>Your subscription has expired. "
            "Some features may be limited until you renew.</p>"
            f'<p><a href="{renew_url}">Renew your plan now</a> '
            'to restore full access.</p>'
            f"<p>Best regards,<br/>{app_name} Team</p>"
        )
        
        try:
            return await self.email_service.send_email(
                to_email=email,
                subject=subject,
                html_content=body
            )
        except Exception as e:
            print(f"Error sending plan expired email: {str(e)}")
            return False
    
    async def check_and_notify_expiring_plans(self) -> None:
        """
        Check for plans expiring soon and send notifications.
        
        This should be called periodically (e.g., daily) to notify users
        about upcoming plan expirations.
        """
        now = datetime.utcnow()
        
        # Check for plans expiring in 1, 2, or 3 days
        for days in [3, 2, 1]:
            expiry_start = now + timedelta(days=days)
            expiry_end = expiry_start + timedelta(days=1)
            
            result = await self.db.execute(
                select(Organization).where(
                    Organization.plan_expires_at.between(expiry_start, expiry_end)
                )
            )
            
            for org in result.scalars().all():
                admin_emails = await self._get_org_admin_emails(org.id)
                
                for email in admin_emails:
                    await self.send_notification(
                        notification_type=NotificationType.PLAN_EXPIRING,
                        recipient_id=email,
                        data={
                            "email": email,
                            "days_left": days,
                            "plan_name": org.plan,
                            "renew_url": f"{settings.FRONTEND_URL}/billing"
                        }
                    )
    
    async def _get_org_admin_emails(self, org_id: UUID) -> List[str]:
        """
        Get admin email addresses for an organization.
        
        Args:
            org_id: Organization ID
            
        Returns:
            List of admin email addresses
            
        Note:
            This is a placeholder implementation. Replace with actual
            database query to fetch admin emails.
        """
        # Implementation example:
        # result = await self.db.execute(
        #     select(User.email).where(
        #         User.organization_id == org_id,
        #         User.role == "admin"
        #     )
        # )
        # return [row[0] for row in result.all()]
        return ["admin@example.com"]  # Replace with actual implementation
        notification_type: NotificationType,
        data: Dict[str, Any]
    ) -> Dict[str, str]:
        """Get notification template from cache or database."""
        cache_key = f"{self.cache_prefix}template:{notification_type}"
        
        # Try cache first
        template = await Cache.get(cache_key)
        if template:
            return template

        # Cache miss, get from predefined templates
        template = self._get_predefined_template(notification_type)
        
        # Cache template
        await Cache.set(cache_key, template)
        return template

    def _get_predefined_template(
        self,
        notification_type: NotificationType
    ) -> Dict[str, str]:
        """Get predefined notification template."""
        templates = {
            NotificationType.TICKET_CREATED: {
                "subject": "New Ticket Created #{ticket_id}",
                "body": (
                    "A new support ticket has been created:\n\n"
                    "Ticket ID: {ticket_id}\n"
                    "Title: {title}\n"
                    "Status: {status}"
                )
            },
            NotificationType.TICKET_UPDATED: {
                "subject": "Ticket #{ticket_id} Updated",
                "body": (
                    "Your support ticket has been updated:\n\n"
                    "Ticket ID: {ticket_id}\n"
                    "Status: {status}\n"
                    "Update: {update}"
                )
            },
            NotificationType.TICKET_ASSIGNED: {
                "subject": "Ticket #{ticket_id} Assigned",
                "body": (
                    "A support ticket has been assigned to you:\n\n"
                    "Ticket ID: {ticket_id}\n"
                    "Title: {title}\n"
                    "Priority: {priority}"
                )
            },
            NotificationType.TICKET_RESOLVED: {
                "subject": "Ticket #{ticket_id} Resolved",
                "body": (
                    "Your support ticket has been resolved:\n\n"
                    "Ticket ID: {ticket_id}\n"
                    "Resolution: {resolution}\n"
                    "Time to Resolve: {resolution_time}"
                )
            },
            NotificationType.USER_CREATED: {
                "subject": "Welcome to Customer Support Platform",
                "body": (
                    "Welcome {name}!\n\n"
                    "Your account has been created successfully.\n"
                    "Role: {role}\n"
                    "Organization: {organization}"
                )
            },
            NotificationType.PAYMENT_RECEIVED: {
                "subject": "Payment Received",
                "body": (
                    "We've received your payment:\n\n"
                    "Amount: {amount}\n"
                    "Plan: {plan}\n"
                    "Valid Until: {valid_until}"
                )
            },
            NotificationType.PLAN_EXPIRING: {
                "subject": "Your Plan is Expiring Soon",
                "body": (
                    "Your current plan will expire soon:\n\n"
                    "Plan: {plan}\n"
                    "Expiry Date: {expiry_date}\n"
                    "Please renew to maintain uninterrupted service."
                )
            }
        }
        return templates.get(notification_type, {
            "subject": "Notification",
            "body": "No template found for this notification type."
        })

    async def _send_email_notification(
        self,
        recipient_id: UUID,
        template: Dict[str, str],
        data: Dict[str, Any]
    ) -> bool:
        """Send notification via email."""
        try:
            # Format template with data
            subject = template["subject"].format(**data)
            body = template["body"].format(**data)

            # Get recipient email
            recipient_email = await self._get_recipient_email(recipient_id)
            if not recipient_email:
                return False

            return await self.email_service.send_email(
                recipient_email,
                subject,
                body
            )
        except Exception:
            return False

    async def _send_telegram_notification(
        self,
        recipient_id: UUID,
        template: Dict[str, str],
        data: Dict[str, Any]
    ) -> bool:
        """Send notification via telegram."""
        try:
            # Format template with data
            message = (
                f"{template['subject'].format(**data)}\n\n"
                f"{template['body'].format(**data)}"
            )

            # Get recipient telegram ID
            telegram_id = await self._get_recipient_telegram_id(recipient_id)
            if not telegram_id:
                return False

            return await self.telegram_service.send_response(
                telegram_id,
                message
            )
        except Exception:
            return False

    async def _get_recipient_email(self, recipient_id: UUID) -> Optional[str]:
        """Get recipient's email from cache or database."""
        cache_key = f"{self.cache_prefix}email:{recipient_id}"
        
        # Try cache first
        email = await Cache.get(cache_key)
        if email:
            return email

        # Cache miss, get from database
        from app.crud.users import user as user_crud
        user = await user_crud.get(self.db, id=recipient_id)
        if not user:
            return None

        # Cache the email
        await Cache.set(cache_key, user.email)
        return user.email

    async def _get_recipient_telegram_id(
        self,
        recipient_id: UUID
    ) -> Optional[str]:
        """Get recipient's telegram ID from cache or database."""
        cache_key = f"{self.cache_prefix}telegram:{recipient_id}"
        
        # Try cache first
        telegram_id = await Cache.get(cache_key)
        if telegram_id:
            return telegram_id

        # Cache miss, get from database
        from app.crud.users import user as user_crud
        user = await user_crud.get(self.db, id=recipient_id)
        if not user or not user.telegram_id:
            return None

        # Cache the telegram ID
        await Cache.set(cache_key, user.telegram_id)
        return user.telegram_id