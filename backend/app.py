from tarfile import data_filter
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
import os
from dotenv import load_dotenv
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

load_dotenv()

app = Flask(__name__)
CORS(app)

#configure google genai

GENAI_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GENAI_API_KEY:
    print("Warning: GOOGLE_API_KEY is not set. /generate-email will return a 500 until configured.")
else:
    print("Google GenAI API key loaded successfully")

genai.configure(api_key=GENAI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

# Configure Brevo (Sendinblue) transactional email
BREVO_API_KEY = os.getenv("BREVO_API_KEY")
BREVO_SENDER_EMAIL = os.getenv("BREVO_SENDER_EMAIL")
BREVO_SENDER_NAME = os.getenv("BREVO_SENDER_NAME", "No-Reply")
EMAIL_DRY_RUN = os.getenv("EMAIL_DRY_RUN", "false").lower() in {"1", "true", "yes"}

def sanitize_email_body(subject:str, body:str) -> str:
    """Remove any useless information"""
    if not body:
        return ""
    lines=[line.strip() for line in body.split("\n") if line.strip("\n")]
    if not lines:
        return body
    first_line = lines[0].strip()
    subject_norm=(subject or "").strip().rstrip('.').lower()
    first_norm=first_line.rstrip().lower()
    
    return "\n".join(lines[1:])

@app.route('/generate-email',methods=['POST'])
def generate_email():
    data=request.json
    prompt=data.get('prompt')

    if not prompt:
        return jsonify({'error':'Prompt is required'}),400

    if not GENAI_API_KEY:
        return jsonify({'error':'API key is not set'}),500

    try:
        subject_prompt = f"""
Write a single email subject line that accurately summarizes the entire email.

Prompt: {prompt}

Constraints:
- 15 words or fewer
- Precise and to the point; no fluff or clickbait
- Reflect the email’s core message and intent
- Use title case (or proper capitalization); max one punctuation mark
- No emojis, brackets, or quotation marks

Output only the subject line—no explanations.
"""

        subject_response = model.generate_content(subject_prompt)
        subject = (subject_response.text or "").strip()

        body_prompt = f"""
You are a professional email writer.
Write an articulate, concise, professional email body that fully addresses the user's prompt and aligns with the subject.

User prompt: {prompt}
Subject: {subject}

Requirements:
- Begin with a natural greeting (e.g., "Hi [Recipient Name],").
- Be articulate, concise, and logically structured.
- Use flawless grammar, spelling, and punctuation.
- Do not repeat sentences, ideas, or phrases; avoid filler.
- Maintain a professional, courteous tone; use clear transitions.
- If details are missing, make minimal, reasonable assumptions and keep content generic.

Structure:
1) Greeting
2) Main body in 1–3 short paragraphs (bullets only if appropriate)
3) Closing line
4) Signature: "Regards and thanks," then [Sender Name]

Constraints:
- Plain text only (no markdown, emojis, or brackets unless part of the content).
- No meta commentary or instructions.
- Output only the final email body.
"""

        body_response = model.generate_content(body_prompt)
        email_body = sanitize_email_body(subject, (body_response.text or "").strip())

        return jsonify({
            'subject': subject,
            'body': email_body
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/send-email',methods=['POST'])
def send_email():
    data = request.json or {}
    recipients = data.get('recipients') or data.get('recipient')
    subject = data.get('subject')
    body = data.get('body')
    # Allow request payload to enable dry-run without env restart
    effective_dry_run = EMAIL_DRY_RUN or bool(data.get('dry_run'))

    if not recipients or not subject or not body:
        return jsonify({'error': 'recipients (or recipient), subject, and body are required'}), 400

    if not BREVO_API_KEY and not effective_dry_run:
        return jsonify({'error': 'BREVO_API_KEY is not set in the environment variables'}), 500

    if not BREVO_SENDER_EMAIL and not effective_dry_run:
        return jsonify({'error': 'BREVO_SENDER_EMAIL is not set in the environment variables'}), 500

    # Normalize recipients to list of dicts as expected by Brevo SDK
    to_list = []
    if isinstance(recipients, str):
        # Support comma-separated string of emails
        emails = [e.strip() for e in recipients.split(',') if e.strip()]
        to_list = [{"email": e} for e in emails]
    elif isinstance(recipients, list):
        for item in recipients:
            if isinstance(item, dict) and item.get('email'):
                to_list.append({"email": item['email'], "name": item.get('name')})
            elif isinstance(item, str):
                to_list.append({"email": item})

    if not to_list:
        return jsonify({'error': 'No valid recipient emails provided'}), 400

    try:
        if effective_dry_run:
            print("[DRY_RUN] Would send email:")
            print({
                'sender': {"name": BREVO_SENDER_NAME, "email": BREVO_SENDER_EMAIL},
                'to': to_list,
                'subject': subject,
                'body': body[:500] + ("..." if len(body) > 500 else ""),
            })
            return jsonify({'message': 'DRY_RUN enabled: email not sent but request is valid.'}), 200

        # Configure Brevo client
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key['api-key'] = BREVO_API_KEY
        api_client = sib_api_v3_sdk.ApiClient(configuration)
        email_api = sib_api_v3_sdk.TransactionalEmailsApi(api_client)

        # Prepare email content
        html_content = f"<pre style=\"font-family:inherit; white-space:pre-wrap\">{body}</pre>"

        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            sender={"name": BREVO_SENDER_NAME, "email": BREVO_SENDER_EMAIL},
            to=to_list,
            subject=subject,
            html_content=html_content,
            text_content=body
        )

        api_response = email_api.send_transac_email(send_smtp_email)
        return jsonify({'message': 'Email sent successfully', 'brevo_message_id': getattr(api_response, 'message_id', None)}), 200
    except ApiException as e:
        # Extract detailed info when available
        status = getattr(e, 'status', 502) or 502
        reason = getattr(e, 'reason', '')
        body = getattr(e, 'body', '')
        details = None
        try:
            import json as _json
            details = _json.loads(body) if isinstance(body, (str, bytes)) and body else None
        except Exception:
            details = None

        error_payload = {
            'error': 'Brevo API error',
            'status': status,
            'reason': reason,
            'details': details or body or str(e),
        }

        # Map 4xx from Brevo to 400 so client treats it as a user/config error
        http_status = 400 if 400 <= status < 500 else 502
        return jsonify(error_payload), http_status
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv("PORT", "6000"))
    app.run(host="0.0.0.0", port=port, debug=True)