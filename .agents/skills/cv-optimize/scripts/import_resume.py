#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.etree import ElementTree


CAREER_ROOT = Path(__file__).resolve().parents[4] / "career"
DEFAULT_IMPORTED_TEXT_PATH = CAREER_ROOT / "profile" / "imported_resume.txt"
DEFAULT_IMPORT_REVIEW_PATH = CAREER_ROOT / "state" / "import_review.jsonl"
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".gif", ".webp"}
TEXT_SUFFIXES = {".txt", ".md", ".rst"}
SECTION_ALIASES = {
    "summary": "SUMMARY",
    "profile": "SUMMARY",
    "professional summary": "SUMMARY",
    "about": "SUMMARY",
    "experience": "EXPERIENCE",
    "work experience": "EXPERIENCE",
    "professional experience": "EXPERIENCE",
    "employment": "EXPERIENCE",
    "education": "EDUCATION",
    "academic background": "EDUCATION",
    "skills": "SKILLS",
    "technical skills": "SKILLS",
    "core skills": "SKILLS",
    "projects": "PROJECTS",
    "personal projects": "PROJECTS",
    "selected projects": "PROJECTS",
    "career focus": "CAREER FOCUS",
    "focus": "CAREER FOCUS",
    "evidence bank": "EVIDENCE BANK",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract text from an uploaded resume and stage it for canonical normalization.",
    )
    parser.add_argument("input_path", help="Path to the uploaded resume file.")
    parser.add_argument(
        "--imported-text-out",
        default=str(DEFAULT_IMPORTED_TEXT_PATH),
        help="Path to write the extracted plain-text resume.",
    )
    parser.add_argument(
        "--review-out",
        default=str(DEFAULT_IMPORT_REVIEW_PATH),
        help="Path to append the import review report as JSONL.",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print the extracted text to stdout after writing local artifacts.",
    )
    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def run_command(command: list[str]) -> str:
    result = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def text_signal_strength(text: str) -> float:
    if not text.strip():
        return 0.0
    visible = [char for char in text if not char.isspace()]
    if not visible:
        return 0.0
    alnum = [char for char in visible if char.isalnum()]
    return len(alnum) / max(len(visible), 1)


def extract_text_from_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def extract_text_from_docx(path: Path) -> str:
    paragraphs: list[str] = []
    with zipfile.ZipFile(path) as archive:
        try:
            raw_xml = archive.read("word/document.xml")
        except KeyError as error:
            raise ValueError("DOCX file does not contain word/document.xml") from error
    root = ElementTree.fromstring(raw_xml)
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    for paragraph in root.findall(".//w:p", namespace):
        parts = []
        for node in paragraph.findall(".//w:t", namespace):
            parts.append(node.text or "")
        line = "".join(parts).strip()
        if line:
            paragraphs.append(line)
    return "\n".join(paragraphs)


