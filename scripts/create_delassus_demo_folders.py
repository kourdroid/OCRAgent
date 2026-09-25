"""Create three local, synthetic Delassus dossier packs for demonstrations."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.lib.colors import HexColor, white
from reportlab.pdfgen import canvas


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = Path(r"C:\Users\Mehdi\Documents\Delassus")
OUTPUT_ROOT = PROJECT_ROOT / "demo_dossiers"
SOURCE_FILES = (
    "bad_411260000216751.pdf",
    "BL 077.PDF",
    "Docs Fournisseur.pdf",
    "DUA.pdf",
    "DUM 7672-08.pdf",
    "FRET 7672-08.pdf",
    "MLV 7672-08.pdf",
)

SCENARIOS = (
    {
        "folder": "01_container_number_mismatch",
        "reference": "DELASSUS-DEMO-CONT-20260818-001",
        "document": "DUM 7672-08.pdf",
        "title": "CONTAINER NUMBER: 9999-99",
        "expected_issue": "DUM container number 9999-99 conflicts with Bill of Lading container 767208.",
        "rule_id": "transport.container_number_match.v1",
        "severity": "critical",
    },
    {
        "folder": "02_weight_mismatch",
        "reference": "DELASSUS-DEMO-WEIGHT-20260818-002",
        "document": "FRET 7672-08.pdf",
        "title": "GROSS WEIGHT: 99,999 KG",
        "expected_issue": "Freight document gross weight differs materially from the transport and declaration documents.",
        "rule_id": "quantities.gross_weight_tolerance.v1",
        "severity": "critical",
    },
    {
        "folder": "03_declaration_reference_mismatch",
        "reference": "DELASSUS-DEMO-REF-20260818-003",
        "document": "DUA.pdf",
        "title": "DECLARATION REF: 41100020269999999",
        "expected_issue": "Declaration reference differs from the reference stated in the BAD and DUM documents.",
        "rule_id": "identity.declaration_reference_match.v1",
        "severity": "critical",
    },
)


def add_exception_banner(source: Path, destination: Path, title: str) -> None:
    reader = PdfReader(str(source))
    writer = PdfWriter()
    for index, page in enumerate(reader.pages):
        if index == 0:
            width = float(page.mediabox.width)
            height = float(page.mediabox.height)
            overlay_path = destination.with_suffix(".overlay.pdf")
            overlay = canvas.Canvas(str(overlay_path), pagesize=(width, height))
            overlay.setFillColor(HexColor("#B42318"))
            overlay.rect(width * 0.04, height * 0.86, width * 0.92, height * 0.10, fill=1, stroke=0)
            overlay.setFillColor(white)
            overlay.setFont("Helvetica-Bold", 13)
            overlay.drawString(width * 0.06, height * 0.92, f"DEMO EXCEPTION - {title}")
            overlay.setFont("Helvetica", 8)
            overlay.drawString(width * 0.06, height * 0.885, "Synthetic training copy for the Ironclad review-workflow demonstration only")
            overlay.save()
            page.merge_page(PdfReader(str(overlay_path)).pages[0])
            overlay_path.unlink()
        writer.add_page(page)
    with destination.open("wb") as output:
        writer.write(output)


def main() -> None:
    missing = [name for name in SOURCE_FILES if not (SOURCE_DIR / name).is_file()]
    if missing:
        raise FileNotFoundError(f"Missing source PDFs: {', '.join(missing)}")

    OUTPUT_ROOT.mkdir(exist_ok=True)
    for scenario in SCENARIOS:
        folder = OUTPUT_ROOT / scenario["folder"]
        if folder.exists():
            shutil.rmtree(folder)
        folder.mkdir()
        for name in SOURCE_FILES:
            source = SOURCE_DIR / name
            destination = folder / name
            if name == scenario["document"]:
                add_exception_banner(source, destination, scenario["title"])
            else:
                shutil.copy2(source, destination)
        manifest = {
            "synthetic_demo": True,
            "external_reference": scenario["reference"],
            "expected_decision": "BLOCKED",
            "modified_document": scenario["document"],
            "expected_issue": scenario["expected_issue"],
            "rule_id": scenario["rule_id"],
            "severity": scenario["severity"],
            "source_document_count": len(SOURCE_FILES),
            "note": "All files are local demo copies. The visible exception banner is intentional.",
        }
        (folder / "DEMO_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        print(f"Created {folder}")


if __name__ == "__main__":
    main()
