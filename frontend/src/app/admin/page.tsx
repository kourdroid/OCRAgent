"use client";

import * as React from "react";
import { CheckCircle2, Plus, RefreshCw, SlidersHorizontal, UsersRound } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { activateRuleSet, createParty, createRuleSet, listParties, listRuleSets } from "@/lib/api";
import { DELASSUS_CLIENT_ID } from "@/lib/clients";
import type { RuleSet, SourceParty } from "@/lib/types";

const TEMPLATE_OPTIONS = ["EXACT_MATCH", "FIELD_REQUIRED", "REQUIRED_DOCUMENT"] as const;

export default function AdminPage() {
  const [parties, setParties] = React.useState<SourceParty[]>([]);
  const [ruleSets, setRuleSets] = React.useState<RuleSet[]>([]);
  const [partyName, setPartyName] = React.useState("");
  const [partyScope, setPartyScope] = React.useState<"INTERNAL" | "EXTERNAL">("EXTERNAL");
  const [partyType, setPartyType] = React.useState("SUPPLIER");
  const [ruleSetName, setRuleSetName] = React.useState("");
  const [ruleName, setRuleName] = React.useState("");
  const [fieldPath, setFieldPath] = React.useState("declaration_number");
  const [templateType, setTemplateType] = React.useState<(typeof TEMPLATE_OPTIONS)[number]>("EXACT_MATCH");
  const [confirmation, setConfirmation] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(true);

  const load = React.useCallback(async () => {
    setLoading(true);
    try {
      const [partyResult, ruleResult] = await Promise.all([
        listParties(DELASSUS_CLIENT_ID, false),
        listRuleSets(DELASSUS_CLIENT_ID),
      ]);
      setParties(partyResult);
      setRuleSets(ruleResult);
      setError(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Administration data could not be loaded");
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  async function addParty() {
    if (!partyName.trim()) return;
    try {
      await createParty(DELASSUS_CLIENT_ID, {
        name: partyName.trim(), scope: partyScope, party_type: partyType, is_active: true,
      });
      setPartyName("");
      await load();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not create party"); }
  }

  async function addRuleSet() {
    if (!ruleSetName.trim() || !ruleName.trim()) return;
    try {
      await createRuleSet(DELASSUS_CLIENT_ID, {
        name: ruleSetName.trim(),
        rules: [{ name: ruleName.trim(), template_type: templateType, field_path: fieldPath.trim() || undefined, severity: "warning", failure_outcome: "REVIEW_REQUIRED" }],
      });
      setRuleSetName("");
      setRuleName("");
      await load();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not create ruleset"); }
  }

  async function activate(rulesetId: string) {
    if (confirmation.trim().length < 8) {
      setError("Enter a confirmation comment of at least eight characters before activation.");
      return;
    }
    try {
      await activateRuleSet(rulesetId, DELASSUS_CLIENT_ID, confirmation.trim());
      setConfirmation("");
      await load();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not activate ruleset"); }
  }

  const partyTypes = partyScope === "INTERNAL"
    ? ["DIRECTION", "FINANCE", "COMMERCIAL", "OTHER"]
    : ["INSTITUTION", "SERVICE_PROVIDER", "CLIENT", "SUPPLIER", "OTHER"];

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <header className="border-b border-zinc-800"><div className="flex min-h-16 items-center justify-between px-5"><div className="flex items-center gap-3"><SidebarTrigger className="text-zinc-400" /><div><h1 className="text-lg font-semibold">Pilot administration</h1><p className="text-xs text-zinc-500">Delassus parties and confirmed workflow rules</p></div></div><Button variant="outline" size="icon" title="Refresh administration data" onClick={() => void load()} className="border-zinc-800"><RefreshCw className="h-4 w-4" /></Button></div></header>
      <main className="mx-auto grid w-full max-w-7xl gap-8 px-5 py-6 lg:grid-cols-2">
        <section><div className="flex items-center gap-2"><UsersRound className="h-4 w-4 text-emerald-400" /><h2 className="text-sm font-semibold">Document parties</h2></div><p className="mt-1 text-xs text-zinc-500">The sender delivers the file. The issuer created the document.</p>
          <div className="mt-4 grid gap-3 border border-zinc-800 p-4 sm:grid-cols-2"><Input value={partyName} onChange={(event) => setPartyName(event.target.value)} placeholder="Organization name" className="border-zinc-800 bg-zinc-950 sm:col-span-2" /><select value={partyScope} onChange={(event) => { const scope = event.target.value as "INTERNAL" | "EXTERNAL"; setPartyScope(scope); setPartyType(scope === "INTERNAL" ? "DIRECTION" : "SUPPLIER"); }} className="h-8 border border-zinc-800 bg-zinc-950 px-2 text-xs"><option value="EXTERNAL">External</option><option value="INTERNAL">Internal</option></select><select value={partyType} onChange={(event) => setPartyType(event.target.value)} className="h-8 border border-zinc-800 bg-zinc-950 px-2 text-xs">{partyTypes.map((value) => <option key={value}>{value}</option>)}</select><Button onClick={() => void addParty()} className="bg-emerald-600 text-white hover:bg-emerald-500 sm:col-span-2"><Plus className="h-4 w-4" />Add party</Button></div>
          <div className="mt-4 divide-y divide-zinc-800 border-y border-zinc-800">{parties.map((party) => <div key={party.party_id} className="flex items-center justify-between py-3 text-sm"><span>{party.name}</span><span className="font-mono text-[10px] text-zinc-500">{party.scope} / {party.party_type}</span></div>)}{!loading && parties.length === 0 && <p className="py-4 text-sm text-zinc-600">No parties configured.</p>}</div>
        </section>
        <section><div className="flex items-center gap-2"><SlidersHorizontal className="h-4 w-4 text-emerald-400" /><h2 className="text-sm font-semibold">Rulesets</h2></div><p className="mt-1 text-xs text-zinc-500">Drafts do not decide dossiers. Activation creates the one confirmed version used by the worker.</p>
          <div className="mt-4 grid gap-3 border border-zinc-800 p-4"><Input value={ruleSetName} onChange={(event) => setRuleSetName(event.target.value)} placeholder="Ruleset name" className="border-zinc-800 bg-zinc-950" /><Input value={ruleName} onChange={(event) => setRuleName(event.target.value)} placeholder="First rule name" className="border-zinc-800 bg-zinc-950" /><select value={templateType} onChange={(event) => setTemplateType(event.target.value as (typeof TEMPLATE_OPTIONS)[number])} className="h-8 border border-zinc-800 bg-zinc-950 px-2 text-xs">{TEMPLATE_OPTIONS.map((value) => <option key={value}>{value}</option>)}</select><Input value={fieldPath} onChange={(event) => setFieldPath(event.target.value)} placeholder="Field path" className="border-zinc-800 bg-zinc-950" /><Button onClick={() => void addRuleSet()} className="bg-emerald-600 text-white hover:bg-emerald-500"><Plus className="h-4 w-4" />Create draft</Button></div>
          <Input value={confirmation} onChange={(event) => setConfirmation(event.target.value)} placeholder="Confirmation comment required for activation" className="mt-4 border-zinc-800 bg-zinc-950" />
          <div className="mt-4 space-y-3">{ruleSets.map((ruleSet) => <div key={ruleSet.ruleset_id} className="border border-zinc-800 p-4"><div className="flex items-start justify-between gap-3"><div><p className="text-sm font-medium">{ruleSet.name}</p><p className="mt-1 font-mono text-[10px] text-zinc-500">V{ruleSet.version} / {ruleSet.status}</p></div>{ruleSet.status === "DRAFT" && <Button size="sm" variant="outline" onClick={() => void activate(ruleSet.ruleset_id)} className="border-emerald-800 text-emerald-300"><CheckCircle2 className="h-3.5 w-3.5" />Activate</Button>}</div><p className="mt-3 text-xs text-zinc-500">{ruleSet.rules.length} tested rule template{ruleSet.rules.length === 1 ? "" : "s"}</p></div>)}</div>
        </section>
        {error && <p className="border border-red-900 bg-red-950/20 px-4 py-3 text-sm text-red-300 lg:col-span-2">{error}</p>}
      </main>
    </div>
  );
}
