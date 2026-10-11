import os
import sys
import json
import logging
from secrets import token_hex
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from dotenv import load_dotenv
import httpx
import video_manager
import auto_mail

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("portfolio_app.log"),
        logging.StreamHandler(sys.stdout)
    ],
    force=True
)
logger = logging.getLogger("PortfolioApp")

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY") or token_hex(32)

manager = video_manager.IMAGEKIT_VIDEO_MANAGER()

# Portfolio Owner & Admin Information from .env
ADMIN_NAME = os.getenv("admin_name") or os.getenv("ADMIN_NAME") or "Ashis"
ADMIN_EMAIL = os.getenv("admin_mail") or os.getenv("ADMIN_EMAIL") or os.getenv("ADMIN_MAIL") or "ashissarkarnetrakhanda1305@gmail.com"
ADMIN_YOUTUBE_URL = os.getenv("admin_youtube") or os.getenv("ADMIN_YOUTUBE_URL") or "https://youtube.com/@ashissarkar"
ADMIN_INSTAGRAM_URL = os.getenv("admin_instagram") or os.getenv("ADMIN_INSTAGRAM_URL") or "https://instagram.com/ashissarkar"
ADMIN_LINKEDIN_URL = os.getenv("admin_linkedin") or os.getenv("ADMIN_LINKEDIN_URL") or "https://linkedin.com/in/ashissarkar"

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "562465382146-3ga4735q7i3ign0na1l6681h0q2tdd0p.apps.googleusercontent.com")

@app.route("/")
def home():
    logger.info("Main portfolio page accessed (Client view).")
    videos = manager.fetch_all_videos()
    current_user = session.get("user")
    return render_template(
        "main.html",
        videos=videos,
        admin_name=ADMIN_NAME,
        admin_email=ADMIN_EMAIL,
        admin_youtube=ADMIN_YOUTUBE_URL,
        admin_instagram=ADMIN_INSTAGRAM_URL,
        admin_linkedin=ADMIN_LINKEDIN_URL,
        google_client_id=GOOGLE_CLIENT_ID,
        current_user=current_user
    )

def is_admin_authenticated():
    """
    Verifies if the currently logged-in user is the registered administrator (from .env).
    """
    user = session.get("user")
    if not user:
        return False
    user_email = (user.get("email") or "").strip().lower()
    registered_admin = ADMIN_EMAIL.strip().lower()
    return bool(user_email and registered_admin and user_email == registered_admin)

@app.route("/admin")
def admin():
    logger.info("Admin route accessed.")
    if not is_admin_authenticated():
        current_user = session.get("user")
        return render_template(
            "admin_login.html",
            admin_name=ADMIN_NAME,
            admin_email=ADMIN_EMAIL,
            google_client_id=GOOGLE_CLIENT_ID,
            current_user=current_user
        )

    videos = manager.fetch_all_videos()
    return render_template(
        "admin_page.html",
        videos=videos,
        admin_name=ADMIN_NAME,
        admin_email=ADMIN_EMAIL,
        current_user=session.get("user")
    )

@app.route("/status")
def dev_status():
    """
    Developer status endpoint to check if the user is correctly logged in or not,
    view current session information, admin configurations, and outbox logs.
    Supports both browser dashboard view and JSON (?format=json).
    """
    current_user = session.get("user")
    is_logged_in = bool(current_user)
    recent_emails = auto_mail.get_sent_emails()
    
    status_data = {
        "logged_in": is_logged_in,
        "user": current_user,
        "admin": {
            "name": ADMIN_NAME,
            "email": ADMIN_EMAIL
        },
        "google_client_id_configured": bool(GOOGLE_CLIENT_ID),
        "groq_configured": bool(auto_mail.get_groq_api_key()),
        "sent_emails_count": len(recent_emails),
        "recent_emails": recent_emails[:10]
    }
    
    if request.args.get("format") == "json" or request.headers.get("Accept") == "application/json":
        return jsonify(status_data)

    return render_template(
        "status.html",
        logged_in=is_logged_in,
        user=current_user or {},
        admin=status_data["admin"],
        google_client_id_configured=status_data["google_client_id_configured"],
        groq_configured=status_data["groq_configured"],
        sent_emails_count=status_data["sent_emails_count"],
        recent_emails=recent_emails,
        json_payload=json.dumps(status_data, indent=2)
    )

