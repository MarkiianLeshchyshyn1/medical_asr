import io
from datetime import datetime
from pathlib import Path

from docx import Document
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate

from backend.utils import MedicalCard


class DocxGenerator:
    def __init__(self, medical_card: MedicalCard, source_transcript: str = ""):
        self.medical_card = medical_card
        self.source_transcript = source_transcript
        self.document = Document()

    def build(self) -> bytes:
        self._add_generated_at()
        self._add_title()
        self._add_patient_section()
        self._add_complaints_section()
        self._add_diagnosis_section()
        self._add_prescriptions_section()
        self._add_doctor_notes_section()
        self._add_source_transcript_section()
        self._add_missing_info_section()
        return self._to_bytes()

    def _add_generated_at(self) -> None:
        self.document.add_paragraph(self._formatted_datetime())

    def _add_title(self) -> None:
        self.document.add_heading("Медична картка", level=1)

    def _add_patient_section(self) -> None:
        patient = self.medical_card.patient
        self.document.add_paragraph(f"ПІБ пацієнта: {patient.full_name or ''}")
        self.document.add_paragraph(f"Вік: {patient.age if patient.age is not None else ''}")
        self.document.add_paragraph(f"Стать: {patient.gender or ''}")

    def _add_complaints_section(self) -> None:
        self.document.add_heading("Скарги", level=2)
        for complaint in self.medical_card.complaints:
            if complaint.duration:
                self.document.add_paragraph(f"- {complaint.description} ({complaint.duration})")
            else:
                self.document.add_paragraph(f"- {complaint.description}")

    def _add_diagnosis_section(self) -> None:
        if not self.medical_card.diagnosis:
            return
        self.document.add_heading("Діагноз", level=2)
        self.document.add_paragraph(self.medical_card.diagnosis.preliminary or "")

    def _add_prescriptions_section(self) -> None:
        self.document.add_heading("Призначення", level=2)
        for prescription in self.medical_card.prescriptions:
            details = []
            if prescription.dosage:
                details.append(prescription.dosage)
            if prescription.duration:
                details.append(prescription.duration)
            if details:
                self.document.add_paragraph(f"- {prescription.name} ({', '.join(details)})")
            else:
                self.document.add_paragraph(f"- {prescription.name}")

    def _add_doctor_notes_section(self) -> None:
        if not self.medical_card.doctor_notes:
            return
        self.document.add_heading("Нотатки лікаря", level=2)
        self.document.add_paragraph(self.medical_card.doctor_notes)

    def _add_source_transcript_section(self) -> None:
        self.document.add_heading("Транскрипт запису", level=2)
        self.document.add_paragraph(self.source_transcript or "")

    def _add_missing_info_section(self) -> None:
        missing_items = self._collect_missing_info()
        if not missing_items:
            return
        self.document.add_heading("Відсутня інформація", level=2)
        for item in missing_items:
            self.document.add_paragraph(f"- {item}")

    def _collect_missing_info(self) -> list[str]:
        missing: list[str] = []
        patient = self.medical_card.patient
        if not patient.full_name:
            missing.append("Відсутня інформація про ПІБ пацієнта")
        if patient.age is None:
            missing.append("Відсутня інформація про вік")
        if not patient.gender:
            missing.append("Відсутня інформація про стать")
        if not self.medical_card.complaints:
            missing.append("Відсутня інформація про скарги")
        elif any(not complaint.duration for complaint in self.medical_card.complaints):
            missing.append("Відсутня інформація про тривалість скарг")
        if not self.medical_card.diagnosis or not self.medical_card.diagnosis.preliminary:
            missing.append("Відсутня інформація про діагноз")
        if not self.medical_card.prescriptions:
            missing.append("Відсутня інформація про призначення")
        else:
            if any(not prescription.dosage for prescription in self.medical_card.prescriptions):
                missing.append("Відсутня інформація про дозування призначень")
            if any(not prescription.duration for prescription in self.medical_card.prescriptions):
                missing.append("Відсутня інформація про тривалість призначень")
        if not self.medical_card.doctor_notes:
            missing.append("Відсутня інформація про нотатки лікаря")
        if not self.source_transcript:
            missing.append("Відсутня інформація про транскрипт запису")
        return missing

    def _to_bytes(self) -> bytes:
        buffer = io.BytesIO()
        self.document.save(buffer)
        buffer.seek(0)
        return buffer.read()

    def _formatted_datetime(self) -> str:
        generated_at = datetime.now().replace(
            year=self.medical_card.document_date.year,
            month=self.medical_card.document_date.month,
            day=self.medical_card.document_date.day,
        )
        return generated_at.strftime("%H:%M %d.%m.%Y")


