import os
from typing import Any, Dict, List, Optional

import requests
import streamlit as st


def get_backend_url() -> str:
    return os.getenv("BACKEND_URL", "http://localhost:6000").rstrip("/")


def post_json(endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{get_backend_url()}{endpoint}"
    response = requests.post(url, json=payload, timeout=30)
    try:
        data = response.json()
    except Exception:
        data = {"error": response.text}
    if not response.ok:
        # Bubble up backend error message without raising an exception
        message = data.get("error") if isinstance(data, dict) else str(data)
        raise requests.RequestException(f"{response.status_code} {response.reason}: {message}")
    return data


def normalize_recipients(input_value: str) -> List[str]:
    if not input_value:
        return []
    return [part.strip() for part in input_value.split(",") if part.strip()]


st.set_page_config(page_title="Email Generator & Sender", page_icon="📧", layout="centered")
st.title("📧 Email Generator & Sender")

with st.sidebar:
    st.header("Settings")
    default_backend = get_backend_url()
    backend_url = st.text_input("Backend URL", value=default_backend, help="Flask backend base URL")
    if backend_url and backend_url != default_backend:
        os.environ["BACKEND_URL"] = backend_url
    st.caption("Backend endpoints: POST /generate-email, POST /send-email")


if "subject" not in st.session_state:
    st.session_state.subject = ""
if "body" not in st.session_state:
    st.session_state.body = ""


st.subheader("1) Generate Email")
prompt = st.text_area(
    "Prompt",
    placeholder="Describe the email you need...",
    height=140,
)

col_g1, col_g2 = st.columns([1, 2])
with col_g1:
    generate_clicked = st.button("Generate", type="primary")
with col_g2:
    st.caption("Uses Gemini via backend to create a concise subject and a clean email body.")

gen_error: Optional[str] = None
if generate_clicked:
    if not prompt:
        gen_error = "Please enter a prompt."
    else:
        try:
            result = post_json("/generate-email", {"prompt": prompt})
            st.session_state.subject = result.get("subject", "").strip()
            st.session_state.body = result.get("body", "").strip()
        except requests.RequestException as exc:
            gen_error = f"Generation failed: {exc}"

if gen_error:
    st.error(gen_error)

st.text_input("Subject", key="subject", placeholder="Generated subject will appear here")
st.text_area("Body", key="body", height=220, placeholder="Generated email body will appear here")


def count_words(text: str) -> int:
    return len([w for w in (text or "").split() if w.strip()])


with st.expander("Subject guidance"):
    subject_words = count_words(st.session_state.subject)
    st.write(f"Words in subject: {subject_words} (limit: 15)")
    if subject_words > 15:
        st.warning("Subject exceeds 15 words. Consider tightening it.")


st.subheader("2) Send Email")
recipient_input = st.text_input(
    "Recipients",
    placeholder="name@example.com, second@example.com",
    help="Comma-separated list of recipient emails.",
)

dry_run = st.checkbox(
    "Dry run (validate only; do not actually send via Brevo)",
    value=True,
    help="When enabled, the backend won't contact Brevo. Useful before configuring credentials.",
)

send_error: Optional[str] = None
send_success: Optional[str] = None

if st.button("Send Email", type="primary"):
    recipients = normalize_recipients(recipient_input)
    if not recipients:
        send_error = "Please enter at least one recipient email."
    elif not st.session_state.subject:
        send_error = "Subject is required."
    elif not st.session_state.body:
        send_error = "Body is required."
    else:
        # Prepare payload for backend
        payload: Dict[str, Any] = {
            "recipients": recipients,
            "subject": st.session_state.subject,
            "body": st.session_state.body,
            "dry_run": dry_run,
        }
        try:
            result = post_json("/send-email", payload)
            send_success = result.get("message", "Email sent successfully")
        except requests.RequestException as exc:
            send_error = f"Send failed: {exc}"

if send_error:
    st.error(send_error)
if send_success:
    st.success(send_success)

st.divider()
st.caption("Tip: You can edit the subject/body before sending. Configure the backend URL in the sidebar.")