@app.route("/api/auth/google", methods=["POST"])
def auth_google():
    """
    Handles Google Identity Services JWT credential validation.
    Extracts name, email, picture, and stores into the user session.
    """
    data = request.get_json() or {}
    credential = data.get("credential")

    if not credential:
        return jsonify({"success": False, "error": "No credential token provided"}), 400

    try:
        # Validate token using Google's public tokeninfo endpoint
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(f"https://oauth2.googleapis.com/tokeninfo?id_token={credential}")

        if resp.status_code != 200:
            logger.error(f"Google token validation failed: {resp.text}")
            return jsonify({"success": False, "error": "Invalid Google credential"}), 401

        payload = resp.json()
        user_info = {
            "sub": payload.get("sub"),
            "email": payload.get("email"),
            "name": payload.get("name", payload.get("email", "").split("@")[0]),
            "picture": payload.get("picture", ""),
            "auth_provider": "google",
            "email_verified": payload.get("email_verified", True)
        }

        session["user"] = user_info
        logger.info(f"User signed in via Google: {user_info['name']} ({user_info['email']})")
        return jsonify({"success": True, "user": user_info})

    except Exception as e:
        logger.error(f"Exception during Google auth: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/auth/dev-login", methods=["POST"])
def auth_dev_login():
    """
    Fast developer login helper for quick local testing without OAuth redirect domains.
    """
    data = request.get_json() or {}
    name = data.get("name", "Alex Rivera (Demo Client)")
    email = data.get("email", "alex.client.demo@gmail.com")

    user_info = {
        "sub": "dev_test_sub_998811",
        "name": name,
        "email": email,
        "picture": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80",
        "auth_provider": "google_dev_demo",
        "email_verified": True
    }
    session["user"] = user_info
    logger.info(f"Dev test user signed in: {name} ({email})")
    return jsonify({"success": True, "user": user_info})

@app.route("/api/auth/admin-login", methods=["POST"])
def auth_admin_login():
    """
    Direct verification for the registered admin email from .env (admin portal quick auth).
    """
    data = request.get_json() or {}
    submitted_email = (data.get("email") or "").strip().lower()
    registered_admin = ADMIN_EMAIL.strip().lower()

    if submitted_email and submitted_email != registered_admin:
        logger.warning(f"Rejected admin login attempt with unauthorized email: '{submitted_email}'")
        return jsonify({
            "success": False,
            "error": f"Access Denied: '{submitted_email}' is not the registered admin ({ADMIN_EMAIL})."
        }), 403

    admin_user = {
        "sub": "admin_registered_sub_001",
        "name": ADMIN_NAME,
        "email": ADMIN_EMAIL,
        "picture": "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150&auto=format&fit=crop&q=80",
        "auth_provider": "registered_admin",
        "email_verified": True,
        "is_admin": True
    }
    session["user"] = admin_user
    logger.info(f"Admin session successfully established for registered admin: {ADMIN_EMAIL}")
    return jsonify({"success": True, "user": admin_user, "is_admin": True})

@app.route("/api/auth/logout", methods=["GET", "POST"])
def auth_logout():
    session.pop("user", None)
    logger.info("User signed out.")
    if request.method == "POST" or request.args.get("format") == "json":
        return jsonify({"success": True, "logged_in": False})
    return redirect(url_for("home"))

@app.route("/api/auth/user")
def auth_get_current_user():
    current_user = session.get("user")
    return jsonify({
        "logged_in": bool(current_user),
        "user": current_user
    })

@app.route("/api/ai-enhance", methods=["POST"])
def ai_enhance():
    """
    Receives draft inquiry details and enhances the mail using Groq AI.
    """
    data = request.get_json() or {}
    user_name = data.get("user_name", "")
    user_email = data.get("user_email", "")
    subject = data.get("subject", "")
    description = data.get("description", "")
    reference_link = data.get("reference_link", "")

    # Auto-fill from session if user is logged in
    if "user" in session and session["user"]:
        if not user_name:
            user_name = session["user"].get("name", "")
        if not user_email:
            user_email = session["user"].get("email", "")

    result = auto_mail.enhance_email(
        user_name=user_name,
        user_email=user_email,
        admin_name=ADMIN_NAME,
        admin_email=ADMIN_EMAIL,
        subject=subject,
        description=description,
        reference_link=reference_link
    )
    return jsonify(result)

