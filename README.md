## Lumio Partners — Email Generator & Sender

Generate polished email subjects and bodies with Google Gemini, and send real-time emails via Brevo. Includes a Streamlit frontend and a Flask backend.

### Features
- Generate concise subjects (≤ 15 words) and clean, professional email bodies
- Send emails using Brevo (Sendinblue) Transactional Email API
- Streamlit UI with preview/edit, recipients input, and optional Dry Run
- Configurable backend URL and port (default port: 6000)

### Project Structure
```
Lumio_Partners/
  backend/app.py       # Flask API: /generate-email, /send-email
  frontend/app.py      # Streamlit UI
  requirements.txt     # Python dependencies
  myenv/               # (Existing) virtual environment
```

### Prerequisites
- Python 3.10+ (3.13 supported)
- A Brevo account and API key if you want to send real emails
- A Google API key for Gemini (to generate content)

### Setup
1) Create and activate a virtual environment (you may reuse the included `myenv`):

- PowerShell:
```
python -m venv myenv
./myenv/Scripts/Activate.ps1
```

- Git Bash:
```
python -m venv myenv
source myenv/Scripts/activate
```

2) Install dependencies:
```
pip install -r requirements.txt
```

3) Create a `.env` file in the project root:
```
GOOGLE_API_KEY=your_google_gemini_api_key

# Optional for real sends (not required if using Dry Run)
BREVO_API_KEY=your_brevo_api_key
BREVO_SENDER_EMAIL=verified_sender@example.com
BREVO_SENDER_NAME=No-Reply

# Optional: validate only; do not call Brevo
EMAIL_DRY_RUN=true
```

### Run
1) Start the backend (Flask) on port 6000:

- PowerShell:
```
$env:PORT = "6000"
# Optional: stay in validation mode until Brevo credentials are ready
$env:EMAIL_DRY_RUN = "true"
./myenv/Scripts/python.exe backend/app.py
```

- Git Bash:
```
PORT=6000 EMAIL_DRY_RUN=true ./myenv/Scripts/python.exe backend/app.py
```

The backend will listen on `http://localhost:6000`.

2) Start the frontend (Streamlit):
```
./myenv/Scripts/streamlit.exe run frontend/app.py
```

In the Streamlit sidebar, set Backend URL to `http://localhost:6000` if it isn’t already.

### API
- POST `/generate-email`
  - Request JSON:
    ```json
    { "prompt": "Describe the email you need..." }
    ```
  - Response JSON:
    ```json
    { "subject": "Generated concise subject", "body": "Clean professional email body" }
    ```

- POST `/send-email`
  - Request JSON:
    ```json
    {
      "recipients": ["name@example.com", "other@example.com"],
      "subject": "Subject text",
      "body": "Plain text body",
      "dry_run": true
    }
    ```
    - `recipients` may also be an array of objects: `{ "email": "name@example.com", "name": "Name" }`
    - `dry_run` (optional) overrides `EMAIL_DRY_RUN` for that request
  - Response (success):
    ```json
    { "message": "Email sent successfully", "brevo_message_id": "..." }
    ```
  - Response (dry run):
    ```json
    { "message": "DRY_RUN enabled: email not sent but request is valid." }
    ```

### Streamlit Usage
1) Enter a prompt and click Generate to create the subject and body
2) Review/edit the generated content
3) Enter one or more recipient emails (comma-separated)
4) Keep “Dry run” checked to validate, or uncheck it to actually send (requires Brevo vars)
5) Click Send Email

### Brevo Configuration Notes
- Verify `BREVO_SENDER_EMAIL` (or domain) in Brevo before sending
- Ensure Transactional Email is enabled in your Brevo account
- Typical client-side errors will return HTTP 400 with a detailed message from Brevo

### Troubleshooting
- 404 NOT FOUND calling `/generate-email` or `/send-email`:
  - Backend not running or URL/port mismatch; start backend on port 6000 and/or set the Streamlit Backend URL
- 400 BAD REQUEST: Brevo API error:
  - Invalid sender, unverified domain, malformed recipients, or missing credentials
  - Use dry run to validate payloads without contacting Brevo
- 502 BAD GATEWAY from `/send-email`:
  - Transient Brevo/network issue; retry later. Frontend now shows detailed backend error text

### Environment Variables Summary
- `PORT`: Flask server port (defaults to 6000)
- `GOOGLE_API_KEY`: Gemini key used for generation
- `BREVO_API_KEY`: Brevo key used for sending (required for real sends)
- `BREVO_SENDER_EMAIL`: Verified sender email in Brevo
- `BREVO_SENDER_NAME`: Optional sender display name (default: No-Reply)
- `EMAIL_DRY_RUN`: `true/false` to validate without sending

### License
Internal project; add a license if you plan to distribute.


