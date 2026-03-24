import os
import time
from concurrent.futures import ThreadPoolExecutor

import streamlit as st

from client import DocumentGenerationClient

BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://127.0.0.1:8000")


def format_generation_time(elapsed_seconds: float) -> str:
    return f"{elapsed_seconds:.2f} sec"


def reset_review_state() -> None:
    st.session_state.pop("transcript", None)
    st.session_state.pop("numbered_transcript", None)
    st.session_state.pop("segments", None)
    st.session_state.pop("dialogue_turns", None)
    st.session_state.pop("dialogue_text", None)
    st.session_state.pop("transcript_source_key", None)
    st.session_state.pop("document_bytes", None)
    st.session_state.pop("document_mime_type", None)
    st.session_state.pop("document_filename", None)


def apply_helsi_styles() -> None:
    st.markdown(
        """
        <style>
            .stApp { background: #A3C8FF; }
            .block-container { max-width: 980px; padding-top: 3rem; padding-bottom: 2rem; }
            .helsi-hero {
                background: linear-gradient(180deg, #4f9cf0 0%, #5aa5f2 100%);
                border-radius: 24px;
                padding: 28px 24px 22px 24px;
                color: white;
                margin-bottom: 18px;
                text-align: center;
            }
            .helsi-logo { font-size: 32px; font-weight: 800; margin: 0; line-height: 1.2; }
            .helsi-subtitle { font-size: 20px; color: rgba(255,255,255,0.95); margin-top: 12px; margin-bottom: 0; line-height: 1.35; }
            label, .stRadio label, .stFileUploader label, .stSelectbox label, .stAudioInput label {
                color: #1f3b63 !important;
                font-weight: 600;
                font-size: 18px !important;
            }
            .stRadio > div {
                background: rgba(255, 255, 255, 0.18);
                border-radius: 18px;
                padding: 12px 14px;
            }
            .stRadio p, .stRadio span { color: #24456f !important; }
            div[data-baseweb="select"] > div, div[data-testid="stFileUploaderDropzone"] {
                border: 1px solid #d8e7fb;
                border-radius: 18px;
                background: rgba(255, 255, 255, 0.92);
                color: #24456f;
            }
            div[data-testid="stFileUploaderDropzone"] * { color: #24456f !important; }
            .stAudio { background: rgba(255, 255, 255, 0.92); border-radius: 16px; padding: 8px; }
            .stButton > button, .stDownloadButton > button {
                background: linear-gradient(180deg, #5ba9f5 0%, #4f97e8 100%);
                color: white;
                border: none;
                border-radius: 14px;
                font-weight: 600;
                min-height: 48px;
                box-shadow: 0 10px 22px rgba(79, 151, 232, 0.26);
            }
            .stButton > button:hover, .stDownloadButton > button:hover {
                background: linear-gradient(180deg, #4f97e8 0%, #4588d3 100%);
                color: white;
            }
            .stAlert { border-radius: 16px; }
            div[data-baseweb="notification"][kind="success"] {
                background: #ffffff !important;
                border: 2px solid #1f8a4c !important;
            }
            div[data-baseweb="notification"][kind="success"] p {
                color: #0f2f57 !important;
                font-weight: 700 !important;
            }
            div[data-baseweb="notification"][kind="error"] {
                background: #ffffff !important;
                border: 2px solid #c02f2f !important;
            }
            div[data-baseweb="notification"][kind="error"] p {
                color: #4a0f0f !important;
                font-weight: 700 !important;
            }
            .timer-banner {
                background: #ffffff;
                border: 2px solid #3f7fca;
                border-radius: 14px;
                color: #0f2f57;
                font-weight: 700;
                padding: 12px 14px;
            }
            .success-banner {
                background: #ffffff;
                border: 2px solid #1f8a4c;
                border-radius: 14px;
                color: #0f2f57;
                font-weight: 700;
                padding: 12px 14px;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_audio_source_selector() -> tuple[bytes | None, str | None]:
    source_type = st.radio("Audio source", ["Upload WAV file", "Record audio"], horizontal=True)

    if source_type == "Upload WAV file":
        uploaded_file = st.file_uploader("Voice request (wav)", type=["wav"])
        if uploaded_file is None:
            return None, None
        audio_bytes = uploaded_file.getvalue()
        st.audio(audio_bytes, format="audio/wav")
        return audio_bytes, uploaded_file.name

    recorded_audio = st.audio_input("Record voice request")
    if recorded_audio is None:
        return None, None

    audio_bytes = recorded_audio.getvalue()
    st.audio(audio_bytes, format="audio/wav")
    return audio_bytes, "recorded_audio.wav"


def generate_document_with_live_timer(
    client: DocumentGenerationClient,
    transcript: str,
    output_format: str,
) -> tuple[bytes, str, str, float]:
    timer_placeholder = st.empty()
    start_time = time.perf_counter()

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(client.generate_document_from_transcript, transcript, output_format)

        while not future.done():
            elapsed_seconds = time.perf_counter() - start_time
            timer_placeholder.markdown(
                f'<div class="timer-banner">Generation in progress: {format_generation_time(elapsed_seconds)}</div>',
                unsafe_allow_html=True,
            )
            time.sleep(0.1)

        document_bytes, mime_type, filename = future.result()

    elapsed_seconds = time.perf_counter() - start_time
    timer_placeholder.markdown(
        f'<div class="timer-banner">Generation time: {format_generation_time(elapsed_seconds)}</div>',
        unsafe_allow_html=True,
    )
    return document_bytes, mime_type, filename, elapsed_seconds


def transcribe_audio_with_live_timer(
    client: DocumentGenerationClient,
    audio_bytes: bytes,
    audio_filename: str,
) -> tuple[str, str, list[dict], list[dict], str, float]:
    timer_placeholder = st.empty()
    start_time = time.perf_counter()

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(client.transcribe_audio, audio_bytes, audio_filename)

        while not future.done():
            elapsed_seconds = time.perf_counter() - start_time
            timer_placeholder.markdown(
                f'<div class="timer-banner">Transcription in progress: {format_generation_time(elapsed_seconds)}</div>',
                unsafe_allow_html=True,
            )
            time.sleep(0.1)

        transcript, numbered_transcript, segments, dialogue_turns, dialogue_text = future.result()

    elapsed_seconds = time.perf_counter() - start_time
    timer_placeholder.markdown(
        f'<div class="timer-banner">Transcription time: {format_generation_time(elapsed_seconds)}</div>',
        unsafe_allow_html=True,
    )
    return transcript, numbered_transcript, segments, dialogue_turns, dialogue_text, elapsed_seconds


def render_generation_view(client: DocumentGenerationClient) -> None:
    st.markdown(
        """
        <div class="helsi-hero">
            <div class="helsi-logo">Automated medical document generation</div>
            <p class="helsi-subtitle">Upload or record a voice request and receive a ready medical document</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()
    audio_bytes, audio_filename = render_audio_source_selector()
    st.divider()

    if audio_bytes is None or audio_filename is None:
        st.info("Please upload or record a WAV audio file.")
        return

    current_source_key = f"{audio_filename}:{len(audio_bytes)}"
    previous_source_key = st.session_state.get("transcript_source_key")
    if previous_source_key != current_source_key:
        reset_review_state()
        st.session_state["transcript_source_key"] = current_source_key

    if st.button("Transcribe audio", use_container_width=True):
        try:
            transcript, numbered_transcript, segments, dialogue_turns, dialogue_text, _ = transcribe_audio_with_live_timer(
                client=client,
                audio_bytes=audio_bytes,
                audio_filename=audio_filename,
            )
            st.session_state["transcript"] = transcript
            st.session_state["numbered_transcript"] = numbered_transcript
            st.session_state["segments"] = segments
            st.session_state["dialogue_turns"] = dialogue_turns
            st.session_state["dialogue_text"] = dialogue_text
            st.session_state.pop("document_bytes", None)
            st.session_state.pop("document_mime_type", None)
            st.session_state.pop("document_filename", None)
        except Exception as e:
            st.error(f"Error: {e}")
            return

    dialogue_text_value = st.session_state.get("dialogue_text")
    if dialogue_text_value is None:
        return

    st.divider()
    st.subheader("Doctor review")
    approved_transcript = st.text_area(
        "Review and edit transcript before approval",
        height=300,
        key="dialogue_text",
    )
    doc_format = st.selectbox("Document format", ["PDF", "DOCX"])
    is_approved = st.checkbox("I confirm that the transcript is reviewed and approved by the doctor.")

    if st.button("Generate document", use_container_width=True):
        if not approved_transcript.strip():
            st.warning("Transcript must not be empty.")
            return

        if not is_approved:
            st.warning("Please approve the transcript before generating the document.")
            return

        try:
            document_bytes, mime_type, filename, _ = generate_document_with_live_timer(
                client=client,
                transcript=approved_transcript,
                output_format=doc_format.lower(),
            )
            st.session_state["document_bytes"] = document_bytes
            st.session_state["document_mime_type"] = mime_type
            st.session_state["document_filename"] = filename
        except Exception as e:
            st.error(f"Error: {e}")
            return

    document_bytes = st.session_state.get("document_bytes")
    if document_bytes is None:
        return

    st.markdown(
        '<div class="success-banner">Document generated successfully.</div>',
        unsafe_allow_html=True,
    )
    st.download_button(
        label="Download document",
        data=document_bytes,
        file_name=st.session_state["document_filename"],
        mime=st.session_state["document_mime_type"],
        use_container_width=True,
    )


def run_app() -> None:
    client = DocumentGenerationClient(BACKEND_BASE_URL)

    st.set_page_config(page_title="AI Medical Document Generator", page_icon="🩺", layout="wide")
    apply_helsi_styles()
    render_generation_view(client)


run_app()