@app.route("/api/send-mail", methods=["POST"])
def send_mail_endpoint():
    """
    Sends the enhanced inquiry to Ashis.
    Requires the user to be logged in (via Google or dev login).
    """
    current_user = session.get("user")
    data = request.get_json() or {}

    if not current_user:
        logger.warning("Send mail blocked: User is not logged in.")
        return jsonify({
            "success": False,
            "requires_login": True,
            "error": "Google sign-in is required before dispatching your email."
        }), 401

    user_name = data.get("user_name") or current_user.get("name", "Prospective Client")
    user_email = current_user.get("email") or data.get("user_email", "client@example.com")
    subject = data.get("subject", "Video Editing Inquiry")
    body = data.get("body", "")
    reference_link = data.get("reference_link", "")

    if not body.strip():
        return jsonify({"success": False, "error": "Email body cannot be empty"}), 400

    result = auto_mail.send_email(
        user_name=user_name,
        user_email=user_email,
        admin_name=ADMIN_NAME,
        admin_email=ADMIN_EMAIL,
        subject=subject,
        body=body,
        reference_link=reference_link
    )

    return jsonify(result)

@app.route("/list_videos")
def list_videos_endpoint():
    logger.info("API request to /list_videos")
    videos = manager.fetch_all_videos()
    return jsonify(videos)

@app.route("/upload", methods=['POST'])
def upload():
    logger.info("Video upload initiated.")
    if not is_admin_authenticated():
        logger.warning("Upload denied: Unauthorized access attempt without admin privileges.")
        return jsonify({"success": False, "error": "Access Denied: Only registered admin can upload videos."}), 403

    if 'video' not in request.files:
        logger.error("Upload failed: No video file provided in the request.")
        return jsonify({"success": False, "error": "No video file provided"}), 400
        
    file = request.files['video']
    title = request.form.get('title', 'Untitled Video')
    
    if file.filename == '':
        logger.error("Upload failed: File selected but filename is empty.")
        return jsonify({"success": False, "error": "No selected file"}), 400
        
    logger.info(f"Processing upload for file: '{file.filename}', Title: '{title}'")
    
    file_bytes = file.read()
    
    # ImageKit Free Tier usually has a 25MB limit. 
    # Checking file size in bytes (25 * 1024 * 1024 = 26214400)
    if len(file_bytes) > 26214400:
        logger.error(f"Upload failed: File '{file.filename}' is too large ({(len(file_bytes)/1024/1024):.2f} MB). Max allowed is 25 MB.")
        return "File too large. Maximum size is 25MB.", 400

    upload_res = manager.upload_video(file_bytes, file.filename, title)
    
    if upload_res and "url" in upload_res:
        logger.info(f"Video uploaded successfully! URL: {upload_res['url']}")
    else:
        logger.error(f"Video upload failed for {file.filename}.")
    
    return redirect(url_for('admin'))

@app.route("/delete_video/<file_id>", methods=['POST'])
def delete_video_endpoint(file_id):
    logger.info(f"Deletion requested for video ID: {file_id}")
    if not is_admin_authenticated():
        logger.warning(f"Delete denied: Unauthorized attempt to delete video ID {file_id}")
        return jsonify({"success": False, "error": "Access Denied: Only registered admin can delete videos."}), 403

    delete_res = manager.delete_video(file_id)
    
    if delete_res and delete_res.get("result") == "ok":
        logger.info(f"Successfully deleted video ID: {file_id}")
    else:
        logger.error(f"Failed to delete video ID: {file_id}. Details: {delete_res}")
        
    return redirect(url_for('admin'))

if __name__ == "__main__":
    logger.info("Starting Portfolio Web Server...")
    app.run(debug=True, host = "0.0.0.0", port=5000)
