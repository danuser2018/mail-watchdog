import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from models import MailMessage

logger = logging.getLogger(__name__)

class SMTPClient:
    """
    SMTPClient is a wrapper around Python's standard smtplib library.
    It manages secure SMTP connection lifecycle and email construction/delivery.
    """
    def __init__(self, host: str, port: int, user: str = None, password: str = None, from_addr: str = None):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.from_addr = from_addr or user or "Nova <nova@localhost>"

    def send(self, message: MailMessage, recipient: str):
        """
        Builds the MIME message and transmits it via SMTP.
        Selects implicit SSL/TLS or explicit STARTTLS based on configuration.
        recipient: resolved email address obtained from identity-service by the caller (processor.py).
        """
        # Build MIMEMultipart message container
        msg = MIMEMultipart("alternative")
        msg["Subject"] = message.subject
        msg["From"] = self.from_addr
        msg["To"] = recipient

        # Determine if content_type is HTML or plain text
        subtype = "html" if "html" in message.content_type.lower() else "plain"
        part = MIMEText(message.body, subtype, "utf-8")
        msg.attach(part)

        server = None
        try:
            # 1. Establish connection
            if self.port == 465:
                logger.debug(f"Connecting to SMTP server {self.host}:{self.port} via SSL/TLS...")
                server = smtplib.SMTP_SSL(self.host, self.port, timeout=10)
            else:
                logger.debug(f"Connecting to SMTP server {self.host}:{self.port}...")
                server = smtplib.SMTP(self.host, self.port, timeout=10)
                server.ehlo()
                
                # Check for STARTTLS support and upgrade
                if server.has_extn("starttls"):
                    logger.debug("STARTTLS extension detected. Upgrading connection...")
                    server.starttls()
                    server.ehlo()

            # 2. Authentication
            if self.user and self.password:
                # Log only the username, NEVER the password
                logger.debug(f"Authenticating SMTP connection for user: {self.user}")
                server.login(self.user, self.password)

            # 3. Transmit the email
            logger.info(f"Dispatching email ID: {message.id} to recipient: {recipient}")
            server.sendmail(self.from_addr, [recipient], msg.as_string())
            logger.info(f"Successfully sent email ID: {message.id}")

        except Exception as e:
            # Re-raise the SMTP exception to be handled by retry orchestrator
            logger.error(f"Failed to deliver email ID {message.id} via SMTP: {e}")
            raise e
        finally:
            if server:
                try:
                    server.quit()
                    logger.debug("SMTP connection closed.")
                except Exception:
                    pass
