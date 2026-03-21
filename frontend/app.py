import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import BACKEND_BASE_URL
from frontend.client import DocumentGenerationClient


def format_generation_time(elapsed_seconds: float) -> str:
    return f"{elapsed_seconds:.2f} sec"


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
            }
            .helsi-logo { font-size: 18px; font-weight: 700; margin: 0; white-space: nowrap; }
            .helsi-subtitle { font-size: 15px; color: rgba(255,255,255,0.88); margin-top: 10px; margin-bottom: 0; }
            .history-card, .download-card {
                background: rgba(255, 255, 255, 0.92);
                border-radius: 18px;
                padding: 18px;
                border: 1px solid #d8e7fb;
                color: #24456f;
                margin-bottom: 16px;
            }
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
    audio_bytes: bytes,
    audio_filename: str,
    output_format: str,
) -> tuple[dict, float]:
    timer_placeholder = st.empty()
    start_time = time.perf_counter()

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(client.generate_document, audio_bytes, audio_filename, output_format)

        while not future.done():
            elapsed_seconds = time.perf_counter() - start_time
            timer_placeholder.info(f"Generation in progress: {format_generation_time(elapsed_seconds)}")
            time.sleep(0.1)

        result = future.result()

    elapsed_seconds = time.perf_counter() - start_time
    timer_placeholder.info(f"Generation time: {format_generation_time(elapsed_seconds)}")
    return result, elapsed_seconds


def render_sidebar_history(client: DocumentGenerationClient) -> None:
    st.sidebar.title("History")

    if st.sidebar.button("New transcription", use_container_width=True):
        st.session_state["selected_record_id"] = None

    try:
        history_items = client.list_history()
    except Exception as e:
        st.sidebar.error(f"History unavailable: {e}")
        return

    if not history_items:
        st.sidebar.info("No history yet.")
        return

    for item in history_items:
        label = f"{item['id']} | {item['transcript_preview'] or 'No transcript'}"
        if st.sidebar.button(label, key=f"history_{item['id']}", use_container_width=True):
            st.session_state["selected_record_id"] = item["id"]


def render_history_detail(client: DocumentGenerationClient, record_id: int) -> None:
    record = client.get_history_item(record_id)
    audio_bytes = client.download_audio(record_id)
    document_bytes = client.download_document(record_id)

    st.markdown(
        """
        <div class="helsi-hero">
            <div class="helsi-logo">Saved transcription</div>
            <p class="helsi-subtitle">Open previous results and download the source audio or generated document</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="history-card">
            <strong>ID:</strong> {record["id"]}<br>
            <strong>Created:</strong> {record["created_at"]}<br>
            <strong>Transcript:</strong><br>{record["transcript"]}
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="download-card"><strong>Source audio</strong><br>Download original WAV file.</div>', unsafe_allow_html=True)
        st.download_button(
            label="Download audio",
            data=audio_bytes,
            file_name=record["audio_filename"],
            mime="audio/wav",
            use_container_width=True,
        )

    with col2:
        st.markdown('<div class="download-card"><strong>Generated file</strong><br>Download generated medical document.</div>', unsafe_allow_html=True)
        mime_type = (
            "application/pdf"
            if record["output_format"] == "pdf"
            else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        st.download_button(
            label="Download document",
            data=document_bytes,
            file_name=record["document_filename"],
            mime=mime_type,
            use_container_width=True,
        )


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
    doc_format = st.selectbox("Document format", ["PDF", "DOCX"])
    st.divider()

    if not st.button("Generate document", use_container_width=True):
        return

    if audio_bytes is None or audio_filename is None:
        st.warning("Please upload or record a WAV audio file.")
        return

    try:
        result, _ = generate_document_with_live_timer(
            client=client,
            audio_bytes=audio_bytes,
            audio_filename=audio_filename,
            output_format=doc_format.lower(),
        )
        st.session_state["selected_record_id"] = result["id"]
        st.rerun()
    except Exception as e:
        st.error(f"Error: {e}")


def run_app() -> None:
    client = DocumentGenerationClient(BACKEND_BASE_URL)

    st.set_page_config(page_title="AI Medical Document Generator", page_icon="🩺", layout="wide")
    apply_helsi_styles()

    if "selected_record_id" not in st.session_state:
        st.session_state["selected_record_id"] = None

    render_sidebar_history(client)

    selected_record_id = st.session_state["selected_record_id"]
    if selected_record_id is None:
        render_generation_view(client)
    else:
        render_history_detail(client, selected_record_id)


run_app()
