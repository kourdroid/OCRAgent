"""Read-only, isolated reproductions for the 2026-09-08 production audit.
No database, network, queue, or customer files are accessed.
Run: python docs/audit_probes_2026_09_08.py
These probes demonstrate existing behavior, not a passing production test suite.
"""
from __future__ import annotations
import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.dossiers.models import DossierCaseContext, RuleDefinitionRequest, DossierReport
from src.dossiers.rules import evaluate_ruleset
from src.dossiers.processor import DossierProcessor
from src.infrastructure.dossier_repos import _serialize_row
from src.infrastructure.paddle_document_provider import _extract_facts
from src.providers.ocr import OCRDocument, OCRPage, OCRLine
from src.dossiers.models import DocumentType
from src.dossiers.reporting import render_report_pdf
from src.api import routes, dossier_routes, admin_routes

def emit(name, **result):
    print(json.dumps({"probe": name, **result}, ensure_ascii=True))

fact = {"field_path":"container_number","value":"ABC123","page":1,"source_text":"Container ABC123","confidence":0.1}
context = DossierCaseContext(case_id="audit",client_id="delassus",documents=[
    {"document_id":"one","document_type":"BILL_OF_LADING","facts":[fact]},
    {"document_id":"two","document_type":"DUM_MLV","facts":[]}
])
rule = {"rule_id":"audit-match","template_type":"EXACT_MATCH","field_path":"container_number","failure_outcome":"BLOCKED"}
ruleset = {"ruleset_id":"audit","version":1,"rules":[rule]}
decision = evaluate_ruleset(context, ruleset)
emit("single_low_confidence_value_matches",status=decision.status,discrepancies=len(decision.discrepancies))

serialized = _serialize_row({**ruleset,"rules":json.dumps([rule])})
try:
    evaluate_ruleset(context,serialized)
except Exception as exc:
    emit("database_json_rules_decode",rules_python_type=type(serialized["rules"]).__name__,error=type(exc).__name__,message=str(exc))

required = RuleDefinitionRequest(name="Required customs document",template_type="REQUIRED_DOCUMENT",field_path="DUM_MLV").model_dump(mode="json")
required["rule_id"]="audit-required"
decision = evaluate_ruleset(context, {"ruleset_id":"audit","version":1,"rules":[required]})
emit("ui_required_document_payload",schema_accepted=True,present_document_type="DUM_MLV",messages=[d.message for d in decision.discrepancies])

for value in ["767208","MSCU1234567"]:
    ocr = OCRDocument(pages=[OCRPage(page=1,width=100,height=100,lines=[OCRLine(text="Container "+value,confidence=.99,bbox=[0,0,1,1])])])
    facts = _extract_facts(ocr,DocumentType.BILL_OF_LADING,("container_number",))
    emit("container_extraction",input=value,values=[f.value for f in facts])

emit("api_route_auth_dependencies",routes=[
    {"path":r.path,"methods":sorted(r.methods),"dependencies":len(r.dependant.dependencies)}
    for module in (routes, dossier_routes, admin_routes)
    for r in module.router.routes if hasattr(r,"dependant")
])

async def completed_source_redelivery():
    repo = AsyncMock()
    repo.get_source_for_job.return_value={"job_status":"COMPLETED","case_id":"audit","workflow_id":"morocco_import_dossier"}
    processor=DossierProcessor(repository=repo,provider=AsyncMock(),workflow_registry=AsyncMock())
    await processor.process_source(job_id="job",case_id="audit",client_id="delassus",workflow_id="morocco_import_dossier",file_path="unused")
    emit("completed_source_redelivery",readiness_checks=repo.is_case_ready_for_decision.await_count,decisions_saved=repo.save_decision.await_count)
asyncio.run(completed_source_redelivery())

report=DossierReport(case={"case_id":"audit"},documents=[],decision={"status":"REVIEW_REQUIRED","summary":"Audit"},reviews=[{"resolution":"OVERRIDDEN","comment":"Literal <b>text"}],audit_events=[])
try:
    render_report_pdf(report)
    emit("report_comment_markup",generated=True)
except Exception as exc:
    emit("report_comment_markup",generated=False,error=type(exc).__name__,message=str(exc)[:200])
