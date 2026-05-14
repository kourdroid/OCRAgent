import { ModulePage } from "@/components/module-page";

export default function HumanReviewPage() {
  return (
    <ModulePage
      eyebrow="HUMAN REVIEW"
      title="Operator review only when policy requires it"
      description="The system should be headless by default but still expose review screens when a client needs approvals, new layout confirmation, discrepancy checks, or blocked delivery handling."
      status="PLUGIN-ROUTED REVIEW"
      stats={[
        {
          label: "Review Trigger",
          value: "Policy",
          detail: "The plugin decides when requires_human is true.",
        },
        {
          label: "Core Role",
          value: "Route",
          detail: "The core persists the result and sends work to the correct channel.",
        },
        {
          label: "Client UX",
          value: "Optional",
          detail: "Some clients may use dashboard review; others may only receive notifications.",
        },
      ]}
      sections={[
        {
          title: "Schema Approval",
          description:
            "New vendors or layouts can pause for human confirmation before extraction is trusted downstream.",
          tags: ["New layout", "Field mapping", "Approval"],
        },
        {
          title: "Discrepancy Review",
          description:
            "Material mismatches between invoice, PO, and receipt should be visible with evidence and explanations.",
          tags: ["Price variance", "Quantity mismatch", "Evidence"],
        },
        {
          title: "Blocked Delivery",
          description:
            "Documents that cannot be auto-cleared should stop before webhook, email, or ERP delivery.",
          tags: ["Audit block", "No silent delivery", "Traceability"],
        },
        {
          title: "Notification-Only Clients",
          description:
            "A client may skip the dashboard and receive review links, WhatsApp alerts, or email summaries.",
          tags: ["Email", "WhatsApp", "Review link"],
        },
      ]}
    />
  );
}