class PdfGenerator:
    def __init__(self, medical_card: MedicalCard, source_transcript: str = ""):
        self.medical_card = medical_card
        self.source_transcript = source_transcript
        self.buffer = io.BytesIO()
        self.content: list[Paragraph] = []
        self.document = SimpleDocTemplate(self.buffer, pagesize=A4)

        self.font_name = "DejaVu"
        self.font_path = Path(__file__).resolve().parent / "fonts" / "DejaVuSans.ttf"
        self.title_style: ParagraphStyle | None = None
        self.heading_style: ParagraphStyle | None = None
        self.normal_style: ParagraphStyle | None = None

    def build(self) -> bytes:
        self._setup_font()
        self._setup_styles()
        self._add_generated_at()
        self._add_title()
        self._add_patient_section()
        self._add_complaints_section()
        self._add_diagnosis_section()
        self._add_prescriptions_section()
        self._add_doctor_notes_section()
        self._add_source_transcript_section()
        self._add_missing_info_section()
        return self._to_bytes()

    def _setup_font(self) -> None:
        pdfmetrics.registerFont(TTFont(self.font_name, str(self.font_path)))

    def _setup_styles(self) -> None:
        self.title_style = ParagraphStyle(
            name="TitleStyle",
            fontName=self.font_name,
            fontSize=16,
            spaceAfter=14,
            alignment=1,
        )
        self.heading_style = ParagraphStyle(
            name="HeadingStyle",
            fontName=self.font_name,
            fontSize=12,
            spaceBefore=12,
            spaceAfter=6,
        )
        self.normal_style = ParagraphStyle(
            name="NormalStyle",
            fontName=self.font_name,
            fontSize=10,
            spaceAfter=4,
        )

    def _add_generated_at(self) -> None:
        self.content.append(Paragraph(self._formatted_datetime(), self.normal_style))

    def _add_title(self) -> None:
        self.content.append(Paragraph("Медична картка", self.title_style))

    def _add_patient_section(self) -> None:
        patient = self.medical_card.patient
        self.content.append(Paragraph(f"ПІБ пацієнта: {patient.full_name or ''}", self.normal_style))
        self.content.append(Paragraph(f"Вік: {patient.age if patient.age is not None else ''}", self.normal_style))
        self.content.append(Paragraph(f"Стать: {patient.gender or ''}", self.normal_style))

    def _add_complaints_section(self) -> None:
        self.content.append(Paragraph("Скарги", self.heading_style))
        for complaint in self.medical_card.complaints:
            if complaint.duration:
                self.content.append(Paragraph(f"- {complaint.description} ({complaint.duration})", self.normal_style))
            else:
                self.content.append(Paragraph(f"- {complaint.description}", self.normal_style))

    def _add_diagnosis_section(self) -> None:
        if not self.medical_card.diagnosis:
            return
        self.content.append(Paragraph("Діагноз", self.heading_style))
        self.content.append(Paragraph(self.medical_card.diagnosis.preliminary or "", self.normal_style))

    def _add_prescriptions_section(self) -> None:
        self.content.append(Paragraph("Призначення", self.heading_style))
        for prescription in self.medical_card.prescriptions:
            details = []
            if prescription.dosage:
                details.append(prescription.dosage)
            if prescription.duration:
                details.append(prescription.duration)
            if details:
                self.content.append(Paragraph(f"- {prescription.name} ({', '.join(details)})", self.normal_style))
            else:
                self.content.append(Paragraph(f"- {prescription.name}", self.normal_style))

    def _add_doctor_notes_section(self) -> None:
        if not self.medical_card.doctor_notes:
            return
        self.content.append(Paragraph("Нотатки лікаря", self.heading_style))
        self.content.append(Paragraph(self.medical_card.doctor_notes, self.normal_style))

    def _add_source_transcript_section(self) -> None:
        self.content.append(Paragraph("Транскрипт запису", self.heading_style))
        self.content.append(Paragraph(self.source_transcript or "", self.normal_style))

    def _add_missing_info_section(self) -> None:
        missing_items = self._collect_missing_info()
        if not missing_items:
            return
        self.content.append(Paragraph("Відсутня інформація", self.heading_style))
        for item in missing_items:
            self.content.append(Paragraph(f"- {item}", self.normal_style))

    def _collect_missing_info(self) -> list[str]:
        missing: list[str] = []
        patient = self.medical_card.patient
        if not patient.full_name:
            missing.append("Відсутня інформація про ПІБ пацієнта")
        if patient.age is None:
            missing.append("Відсутня інформація про вік")
        if not patient.gender:
            missing.append("Відсутня інформація про стать")
        if not self.medical_card.complaints:
            missing.append("Відсутня інформація про скарги")
        elif any(not complaint.duration for complaint in self.medical_card.complaints):
            missing.append("Відсутня інформація про тривалість скарг")
        if not self.medical_card.diagnosis or not self.medical_card.diagnosis.preliminary:
            missing.append("Відсутня інформація про діагноз")
        if not self.medical_card.prescriptions:
            missing.append("Відсутня інформація про призначення")
        else:
            if any(not prescription.dosage for prescription in self.medical_card.prescriptions):
                missing.append("Відсутня інформація про дозування призначень")
            if any(not prescription.duration for prescription in self.medical_card.prescriptions):
                missing.append("Відсутня інформація про тривалість призначень")
        if not self.medical_card.doctor_notes:
            missing.append("Відсутня інформація про нотатки лікаря")
        if not self.source_transcript:
            missing.append("Відсутня інформація про транскрипт запису")
        return missing

    def _to_bytes(self) -> bytes:
        self.document.build(self.content)
        self.buffer.seek(0)
        return self.buffer.read()

    def _formatted_datetime(self) -> str:
        generated_at = datetime.now().replace(
            year=self.medical_card.document_date.year,
            month=self.medical_card.document_date.month,
            day=self.medical_card.document_date.day,
        )
        return generated_at.strftime("%H:%M %d.%m.%Y")


def generate_docx(medical_card: MedicalCard, source_transcript: str = "") -> bytes:
    return DocxGenerator(medical_card, source_transcript).build()


def generate_pdf(medical_card: MedicalCard, source_transcript: str = "") -> bytes:
    return PdfGenerator(medical_card, source_transcript).build()
