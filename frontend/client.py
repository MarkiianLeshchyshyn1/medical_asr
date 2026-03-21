import requests


class DocumentGenerationClient:
    def __init__(self, backend_base_url: str):
        self.backend_base_url = backend_base_url.rstrip("/")

    def generate_document(
        self,
        audio_bytes: bytes,
        audio_filename: str,
        output_format: str,
    ) -> dict:
        response = requests.post(
            f"{self.backend_base_url}/generate-document",
            files={"audio_file": (audio_filename, audio_bytes)},
            data={"output_format": output_format},
            timeout=600,
        )
        return self._parse_json_response(response)

    def list_history(self) -> list[dict]:
        response = requests.get(f"{self.backend_base_url}/history", timeout=30)
        return self._parse_json_response(response)

    def get_history_item(self, record_id: int) -> dict:
        response = requests.get(f"{self.backend_base_url}/history/{record_id}", timeout=30)
        return self._parse_json_response(response)

    def download_audio(self, record_id: int) -> bytes:
        response = requests.get(f"{self.backend_base_url}/history/{record_id}/audio", timeout=60)
        return self._parse_bytes_response(response)

    def download_document(self, record_id: int) -> bytes:
        response = requests.get(f"{self.backend_base_url}/history/{record_id}/document", timeout=60)
        return self._parse_bytes_response(response)

    def _parse_json_response(self, response: requests.Response):
        if response.ok:
            return response.json()
        raise RuntimeError(self._extract_error(response))

    def _parse_bytes_response(self, response: requests.Response) -> bytes:
        if response.ok:
            return response.content
        raise RuntimeError(self._extract_error(response))

    def _extract_error(self, response: requests.Response) -> str:
        try:
            return response.json().get("detail", response.text)
        except ValueError:
            return response.text
