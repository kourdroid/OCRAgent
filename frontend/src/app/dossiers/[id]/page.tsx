"use client";

import * as React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  AlertTriangle,
  ArrowLeft,
  Check,
  Download,
  ExternalLink,
  FileText,
  LoaderCircle,
  RefreshCw,
  RotateCcw,
  ShieldAlert,
  X,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { useDossier } from "@/hooks/use-dossier";
import {
  downloadDossierReport,
  reprocessDossier,
  reviewDossier,
} from "@/lib/api";
import { DELASSUS_CLIENT_ID } from "@/lib/clients";
import type {
  DossierComparedValue,
  DossierDiscrepancy,
} from "@/lib/types";

function formatValue(value: string | number | boolean | null): string {
  if (value === null) return "-";
  if (typeof value === "number") {
    return new Intl.NumberFormat("en-US", { maximumFractionDigits: 3 }).format(value);
  }
  return String(value);
}

function decisionClasses(status: string): string {
  if (status === "READY") return "border-emerald-800 bg-emerald-950/20 text-emerald-300";
  if (status === "BLOCKED") return "border-red-800 bg-red-950/20 text-red-300";
  return "border-amber-800 bg-amber-950/20 text-amber-300";
}

export default function DossierReviewPage() {
  const params = useParams<{ id: string }>();
  const caseId = params.id;
  const { dossier, isLoading, error, refetch } = useDossier(
    caseId,
    DELASSUS_CLIENT_ID,
  );
  const [activeDocumentId, setActiveDocumentId] = React.useState<string | null>(null);
  const [activePage, setActivePage] = React.useState(1);
  const [comment, setComment] = React.useState("");
  const [actionError, setActionError] = React.useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  const activeDocument =
    dossier?.documents.find((item) => item.document_id === activeDocumentId) ??
    dossier?.documents[0] ??
    null;
  const displayedPage = activeDocumentId
    ? activePage
    : (activeDocument?.page_start ?? activePage);
  const pendingReview = dossier?.reviews.find((review) => review.status === "PENDING");

  function openEvidence(value: DossierComparedValue) {
    setActiveDocumentId(value.document_id);
    setActivePage(value.evidence.page);
  }

  async function submitReview(action: "APPROVE" | "REJECT" | "OVERRIDE") {
    if (!dossier?.decision || comment.trim().length < 3) {
      setActionError("Ajoutez un commentaire d’au moins trois caractères.");
      return;
    }
    setIsSubmitting(true);
    setActionError(null);
    try {
      await reviewDossier(caseId, {
        client_id: DELASSUS_CLIENT_ID,
        action,
        comment: comment.trim(),
        expected_decision_version: dossier.decision.decision_version,
        idempotency_key: crypto.randomUUID(),
      });
      setComment("");
      await refetch();
    } catch (cause) {
      setActionError(cause instanceof Error ? cause.message : "Review failed");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function submitReprocess() {
    if (!dossier || comment.trim().length < 3) {
      setActionError("Indiquez une raison avant de relancer le traitement.");
      return;
    }
    setIsSubmitting(true);
    setActionError(null);
    try {
      await reprocessDossier(caseId, {
        client_id: DELASSUS_CLIENT_ID,
        document_ids: dossier.sources.map((source) => source.document_id),
        reason: comment.trim(),
      });
      setComment("");
      await refetch();
    } catch (cause) {
      setActionError(cause instanceof Error ? cause.message : "Reprocessing failed");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-zinc-950 text-zinc-400">
        <LoaderCircle className="mr-2 h-5 w-5 animate-spin" />
        Chargement du dossier…
      </div>
    );
  }

  if (error || !dossier) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-zinc-950 px-5 text-center">
        <AlertTriangle className="h-8 w-8 text-red-400" />
        <p className="text-sm text-red-700">{error ?? "Dossier introuvable"}</p>
        <Button
          render={<Link href="/dossiers" />}
          variant="outline"
          className="border-zinc-700"
        >
          Retour aux dossiers
        </Button>
      </div>
    );
  }

  const decision = dossier.decision;
  const displayStatus = decision?.status ?? dossier.case.status;
  const displaySummary = decision?.summary ?? (
    dossier.case.status === "FAILED"
      ? "Le traitement a échoué avant la décision. Indiquez une raison puis relancez le dossier."
      : "Les documents sont en cours d’analyse. Les informations seront présentées avec leurs sources."
  );

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="flex min-h-16 items-center justify-between gap-4 px-4">
          <div className="flex min-w-0 items-center gap-2">
            <SidebarTrigger className="text-zinc-400 hover:bg-zinc-900" />
            <Button
              render={<Link href="/dossiers" />}
              variant="ghost"
              size="icon"
              title="Retour aux dossiers"
              className="text-slate-500 hover:bg-slate-50"
            >
              <ArrowLeft className="h-4 w-4" />
            </Button>
            <div className="min-w-0">
              <h1 className="truncate text-sm font-semibold">
                {dossier.case.external_reference ?? caseId.slice(0, 8).toUpperCase()}
              </h1>
              <p className="truncate font-mono text-[10px] text-slate-400">{caseId}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="rounded-md border-slate-200 bg-slate-50 text-slate-600">
              {dossier.case.status}
            </Badge>
            <Button
              variant="outline"
              size="icon"
              title="Actualiser le dossier"
              onClick={() => void refetch()}
              className="border-slate-200 bg-white text-slate-500 hover:bg-slate-50"
            >
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </header>

      <main className="grid min-h-[calc(100vh-4rem)] lg:grid-cols-[minmax(420px,1.1fr)_minmax(420px,0.9fr)]">
        <section className="flex min-h-[620px] flex-col border-b border-slate-200 bg-white lg:border-b-0 lg:border-r">
          <div className="flex gap-1 overflow-x-auto border-b border-slate-200 bg-white p-3">
            {dossier.documents.map((documentItem) => (
              <button
                key={documentItem.document_id}
                type="button"
                onClick={() => {
                  setActiveDocumentId(documentItem.document_id);
                  setActivePage(documentItem.page_start);
                }}
                className={`flex shrink-0 items-center gap-2 border px-3 py-2 text-xs transition-colors ${
                  documentItem.document_id === activeDocument?.document_id
                    ? "border-blue-300 bg-blue-50 text-blue-700"
                    : "border-slate-200 text-slate-500 hover:border-slate-300 hover:text-slate-800"
                }`}
              >
                <FileText className="h-3.5 w-3.5" />
                {documentItem.document_type}
                <span className="font-mono text-[10px] opacity-60">
                  P{documentItem.page_start}-{documentItem.page_end}
                </span>
              </button>
            ))}
          </div>

          {activeDocument ? (
            <>
              <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3 text-xs">
                <div className="min-w-0">
                  <p className="truncate font-medium text-slate-700">{activeDocument.original_filename}</p>
                  <p className="font-mono text-[10px] text-slate-400">
                    Page {displayedPage} / fiabilité {" "}
                    {Number(activeDocument.classification_confidence ?? 0).toFixed(2)}
                  </p>
                </div>
                <Button
                  render={
                    <a
                      href={`${activeDocument.file_url}#page=${displayedPage}`}
                      target="_blank"
                      rel="noreferrer"
                    />
                  }
                  variant="ghost"
                  size="icon"
                  title="Ouvrir le PDF dans un nouvel onglet"
                  className="text-slate-500 hover:bg-slate-50"
                >
                  <ExternalLink className="h-4 w-4" />
                </Button>
              </div>
              <iframe
                key={`${activeDocument.document_id}:${displayedPage}`}
                title={`Source document ${activeDocument.document_type}`}
                src={`${activeDocument.file_url}#page=${displayedPage}&view=FitH`}
                className="min-h-[540px] flex-1 bg-slate-100"
              />
            </>
          ) : (
            <div className="flex flex-1 items-center justify-center text-sm text-slate-400">
              Les documents apparaîtront après leur classification.
            </div>
          )}
        </section>

        <section className="min-w-0 overflow-y-auto bg-white">
          <div className="border-b border-slate-200 p-6">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Décision actuelle</p>
                <h2 className="mt-1 text-lg font-semibold">
                  {displayStatus}
                </h2>
              </div>
              {decision && (
                <Badge
                  variant="outline"
                  className={`rounded-sm ${decisionClasses(decision.status)}`}
                >
                  V{decision.decision_version}
                </Badge>
              )}
            </div>
            <p className="mt-3 text-sm leading-6 text-slate-600">
              {displaySummary}
            </p>
            {decision && (
              <div className="mt-4 flex flex-wrap gap-2">
                <Button
                  onClick={() => void downloadDossierReport(caseId, DELASSUS_CLIENT_ID, "json")}
                  variant="outline"
                  className="border-slate-300 bg-white"
                >
                  <Download className="h-4 w-4" />
                  Données JSON
                </Button>
                <Button
                  onClick={() => void downloadDossierReport(caseId, DELASSUS_CLIENT_ID, "pdf")}
                  variant="outline"
                  className="border-slate-300 bg-white"
                >
                  <Download className="h-4 w-4" />
                  Rapport PDF
                </Button>
              </div>
            )}
          </div>

          <div className="border-b border-slate-200 p-6">
            <h3 className="text-sm font-semibold">Origine des documents</h3>
            <div className="mt-3 divide-y divide-slate-200 border-y border-slate-200">
              {dossier.sources.map((source) => (
                <div key={source.document_id} className="grid gap-1 px-2 py-3 text-xs sm:grid-cols-[1fr_auto]">
                  <span className="truncate text-slate-700">{source.original_filename}</span>
                  <span className="font-mono text-[10px] text-slate-400">{source.provenance_status ?? "À compléter"}</span>
                  <span className="text-slate-500">Expéditeur : {source.sender_party_name ?? "Inconnu"}</span>
                  <span className="text-slate-500">Émetteur : {source.issuer_party_name ?? "Inconnu"}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="border-b border-slate-200 p-6">
            <h3 className="text-sm font-semibold">Points à vérifier</h3>
            <div className="mt-3 space-y-3">
              {!decision?.discrepancies.length && (
                <p className="text-sm text-slate-400">Aucun point à vérifier pour le moment.</p>
              )}
              {decision?.discrepancies.map((item: DossierDiscrepancy) => (
                <div key={item.rule_id} className="rounded-lg border border-slate-200 p-4">
                  <div className="flex items-start gap-2">
                    <ShieldAlert
                      className={`mt-0.5 h-4 w-4 shrink-0 ${
                        item.severity === "critical" ? "text-red-400" : "text-amber-400"
                      }`}
                    />
                    <div className="min-w-0">
                      <p className="font-mono text-[10px] text-slate-400">{item.rule_id}</p>
                      <p className="mt-1 text-sm text-slate-700">{item.message}</p>
                    </div>
                  </div>
                  {item.values.length > 0 && (
                    <div className="mt-3 grid gap-2">
                      {item.values.map((value, index) => (
                        <button
                          key={`${value.document_id}:${value.field_path}:${index}`}
                          type="button"
                          onClick={() => openEvidence(value)}
                          className="grid grid-cols-[1fr_auto] gap-3 rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-left hover:border-blue-300"
                        >
                          <div className="min-w-0">
                            <p className="truncate text-xs text-slate-700">
                              {formatValue(value.value)}
                            </p>
                            <p className="truncate text-[10px] text-slate-400">
                              {value.evidence.source_text}
                            </p>
                          </div>
                          <span className="font-mono text-[10px] text-blue-600">
                            P{value.evidence.page}
                          </span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="border-b border-slate-200 p-6">
            <h3 className="text-sm font-semibold">Informations extraites</h3>
            <div className="mt-3 divide-y divide-slate-200 border-y border-slate-200">
              {(activeDocument?.facts ?? []).map((fact) => (
                <button
                  key={`${fact.field_path}:${fact.page}`}
                  type="button"
                  onClick={() => setActivePage(fact.page)}
                  className="grid w-full grid-cols-[minmax(120px,0.8fr)_1fr_auto] gap-3 px-2 py-3 text-left hover:bg-slate-50"
                >
                  <span className="truncate font-mono text-[10px] text-slate-400">
                    {fact.field_path}
                  </span>
                  <span className="truncate text-xs text-slate-700">
                    {formatValue(fact.value)}
                  </span>
                  <span className="font-mono text-[10px] text-slate-400">
                    {fact.confidence.toFixed(2)}
                  </span>
                </button>
              ))}
              {activeDocument && activeDocument.facts.length === 0 && (
                <p className="px-2 py-4 text-sm text-slate-400">
                  Aucune information n’a été extraite de ces pages.
                </p>
              )}
            </div>
          </div>

          <div className="p-6">
            <h3 className="text-sm font-semibold">Votre décision</h3>
            <p className="mt-1 text-xs leading-5 text-slate-500">
              Expliquez brièvement votre décision afin de conserver une trace claire.
            </p>
            <textarea
              value={comment}
              onChange={(event) => setComment(event.target.value)}
              placeholder="Ajoutez votre commentaire ou la raison de la relance"
              rows={4}
              className="mt-3 w-full resize-y rounded-lg border border-slate-300 bg-white p-3 text-sm outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100"
            />
            {actionError && (
              <p className="mt-2 flex items-center gap-2 text-xs text-red-700">
                <AlertTriangle className="h-3.5 w-3.5" />
                {actionError}
              </p>
            )}
            <Separator className="my-4 bg-slate-200" />
            <div className="flex flex-wrap gap-2">
              {pendingReview && decision?.status === "READY" && (
                <Button
                  onClick={() => void submitReview("APPROVE")}
                  disabled={isSubmitting}
                  className="bg-blue-600 text-white hover:bg-blue-700"
                >
                  <Check className="h-4 w-4" />
                  Valider
                </Button>
              )}
              {pendingReview && decision?.status !== "READY" && (
                <Button
                  onClick={() => void submitReview("OVERRIDE")}
                  disabled={isSubmitting}
                  className="bg-amber-600 text-white hover:bg-amber-700"
                >
                  <ShieldAlert className="h-4 w-4" />
                  Valider avec réserve
                </Button>
              )}
              {pendingReview && (
                <Button
                  variant="outline"
                  onClick={() => void submitReview("REJECT")}
                  disabled={isSubmitting}
                  className="border-red-200 text-red-700 hover:bg-red-50"
                >
                  <X className="h-4 w-4" />
                  Rejeter
                </Button>
              )}
              <Button
                variant="outline"
                onClick={() => void submitReprocess()}
                disabled={isSubmitting || dossier.sources.length === 0}
                className="border-slate-300 text-slate-700 hover:bg-slate-50"
              >
                <RotateCcw className="h-4 w-4" />
                Relancer le traitement
              </Button>
            </div>

            {dossier.reviews.some((review) => review.status === "RESOLVED") && (
              <div className="mt-5 border-t border-slate-200 pt-4">
                <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Historique des décisions</p>
                {dossier.reviews
                  .filter((review) => review.status === "RESOLVED")
                  .map((review) => (
                    <div key={review.review_id} className="mt-3 text-xs">
                      <span className="font-mono text-slate-700">{review.resolution}</span>
                      <p className="mt-1 text-slate-500">{review.comment}</p>
                    </div>
                  ))}
              </div>
            )}
          </div>
        </section>
      </main>
    </div>
  );
}
