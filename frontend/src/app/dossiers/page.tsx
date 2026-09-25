"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import {
  AlertTriangle,
  CheckCircle2,
  FileSearch,
  FolderOpen,
  LoaderCircle,
  Plus,
  RefreshCw,
  Upload,
  X,
  type LucideIcon,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { SidebarTrigger } from "@/components/ui/sidebar";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useDossiers } from "@/hooks/use-dossiers";
import { ingestDossier, listParties } from "@/lib/api";
import { DELASSUS_CLIENT_ID } from "@/lib/clients";
import type { DecisionStatus, DossierStatus } from "@/lib/types";
import type { SourceParty } from "@/lib/types";

const CASE_STATUS: Record<DossierStatus, { label: string; classes: string }> = {
  INGESTED: { label: "INGESTED", classes: "border-zinc-700 text-zinc-300" },
  PROCESSING: { label: "PROCESSING", classes: "border-sky-800 text-sky-300" },
  AWAITING_REVIEW: {
    label: "AWAITING REVIEW",
    classes: "border-amber-800 text-amber-300",
  },
  RESOLVED: { label: "RESOLVED", classes: "border-emerald-800 text-emerald-300" },
  FAILED: { label: "FAILED", classes: "border-red-800 text-red-300" },
};

const DECISION_STATUS: Record<DecisionStatus, string> = {
  READY: "text-emerald-300",
  BLOCKED: "text-red-300",
  REVIEW_REQUIRED: "text-amber-300",
};

type DossierFilter = "ALL" | "IN_FLIGHT" | DossierStatus;

