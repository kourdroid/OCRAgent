"use client";

import Link from "next/link";
import { ArrowRightIcon } from "@phosphor-icons/react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { SidebarTrigger } from "@/components/ui/sidebar";

type PageStat = {
  label: string;
  value: string;
  detail: string;
};

type PageSection = {
  title: string;
  description: string;
  tags?: string[];
};

type ModulePageProps = {
  eyebrow: string;
  title: string;
  description: string;
  status: string;
  stats: PageStat[];
  sections: PageSection[];
  actionHref?: string;
  actionLabel?: string;
};

export function ModulePage({
  eyebrow,
  title,
  description,
  status,
  stats,
  sections,
  actionHref = "/dashboard",
  actionLabel = "Open Command Center",
}: ModulePageProps) {
  return (
    <div className="min-h-screen w-full bg-zinc-950 text-zinc-100">
      <div className="pointer-events-none fixed inset-0">
        <div className="absolute -top-32 left-1/2 h-[520px] w-[820px] -translate-x-1/2 rounded-full bg-gradient-to-b from-zinc-800/20 to-transparent blur-3xl" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_1px_1px,rgba(255,255,255,0.05)_1px,transparent_0)] [background-size:22px_22px] opacity-60" />
      </div>

      <main className="relative mx-auto flex w-full max-w-6xl flex-col gap-6 px-6 py-8">
        <header className="flex flex-col gap-5">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-3">
              <SidebarTrigger className="-ml-2 text-zinc-400 hover:bg-zinc-900 hover:text-zinc-100" />
              <div className="flex flex-col gap-2">
                <Badge
                  variant="outline"
                  className="w-fit rounded-md border-zinc-800 bg-zinc-900/40 px-2 py-1 text-[11px] text-zinc-400"
                >
                  <span className="font-mono">{eyebrow}</span>
                </Badge>
                <div className="flex flex-col gap-2">
                  <h1 className="max-w-3xl text-2xl font-semibold tracking-tight text-zinc-100">
                    {title}
                  </h1>
                  <p className="max-w-3xl text-sm leading-6 text-zinc-500">
                    {description}
                  </p>
                </div>
              </div>
            </div>

            <Button
              render={<Link href={actionHref} />}
              className="hidden border border-emerald-500/20 bg-zinc-100 text-zinc-950 hover:bg-zinc-200 sm:inline-flex"
            >
              {actionLabel}
              <ArrowRightIcon className="h-4 w-4" />
            </Button>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            {stats.map((stat) => (
              <Card key={stat.label} className="bg-zinc-950/40 ring-1 ring-zinc-800/70">
                <CardHeader className="pb-0">
                  <CardTitle className="text-sm text-zinc-300">{stat.label}</CardTitle>
                </CardHeader>
                <CardContent className="flex flex-col gap-1">
                  <div className="font-mono text-2xl font-semibold tabular-nums text-zinc-100">
                    {stat.value}
                  </div>
                  <div className="text-xs leading-5 text-zinc-500">{stat.detail}</div>
                </CardContent>
              </Card>
            ))}
          </div>
        </header>

        <section className="rounded-xl border border-zinc-800 bg-zinc-950/40 ring-1 ring-zinc-800/40">
          <div className="flex flex-col gap-3 px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex flex-col gap-1">
              <h2 className="text-sm font-semibold tracking-tight text-zinc-100">
                Demo Scope
              </h2>
              <p className="text-xs leading-5 text-zinc-500">
                Focused view for the selected module. Use this page during client walkthroughs
                instead of presenting every capability at once.
              </p>
            </div>
            <Badge
              variant="outline"
              className="w-fit rounded-md border-emerald-900/60 bg-emerald-950/20 px-2 py-1 text-[11px] text-emerald-300"
            >
              <span className="font-mono">{status}</span>
            </Badge>
          </div>

          <Separator className="bg-zinc-800" />

          <div className="grid gap-0 md:grid-cols-2">
            {sections.map((section, index) => (
              <article
                key={section.title}
                className="flex min-h-44 flex-col gap-4 border-b border-zinc-800 p-4 last:border-b-0 md:border-r md:[&:nth-child(2n)]:border-r-0 md:[&:nth-last-child(-n+2)]:border-b-0"
              >
                <div className="flex items-center justify-between gap-3">
                  <h3 className="text-sm font-medium text-zinc-100">{section.title}</h3>
                  <span className="font-mono text-[11px] text-zinc-600">
                    0{index + 1}
                  </span>
                </div>
                <p className="text-xs leading-5 text-zinc-500">{section.description}</p>
                {section.tags && (
                  <div className="mt-auto flex flex-wrap gap-2">
                    {section.tags.map((tag) => (
                      <Badge
                        key={tag}
                        variant="outline"
                        className="rounded-md border-zinc-800 bg-zinc-900/30 px-2 py-1 text-[11px] text-zinc-300"
                      >
                        {tag}
                      </Badge>
                    ))}
                  </div>
                )}
              </article>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}
