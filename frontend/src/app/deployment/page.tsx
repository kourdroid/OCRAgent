import { ModulePage } from "@/components/module-page";

export default function DeploymentPage() {
  return (
    <ModulePage
      eyebrow="DEPLOYMENT PROFILES"
      title="Deployment choices for sensitive and regulated clients"
      description="The architecture must support shared cloud for speed, single-tenant setups for control, and private deployments when data cannot leave the client environment."
      status="PRIVACY-PROFILED"
      stats={[
        {
          label: "Default Demo",
          value: "Cloud",
          detail: "The current demo path runs as a shared cloud workflow.",
        },
        {
          label: "Sensitive Data",
          value: "Private",
          detail: "Local storage and private model providers must be selectable per client.",
        },
        {
          label: "Model Policy",
          value: "Benchmarked",
          detail: "Local model quality must be tested per client instead of promised generically.",
        },
      ]}
      sections={[
        {
          title: "Shared Cloud",
          description:
            "Fastest deployment profile for demos, pilots, and clients with acceptable cloud processing policies.",
          tags: ["Fast setup", "Managed APIs", "Shared ops"],
        },
        {
          title: "Single-Tenant Cloud",
          description:
            "Dedicated infrastructure for clients that need isolation but still accept managed cloud operations.",
          tags: ["Dedicated runtime", "Isolated data", "Client controls"],
        },
        {
          title: "Client-Hosted",
          description:
            "Run storage, source adapters, and processing inside the client network when integration or privacy requires it.",
          tags: ["Client VPC", "Private database", "Internal APIs"],
        },
        {
          title: "Local-Only",
          description:
            "Use local storage and private model providers for sensitive workflows, with quality measured before commitment.",
          tags: ["No external API", "Local model", "Benchmark required"],
        },
      ]}
    />
  );
}