const FILTERS: Array<{ value: DossierFilter; label: string }> = [
  { value: "ALL", label: "Tous les dossiers" },
  { value: "IN_FLIGHT", label: "En cours" },
  { value: "AWAITING_REVIEW", label: "À vérifier" },
  { value: "RESOLVED", label: "Terminés" },
  { value: "FAILED", label: "En erreur" },
];

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export default function DossiersPage() {
  const router = useRouter();
  const fileInput = React.useRef<HTMLInputElement>(null);
  const { dossiers, isLoading, error: loadError, refetch } = useDossiers(
    DELASSUS_CLIENT_ID,
  );
  const [files, setFiles] = React.useState<File[]>([]);
  const [externalReference, setExternalReference] = React.useState("");
  const [parties, setParties] = React.useState<SourceParty[]>([]);
  const [senderPartyId, setSenderPartyId] = React.useState("");
  const [issuerPartyIds, setIssuerPartyIds] = React.useState<Record<string, string>>({});
  const [isUploading, setIsUploading] = React.useState(false);
  const [uploadError, setUploadError] = React.useState<string | null>(null);
  const [filter, setFilter] = React.useState<DossierFilter>("ALL");

  React.useEffect(() => {
    void listParties(DELASSUS_CLIENT_ID).then(setParties).catch(() => setParties([]));
  }, []);

  const inFlight = dossiers.filter((item) =>
    ["INGESTED", "PROCESSING"].includes(item.status),
  ).length;
  const reviewQueue = dossiers.filter(
    (item) => item.status === "AWAITING_REVIEW",
  ).length;
  const resolved = dossiers.filter((item) => item.status === "RESOLVED").length;
  const stats: Array<{ label: string; value: number; icon: LucideIcon }> = [
    { label: "En cours", value: inFlight, icon: LoaderCircle },
    { label: "À vérifier", value: reviewQueue, icon: FileSearch },
    { label: "Terminés", value: resolved, icon: CheckCircle2 },
  ];
  const filteredDossiers = dossiers.filter((dossier) => {
    if (filter === "ALL") return true;
    if (filter === "IN_FLIGHT") {
      return dossier.status === "INGESTED" || dossier.status === "PROCESSING";
    }
    return dossier.status === filter;
  });

  function addFiles(selected: FileList | null) {
    if (!selected) return;
    setFiles((current) => {
      const known = new Set(current.map((file) => `${file.name}:${file.size}`));
      return [
        ...current,
        ...Array.from(selected).filter(
          (file) => !known.has(`${file.name}:${file.size}`),
        ),
      ];
    });
  }

  async function submitDossier() {
    if (!files.length) return;
    setIsUploading(true);
    setUploadError(null);
    try {
      const result = await ingestDossier(
        files,
        DELASSUS_CLIENT_ID,
        externalReference,
        { senderPartyId: senderPartyId || undefined, issuerPartyIds },
      );
      setFiles([]);
      setExternalReference("");
      setSenderPartyId("");
      setIssuerPartyIds({});
      await refetch();
      router.push(`/dossiers/${result.case_id}`);
    } catch (cause) {
      setUploadError(cause instanceof Error ? cause.message : "Upload failed");
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex min-h-16 max-w-7xl items-center justify-between gap-4 px-5 py-3">
          <div className="flex min-w-0 items-center gap-3">
            <SidebarTrigger className="text-zinc-400 hover:bg-zinc-900 hover:text-zinc-100" />
            <div className="min-w-0">
              <h1 className="truncate text-xl font-semibold">Dossiers</h1>
              <p className="truncate text-xs text-slate-500">
                Gérez les documents importés et les décisions à prendre.
              </p>
            </div>
          </div>
          <Button
            variant="outline"
            size="icon"
            title="Actualiser les dossiers"
            onClick={() => void refetch()}
            className="border-slate-200 bg-white text-slate-500 hover:bg-slate-50"
          >
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </header>

      <main className="mx-auto w-full max-w-7xl px-5 py-6">
        <section className="grid overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm sm:grid-cols-3">
          {stats.map(({ label, value, icon: Icon }, index) => (
            <div
              key={label}
              className={`flex items-center justify-between px-4 py-4 ${
                index < 2 ? "border-b border-slate-200 sm:border-b-0 sm:border-r" : ""
              }`}
            >
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
                <p className="mt-1 font-mono text-2xl">{value}</p>
              </div>
              <Icon className="h-5 w-5 text-blue-600" />
            </div>
          ))}
        </section>

        <section className="mt-6 grid gap-6 rounded-xl border border-slate-200 bg-white p-5 shadow-sm lg:grid-cols-[1fr_340px]">
          <div>
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h2 className="text-base font-semibold">Nouveau dossier</h2>
                <p className="mt-1 text-xs text-slate-500">
                  Étape 1 sur 3 — ajoutez les PDF d’un même envoi.
                </p>
              </div>
              <Badge variant="outline" className="border-blue-200 bg-blue-50 text-blue-700">
                DELASSUS
              </Badge>
            </div>

            <button
              type="button"
              onClick={() => fileInput.current?.click()}
              onDragOver={(event) => event.preventDefault()}
              onDrop={(event) => {
                event.preventDefault();
                addFiles(event.dataTransfer.files);
              }}
              className="flex min-h-44 w-full flex-col items-center justify-center rounded-xl border border-dashed border-blue-200 bg-blue-50/40 px-5 text-center transition-colors hover:border-blue-400 hover:bg-blue-50"
            >
              <Upload className="mb-3 h-6 w-6 text-blue-600" />
              <span className="text-sm font-semibold">Ajouter les documents</span>
              <span className="mt-1 text-xs text-slate-500">
                Glissez les PDF ici ou cliquez pour les sélectionner.
              </span>
            </button>
            <input
              ref={fileInput}
              type="file"
              accept=".pdf,application/pdf"
              multiple
              className="sr-only"
              onChange={(event) => addFiles(event.target.files)}
            />

            {uploadError && (
              <div className="mt-3 flex gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-700">
                <AlertTriangle className="h-4 w-4 shrink-0" />
                {uploadError}
              </div>
            )}
          </div>

          <div className="border-l-0 border-slate-200 lg:border-l lg:pl-6">
            <label className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Référence de l’envoi
            </label>
            <Input
              value={externalReference}
              onChange={(event) => setExternalReference(event.target.value)}
              placeholder="Ex. numéro d’envoi ou référence fournisseur"
              className="mt-2 border-slate-300 bg-white"
            />
            <label className="mt-4 block text-xs font-medium uppercase tracking-wide text-slate-500">Expéditeur</label>
            <select value={senderPartyId} onChange={(event) => setSenderPartyId(event.target.value)} className="mt-2 h-9 w-full rounded-md border border-slate-300 bg-white px-2 text-xs">
              <option value="">Expéditeur inconnu (vérification requise)</option>
              {parties.map((party) => <option key={party.party_id} value={party.party_id}>{party.name} / {party.party_type}</option>)}
            </select>
            <Separator className="my-4 bg-slate-200" />
            <div className="max-h-44 space-y-2 overflow-y-auto">
              {files.length === 0 && (
                <p className="text-xs text-slate-400">Aucun document sélectionné.</p>
              )}
              {files.map((file) => (
                <div
                  key={`${file.name}:${file.size}`}
                  className="grid grid-cols-[auto_1fr_auto] items-center gap-2 rounded-lg border border-slate-200 px-3 py-2"
                >
                  <FolderOpen className="h-4 w-4 shrink-0 text-blue-600" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-xs text-slate-700">{file.name}</p>
                    <p className="font-mono text-[10px] text-slate-400">
                      {(file.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                  <select value={issuerPartyIds[file.name] ?? ""} onChange={(event) => setIssuerPartyIds((current) => ({ ...current, [file.name]: event.target.value }))} className="h-7 max-w-36 rounded border border-slate-300 bg-white px-1 text-[10px]">
                    <option value="">Émetteur inconnu</option>
                    {parties.map((party) => <option key={party.party_id} value={party.party_id}>{party.name}</option>)}
                  </select>
                  <Button
                    variant="ghost"
                    size="icon"
                    title={`Retirer ${file.name}`}
                    onClick={() =>
                      setFiles((current) => current.filter((item) => item !== file))
                    }
                    className="h-7 w-7 text-slate-400 hover:text-slate-900"
                  >
                    <X className="h-3.5 w-3.5" />
                  </Button>
                </div>
              ))}
            </div>
            <Button
              onClick={() => void submitDossier()}
              disabled={!files.length || isUploading}
              className="mt-4 w-full bg-blue-600 text-white hover:bg-blue-700"
            >
              {isUploading ? (
                <LoaderCircle className="h-4 w-4 animate-spin" />
              ) : (
                <Plus className="h-4 w-4" />
              )}
              Créer le dossier
            </Button>
          </div>
        </section>

        <section className="pt-6">
          <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
            <h2 className="text-base font-semibold">Suivi des dossiers</h2>
            <label className="flex items-center gap-2 text-xs text-slate-500">
              Afficher
              <select
                value={filter}
                onChange={(event) => setFilter(event.target.value as DossierFilter)}
                className="h-8 rounded-md border border-slate-300 bg-white px-2 text-xs text-slate-700 outline-none focus:border-blue-600"
              >
                {FILTERS.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <p className="mb-3 text-xs text-slate-500">
            Ouvrez un dossier pour vérifier les informations et prendre une décision.
          </p>

          {isLoading && (
            <div className="flex items-center justify-center border-y border-zinc-800 py-14 text-sm text-zinc-500">
              <LoaderCircle className="mr-2 h-4 w-4 animate-spin" />
              Loading dossiers
            </div>
          )}
          {!isLoading && loadError && (
            <div className="border border-red-900 bg-red-950/20 p-4 text-sm text-red-300">
              {loadError}
            </div>
          )}
          {!isLoading && !loadError && filteredDossiers.length === 0 && (
            <div className="border-y border-zinc-800 py-14 text-center text-sm text-zinc-500">
              No dossiers match this filter.
            </div>
          )}
          {!isLoading && !loadError && filteredDossiers.length > 0 && (
            <div className="overflow-x-auto border border-zinc-800">
              <Table>
                <TableHeader>
                  <TableRow className="border-zinc-800 hover:bg-transparent">
                    {["Case", "Reference", "Files", "Decision", "Lifecycle", "Created"].map(
                      (label) => (
                        <TableHead
                          key={label}
                          className="bg-zinc-900/50 text-xs uppercase text-zinc-500"
                        >
                          {label}
                        </TableHead>
                      ),
                    )}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredDossiers.map((dossier) => (
                    <TableRow
                      key={dossier.case_id}
                      onClick={() => router.push(`/dossiers/${dossier.case_id}`)}
                      className="cursor-pointer border-zinc-800 hover:bg-zinc-900/50"
                    >
                      <TableCell className="font-mono text-xs text-zinc-300">
                        {dossier.case_id.slice(0, 8).toUpperCase()}
                      </TableCell>
                      <TableCell>{dossier.external_reference ?? "-"}</TableCell>
                      <TableCell className="font-mono">{dossier.source_count}</TableCell>
                      <TableCell>
                        {dossier.decision_status ? (
                          <span
                            className={`font-mono text-xs ${DECISION_STATUS[dossier.decision_status]}`}
                          >
                            {dossier.decision_status}
                          </span>
                        ) : (
                          <span className="text-xs text-zinc-600">PENDING</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant="outline"
                          className={`rounded-sm ${CASE_STATUS[dossier.status].classes}`}
                        >
                          {CASE_STATUS[dossier.status].label}
                        </Badge>
                      </TableCell>
                      <TableCell className="whitespace-nowrap text-xs text-zinc-500">
                        {formatDate(dossier.created_at)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
