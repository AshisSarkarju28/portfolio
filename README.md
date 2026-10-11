# Portfolio Website

A Flask portfolio site with an admin area, Google sign-in, ImageKit video management, and email inquiry tools.

## Requirements

- Python 3.10 or newer
- An ImageKit account for video uploads and listing

## Setup

From the project directory, create and activate a virtual environment, then install the dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Create a `.env` file in the project directory and configure the values needed for your integrations:

```dotenv
SECRET_KEY=replace-with-a-long-random-value
IMAGEKIT_PRIVATE_KEY=your-imagekit-private-key
GOOGLE_CLIENT_ID=your-google-client-id
ADMIN_NAME=Your Name
ADMIN_EMAIL=you@example.com
GROQ_API_KEY=your-groq-api-key
SMTP_USER=you@example.com
SMTP_PASS=your-email-app-password
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
```

`SECRET_KEY` and `IMAGEKIT_PRIVATE_KEY` should be set before deployment. Google sign-in, AI-assisted email, and SMTP delivery require their respective credentials. Keep `.env` private; it is excluded from Git.

## Run

```powershell
python app.py
```

Open <http://127.0.0.1:5000>. The portfolio is at `/`, the admin area at `/admin`, and the service status page at `/status`.