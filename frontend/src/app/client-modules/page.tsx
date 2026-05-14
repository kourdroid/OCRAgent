import { ModulePage } from "@/components/module-page";

export default function ClientModulesPage() {
  return (
    <ModulePage
      eyebrow="CLIENT MODULES"
      title="Packaged IDP modules selected per client"
      description="The product should be sold as a modular IDP pack: intake, extraction, validation, matching, review, notifications, and delivery can be enabled based on each client workflow."
      status="MODULED, NOT HARDWIRED"
      stats={[
        {
          label: "Core Product",
          value: "IDP",
          detail: "The product value is the decision pipeline, not OCR alone.",
        },
        {
          label: "Client Logic",
          value: "Plugin",
          detail: "Custom matching and validation policies live behind plugin contracts.",
        },
        {
          label: "Interfaces",
          value: "Channels",
          detail: "Dashboard, email, WhatsApp, APIs, and folders are optional adapters.",
        },
      ]}
      sections={[
        {
          title: "Invoice Automation",
          description:
            "Ingest invoices from upload, email, or folders; extract structured data; validate and route the result.",
          tags: ["Invoices", "Email intake", "Structured output"],
        },
        {
          title: "Supply Chain Matching",
          description:
            "Compare invoice claims against purchase orders and receipts with client-specific tolerance rules.",
          tags: ["3-way match", "PO", "Goods receipt"],
        },
        {
          title: "Document Routing",
          description:
            "Send approved or blocked outputs to the channel each client actually uses.",
          tags: ["Webhook", "SMTP", "WhatsApp"],
        },
        {
          title: "Private Workflow Pack",
          description:
            "For sensitive clients, configure local storage, private models, and client-hosted execution.",
          tags: ["On-prem", "Private model", "Client VPC"],
        },
      ]}
    />
  );
}
