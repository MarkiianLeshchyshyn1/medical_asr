import streamlit as st
import requests
from pipeline import MainPipeline


st.set_page_config(
    page_title="AI Medical Document Generator",
    page_icon="🩺",
    layout="centered"
)

# ===== HEADER =====
st.markdown(
    "<h2 style='text-align:center;'>Automated Medical Document Generation</h2>",
    unsafe_allow_html=True
)
st.markdown(
    "<p style='text-align:center; color:gray;'>Upload a voice request and receive a ready medical document</p>",
    unsafe_allow_html=True
)

st.divider()

# ===== AUDIO UPLOAD =====
audio_file = st.file_uploader(
    "Voice request (wav / mp3 / m4a)",
    type=["wav", "mp3", "m4a"]
)

# ===== FORMAT SELECT =====
doc_format = st.selectbox(
    "Document format",
    ["PDF", "DOCX"]
)

st.divider()

# ===== ACTION BUTTON =====
generate = st.button(
    "📝 Generate document",
    use_container_width=True
)

@st.cache_resource
def load_pipeline():
    return MainPipeline()

pipeline = load_pipeline()


# ===== PROCESS =====
if generate:
    if audio_file is None:
        st.warning("Please upload an audio file.")
    else:
        with st.spinner("Processing audio and generating document..."):
            try:
                audio_bytes = audio_file.getvalue()

                document_bytes = pipeline.invoke_pipeline(
                    audio_file=audio_bytes,
                    output_format=doc_format.lower()
                )

                st.success("Document successfully generated ✅")

                mime_type = (
                    "application/pdf"
                    if doc_format.lower() == "pdf"
                    else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )

                st.download_button(
                    label="⬇️ Download document",
                    data=document_bytes,
                    file_name=f"medical_document.{doc_format.lower()}",
                    mime=mime_type,
                    use_container_width=True
                )

            except Exception as e:
                st.error(f"Error: {e}")
