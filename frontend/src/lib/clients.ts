import type { ClientConfig } from "./types";

export const DEFAULT_CLIENT_ID = "default";
export const DELASSUS_CLIENT_ID = "delassus";

export const CLIENT_CONFIGS: ClientConfig[] = [
  {
    clientId: DEFAULT_CLIENT_ID,
    displayName: "Default Demo",
    enabledModules: ["ocr", "schema_review", "reconciliation"],
    defaultRoute: "/dashboard",
    reviewMode: "schema_approval",
    workflowId: "invoice_3way",
    providerProfile: "cloud_default",
    rulesetVersion: "1",
  },
  {
    clientId: "supply_chain",
    displayName: "Supply Chain",
    enabledModules: ["ocr", "schema_review", "reconciliation"],
    defaultRoute: "/dashboard",
    reviewMode: "schema_approval",
    workflowId: "invoice_3way",
    providerProfile: "cloud_default",
    rulesetVersion: "1",
  },
  {
    clientId: DELASSUS_CLIENT_ID,
    displayName: "Delassus",
    enabledModules: ["dossiers", "evidence_review", "reports"],
    defaultRoute: "/dossiers",
    reviewMode: "audit_review",
    workflowId: "morocco_import_dossier",
    providerProfile: "paddle_local",
    rulesetVersion: "1",
  },
];

export function getClientConfig(clientId: string): ClientConfig {
  return CLIENT_CONFIGS.find((client) => client.clientId === clientId) ?? CLIENT_CONFIGS[0];
}
