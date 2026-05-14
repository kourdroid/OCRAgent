import { ModulePage } from "@/components/module-page";

export default function ThreeWayMatchingPage() {
  return (
    <ModulePage
      eyebrow="3-WAY MATCHING"
      title="Invoice, purchase order, and goods receipt reconciliation"
      description="This is the core demo path: extract the vendor claim, compare it against ERP truth, explain discrepancies, and decide whether the document can continue automatically."
      status="PRODUCTION V1 PRIORITY"
      stats={[
        {
          label: "Decision Owner",
          value: "Plugin",
          detail: "The matching plugin owns domain policy and human-review decisions.",
        },
        {
          label: "Truth Sources",
          value: "PO + GR",
          detail: "Current milestone uses existing ERP Postgres purchase orders and receipts.",
        },
        {
          label: "Audit Output",
          value: "Persisted",
          detail: "Discrepancies and requires_human are stored in the audit report.",
        },
      ]}
      sections={[
        {
          title: "Invoice Claim",
          description:
            "The extracted invoice provides vendor, item, quantity, unit price, and total amount. It is evidence, not the source of truth.",
          tags: ["PDF extraction", "Schema-backed JSON", "Vendor layout"],
        },
        {
          title: "Purchase Order",
          description:
            "The PO defines the approved commercial truth: what was authorized, expected pricing, and allowed variance.",
          tags: ["ERP adapter", "PO lines", "Expected price"],
        },
        {
          title: "Goods Receipt",
          description:
            "Warehouse receipt data confirms what was actually received, including shortages or partial deliveries.",
          tags: ["Received quantity", "Shortage detection", "Warehouse evidence"],
        },
        {
          title: "Decision",
          description:
            "The plugin returns a normalized result with discrepancies, confidence, evidence, and whether a human must review the case.",
          tags: ["requires_human", "Audit trail", "Auto-clear or block"],
        },
      ]}
    />
  );
}
