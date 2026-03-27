import re

import requests


class DocumentGenerationClient:
    def __init__(self, backend_base_url: str):
        self.backend_base_url = backend_base_url.rstrip("/")

    def transcribe_audio(
        self,
        audio_bytes: bytes,
        audio_filename: str,
    ) -> str:
        response = requests.post(
            f"{self.backend_base_url}/transcribe-audio",
            files={"audio_file": (audio_filename, audio_bytes)},
            timeout=600,
        )
        if not response.ok:
            raise RuntimeError(self._extract_error(response))
        payload = response.json()
        return payload["dialogue_text"]

    def generate_document_from_transcript(
        self,
        dialogue_text: str,
        output_format: str,
    ) -> tuple[bytes, str, str]:
        response = requests.post(
            f"{self.backend_base_url}/generate-document-from-transcript",
            json={"dialogue_text": dialogue_text, "output_format": output_format},
            timeout=600,
        )
        if not response.ok:
            raise RuntimeError(self._extract_error(response))

        content_type = response.headers.get("Content-Type", "application/octet-stream")
        filename = self._extract_filename(response) or f"medical_document.{output_format}"
        return response.content, content_type, filename

    def _extract_error(self, response: requests.Response) -> str:
        try:
            return response.json().get("detail", response.text)
        except ValueError:
            return response.text

    def _extract_filename(self, response: requests.Response) -> str | None:
        content_disposition = response.headers.get("Content-Disposition", "")
        match = re.search(r'filename="?([^";]+)"?', content_disposition)
        if not match:
            return None
        return match.group(1)
