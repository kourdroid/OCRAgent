import { ModulePage } from "@/components/module-page";

export default function SourceSystemsPage() {
  return (
    <ModulePage
      eyebrow="SOURCE SYSTEMS"
      title="Explicit source-of-truth connections for each client"
      description="The core should not care whether truth comes from Postgres, Odoo, SAP, Excel, cached webhooks, folders, or client-hosted systems. That belongs behind adapters and client configuration."
      status="POSTGRES FIRST, ADAPTERS NEXT"
      stats={[
        {
          label: "Current Source",
          value: "Postgres",
          detail: "The demo reads ERP purchase orders and goods receipts from existing tables.",
        },
        {
          label: "Boundary",
          value: "Adapter",
          detail: "Every future source should implement the same fetch contract.",
        },
        {
          label: "Client Control",
          value: "Config",
          detail: "Source selection is wiring, not hardcoded matching behavior.",
        },
      ]}
      sections={[
        {
          title: "ERP Database",
          description:
            "The first milestone uses direct database access for purchase order and goods receipt evidence.",
          tags: ["Postgres ERP", "PO lines", "Goods receipts"],
        },
        {
          title: "External ERP APIs",
          description:
            "Odoo, SAP, and similar systems should plug in through source adapters without changing plugin logic.",
          tags: ["Odoo", "SAP", "REST APIs"],
        },
        {
          title: "File-Based Sources",
          description:
            "Some clients will provide Excel files, folders, or email attachments as operational truth sources.",
          tags: ["Excel", "Folders", "Email"],
        },
        {
          title: "Client-Hosted Data",
          description:
            "Sensitive deployments may require local storage, client servers, private networks, or webhook caches.",
          tags: ["On-prem", "Webhook cache", "Local storage"],
        },
      ]}
    />
  );
}