def extract_text_from_pdf(path: Path) -> tuple[str, str, str, bool, list[str]]:
    notes: list[str] = []
    if command_exists("pdftotext"):
        extracted = run_command(["pdftotext", "-layout", str(path), "-"])
        if len(extracted.strip()) >= 200 and text_signal_strength(extracted) >= 0.45:
            return extracted, "pdftotext", "high", False, notes
        notes.append("Embedded PDF text was too weak; trying OCR fallback.")
    else:
        notes.append("pdftotext was not available; trying OCR fallback.")

    if not command_exists("pdftoppm") or not command_exists("tesseract"):
        raise RuntimeError(
            "Could not extract text from PDF. Install poppler-utils and tesseract-ocr, "
            "or provide a TXT/MD/DOCX version."
        )

    ocr_parts: list[str] = []
    with TemporaryDirectory(prefix="resume_pdf_") as tmp_dir:
        prefix = Path(tmp_dir) / "page"
        subprocess.run(
            ["pdftoppm", "-png", str(path), str(prefix)],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        page_images = sorted(Path(tmp_dir).glob("page-*.png"))
        if not page_images:
            raise RuntimeError("OCR fallback did not generate any page images.")
        for image_path in page_images:
            ocr_parts.append(run_command(["tesseract", str(image_path), "stdout"]))
    notes.append("OCR fallback was used; review imported facts before trusting them.")
    return "\n".join(ocr_parts), "ocr_pdf", "low", True, notes


def extract_text_from_image(path: Path) -> tuple[str, str, str, bool, list[str]]:
    if not command_exists("tesseract"):
        raise RuntimeError("Image OCR requires tesseract-ocr.")
    text = run_command(["tesseract", str(path), "stdout"])
    notes = ["Image OCR fallback was used; review imported facts before trusting them."]
    return text, "ocr_image", "low", True, notes


def detect_sections(text: str) -> list[str]:
    detected: list[str] = []
    seen = set()
    for raw_line in text.splitlines():
        key = re.sub(r"[^a-z0-9 ]+", " ", raw_line.lower()).strip()
        if key in SECTION_ALIASES:
            canonical = SECTION_ALIASES[key]
            if canonical not in seen:
                detected.append(canonical)
                seen.add(canonical)
    return detected


def extract_contacts(text: str) -> dict[str, str]:
    contacts: dict[str, str] = {}
    email_match = re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text)
    if email_match:
        contacts["email"] = email_match.group(0)
    linkedin_match = re.search(r"https?://(?:www\.)?linkedin\.com/[^\s)]+", text)
    if linkedin_match:
        contacts["linkedin"] = linkedin_match.group(0)
    github_match = re.search(r"https?://(?:www\.)?github\.com/[^\s)]+", text)
    if github_match:
        contacts["github"] = github_match.group(0)
    return contacts


def build_review_row(
    input_path: Path,
    extraction_method: str,
    confidence: str,
    review_required: bool,
    extracted_text: str,
    notes: list[str],
) -> dict[str, object]:
    return {
        "recorded_at": utc_now(),
        "source_file": str(input_path),
        "source_format": input_path.suffix.lower().lstrip("."),
        "extraction_method": extraction_method,
        "confidence": confidence,
        "review_required": review_required,
        "detected_sections": detect_sections(extracted_text),
        "detected_contacts": extract_contacts(extracted_text),
        "notes": notes,
        "line_count": len([line for line in extracted_text.splitlines() if line.strip()]),
    }


def append_jsonl(path: Path, row: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
        handle.write("\n")


def extract_resume(path: Path) -> tuple[str, str, str, bool, list[str]]:
    suffix = path.suffix.lower()
    if suffix in TEXT_SUFFIXES:
        return extract_text_from_text_file(path), "plain_text", "high", False, []
    if suffix == ".docx":
        return extract_text_from_docx(path), "docx_xml", "medium", False, []
    if suffix == ".pdf":
        return extract_text_from_pdf(path)
    if suffix in IMAGE_SUFFIXES:
        return extract_text_from_image(path)
    raise ValueError(
        f"Unsupported input format: {path.suffix or '<none>'}. "
        "Supported formats: PDF, DOCX, TXT, MD, and common image files."
    )


def main() -> None:
    try:
        args = parse_args()
        input_path = Path(args.input_path).resolve()
        if not input_path.exists():
            raise FileNotFoundError(f"missing input file: {input_path}")

        extracted_text, extraction_method, confidence, review_required, notes = extract_resume(input_path)
        normalized_text = normalize_text(extracted_text)

        imported_text_path = Path(args.imported_text_out).resolve()
        imported_text_path.parent.mkdir(parents=True, exist_ok=True)
        imported_text_path.write_text(normalized_text, encoding="utf-8")

        review_row = build_review_row(
            input_path=input_path,
            extraction_method=extraction_method,
            confidence=confidence,
            review_required=review_required,
            extracted_text=normalized_text,
            notes=notes,
        )
        append_jsonl(Path(args.review_out).resolve(), review_row)

        print(f"imported_text: {imported_text_path}")
        print(f"extraction_method: {extraction_method}")
        print(f"confidence: {confidence}")
        print(f"review_required: {str(review_required).lower()}")
        print(f"detected_sections: {', '.join(review_row['detected_sections']) or '<none>'}")

        if args.stdout:
            print("\n--- extracted text ---\n")
            print(normalized_text)
    except (FileNotFoundError, RuntimeError, ValueError, subprocess.CalledProcessError, zipfile.BadZipFile) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
