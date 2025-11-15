"""
Email sending functionality for podcast summaries.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List
from loguru import logger


class EmailSender:
    """Send emails via SMTP."""

    def __init__(
        self,
        smtp_server: str,
        smtp_port: int,
        username: str,
        password: str,
        from_email: str,
        use_tls: bool = True
    ):
        """
        Initialize email sender.

        Args:
            smtp_server: SMTP server hostname
            smtp_port: SMTP server port
            username: SMTP username
            password: SMTP password
            from_email: From email address
            use_tls: Whether to use TLS encryption
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_email = from_email
        self.use_tls = use_tls

    def send_email(
        self,
        to_email: str,
        subject: str,
        body_html: str,
        body_text: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> bool:
        """
        Send an email.

        Args:
            to_email: Recipient email address
            subject: Email subject
            body_html: HTML email body
            body_text: Plain text email body (optional)
            cc: CC recipients (optional)
            bcc: BCC recipients (optional)

        Returns:
            True if sent successfully
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = to_email

            if cc:
                msg['Cc'] = ', '.join(cc)

            # Attach plain text version
            if body_text:
                part1 = MIMEText(body_text, 'plain')
                msg.attach(part1)

            # Attach HTML version
            part2 = MIMEText(body_html, 'html')
            msg.attach(part2)

            # Prepare recipient list
            recipients = [to_email]
            if cc:
                recipients.extend(cc)
            if bcc:
                recipients.extend(bcc)

            # Connect to SMTP server and send
            logger.info(f"Connecting to SMTP server: {self.smtp_server}:{self.smtp_port}")

            if self.use_tls:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)

            server.login(self.username, self.password)
            server.sendmail(self.from_email, recipients, msg.as_string())
            server.quit()

            logger.info(f"Email sent successfully to {to_email}")
            return True

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {e}")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    def test_connection(self) -> bool:
        """
        Test SMTP connection and authentication.

        Returns:
            True if connection successful
        """
        try:
            logger.info(f"Testing SMTP connection to {self.smtp_server}:{self.smtp_port}")

            if self.use_tls:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)

            server.login(self.username, self.password)
            server.quit()

            logger.info("SMTP connection test successful")
            return True

        except Exception as e:
            logger.error(f"SMTP connection test failed: {e}")
            return False
