import os
import json
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("AutoMail")

ADMIN_NAME = os.getenv("admin_name") or os.getenv("ADMIN_NAME") or "Ashis"
ADMIN_EMAIL = os.getenv("admin_mail") or os.getenv("ADMIN_EMAIL") or os.getenv("ADMIN_MAIL") or "ashissarkarnetrakhanda1305@gmail.com"

# In-memory history of sent emails for developer inspection
SENT_EMAILS_HISTORY = []
LOG_FILE_PATH = os.path.join(os.path.dirname(__file__), "sent_emails.jsonl")

def get_groq_api_key():
    return os.getenv("gork_api_key") or os.getenv("GROQ_API_KEY") or os.getenv("GROK_API_KEY")

def enhance_email(user_name: str, user_email: str, admin_name: str = ADMIN_NAME, 
                  admin_email: str = ADMIN_EMAIL, subject: str = "", 
                  description: str = "", reference_link: str = "") -> dict:
    """
    Uses Groq AI (qwen/qwen3.8-27b) to refine user inquiry into a polished,
    high-converting collaboration email to video editor Ashis.
    """
    user_name = user_name.strip() if user_name else "Prospective Client"
    user_email = user_email.strip() if user_email else "client@example.com"
    subject = subject.strip() if subject else "Video Editing & Content Collaboration"
    description = description.strip() if description else "I would like to collaborate on high-retention short-form reel editing."
    reference_link = reference_link.strip()

    groq_key = get_groq_api_key()
    
    if groq_key:
        try:
            logger.info("Enhancing email content using Groq AI...")
            prompt = f"""You are an elite creative producer and executive copywriter. 
A prospective client is contacting professional video editor {admin_name} ({admin_email}) to collaborate on high-impact reel / short-form content.

Client Details:
- Name: {user_name}
- Email: {user_email}
- Raw Subject: {subject}
- Project Brief / Description: {description}
- Reference / Inspiration Link: {reference_link if reference_link else "None provided"}

TASK:
Generate a refined, professional, and exciting email draft ready to send.
The email should:
1. Have a punchy, compelling Subject Line (format: 'Subject: <refined subject>').
2. Open warmly and state the project scope clearly with enthusiasm.
3. Highlight key goals (retention, style, deliverables, and timeline).
4. If a reference link was provided, mention it gracefully as the stylistic benchmark.
5. Provide a clear call to action to discuss rates, availability, and next steps.
6. Sign off professionally with {user_name}'s name and contact email.

IMPORTANT: Return ONLY the ready-to-send email starting with:
Subject: [Your Refined Subject]

Dear {admin_name},

[Refined body...]
Do NOT include preamble, commentary, explanations, or multiple options.
"""
            with httpx.Client(timeout=20.0) as client:
                res = client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {groq_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "qwen/qwen3.8-27b",
                        "messages": [
                            {"role": "system", "content": "You are a professional email drafting assistant for high-end video production inquiries. Provide only the final email text."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.7,
                        "max_tokens": 1000
                    }
                )

            if res.status_code == 200:
                data = res.json()
                content = data["choices"][0]["message"]["content"].strip()
                
                # Parse subject and body
                enhanced_subject = subject
                enhanced_body = content
                
                lines = content.splitlines()
                if lines and lines[0].lower().startswith("subject:"):
                    enhanced_subject = lines[0][len("subject:"):].strip()
                    enhanced_body = "\n".join(lines[1:]).strip()

                return {
                    "success": True,
                    "enhanced_subject": enhanced_subject,
                    "enhanced_body": enhanced_body,
                    "model": "qwen/qwen3.8-27b",
                    "source": "groq_ai"
                }
            else:
                logger.warning(f"Groq API returned status {res.status_code}: {res.text}")
        except Exception as e:
            logger.error(f"Error calling Groq API: {e}", exc_info=True)

    # Fallback high quality template if AI key is unavailable or fails
    fallback_subject = f"Project Inquiry: {subject} – Collaboration with {admin_name}"
    ref_text = f"\n\nStylistic Reference & Assets:\n{reference_link}" if reference_link else ""
    fallback_body = f"""Dear {admin_name},

I hope this message finds you well.

I came across your portfolio and was blown away by your short-form editing style and retention dynamics. I am currently planning a series of high-impact videos and would love to collaborate with you on post-production.

Project Overview:
{description}{ref_text}

I would love to learn more about your current availability, workflow, and pricing structure for this scope. Looking forward to discussing how we can create engaging content together.

Best regards,
{user_name}
{user_email}"""

    return {
        "success": True,
        "enhanced_subject": fallback_subject,
        "enhanced_body": fallback_body,
        "model": "template_fallback",
        "source": "fallback"
    }

def send_email(user_name: str, user_email: str, admin_name: str = ADMIN_NAME,
               admin_email: str = ADMIN_EMAIL, subject: str = "", body: str = "",
               reference_link: str = "") -> dict:
    """
    Dispatches the email to admin (Ashis) and logs the event.
    Supports real SMTP sending if SMTP_USER and SMTP_PASS are configured.
    """
    timestamp = datetime.now().isoformat()
    record = {
        "id": f"mail_{int(datetime.now().timestamp())}",
        "timestamp": timestamp,
        "user_name": user_name,
        "user_email": user_email,
        "admin_name": admin_name,
        "admin_email": admin_email,
        "subject": subject,
        "body": body,
        "reference_link": reference_link,
        "status": "delivered"
    }

    import urllib.parse

    smtp_user = os.getenv("admin_mail_app_user") or os.getenv("admin_mail") or os.getenv("SMTP_USER") or os.getenv("MAIL_USERNAME")
    smtp_pass = os.getenv("admin_mail_app_password") or os.getenv("SMTP_PASS") or os.getenv("GMAIL_APP_PASSWORD") or os.getenv("MAIL_PASSWORD")
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))

    delivered_via = "logged_local"

    # Pre-generate direct Gmail compose web link and mailto link
    full_subject = f"[{user_name}] {subject}"
    encoded_sub = urllib.parse.quote(full_subject)
    encoded_body = urllib.parse.quote(body)
    gmail_compose_url = f"https://mail.google.com/mail/?view=cm&fs=1&to={admin_email}&su={encoded_sub}&body={encoded_body}"
    mailto_url = f"mailto:{admin_email}?subject={encoded_sub}&body={encoded_body}"

    record["gmail_compose_url"] = gmail_compose_url
    record["mailto_url"] = mailto_url

    if smtp_user and smtp_pass:
        try:
            logger.info(f"Connecting to SMTP server {smtp_server}:{smtp_port} via {smtp_user}...")
            msg = MIMEMultipart()
            msg["From"] = f"{user_name} <{smtp_user}>"
            msg["To"] = admin_email
            msg["Reply-To"] = user_email
            msg["Subject"] = full_subject

            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(smtp_server, smtp_port, timeout=12.0) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)

            delivered_via = "smtp_live"
            logger.info(f"Email successfully delivered to {admin_email} via SMTP!")
        except Exception as e:
            logger.error(f"Failed to send email via SMTP: {e}", exc_info=True)
            record["smtp_error"] = str(e)
            delivered_via = "logged_after_smtp_fail"

    record["delivery_method"] = delivered_via
    SENT_EMAILS_HISTORY.insert(0, record)

    # Append to local file for persistent logging
    try:
        with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception as e:
        logger.warning(f"Could not write to {LOG_FILE_PATH}: {e}")

    return {
        "success": True,
        "message": f"Proposal prepared for {admin_name} ({admin_email})!",
        "delivery_method": delivered_via,
        "has_live_smtp": bool(smtp_pass),
        "gmail_compose_url": gmail_compose_url,
        "mailto_url": mailto_url,
        "email_record": record
    }

def get_sent_emails():
    """Returns the history of sent emails."""
    return SENT_EMAILS_HISTORY
