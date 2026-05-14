"use client"

import * as React from "react"
import Link from "next/link"
import { 
  ArrowLeftIcon, 
  CpuIcon, 
  MagnifyingGlassPlus, 
  MagnifyingGlassMinus, 
  ArrowClockwise,
  WarningOctagon,
  ShieldWarning,
  Table as TableIcon,
  FileText,
  CalendarBlank,
  Buildings,
  CheckCircle,
  XCircle,
  ShieldCheck
} from "@phosphor-icons/react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { SidebarTrigger, useSidebar } from "@/components/ui/sidebar"

export default function DocumentAuditReportPage() {
  const { setOpen } = useSidebar()
  
  // Collapse sidebar on mount for studio immersion
  React.useEffect(() => {
    setOpen(false)
  }, [setOpen])

  return (
    <div className="flex h-screen w-full flex-col overflow-hidden bg-zinc-950 text-zinc-100">
      
      {/* Top Application Bar */}
      <header className="z-10 flex h-14 w-full flex-none items-center justify-between overflow-hidden border-b border-zinc-800 bg-zinc-950 px-4">
        <div className="flex items-center gap-4">
          <SidebarTrigger className="-ml-2 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100" />
          <Separator orientation="vertical" className="hidden h-4 bg-zinc-800 md:block" />
          <Link href="/" className="text-zinc-500 transition-colors hover:text-zinc-300">
            <ArrowLeftIcon className="h-5 w-5" />
          </Link>
          <Separator orientation="vertical" className="h-6 bg-zinc-800" />
          <div className="flex items-center gap-2">
            <CpuIcon className="h-5 w-5 text-emerald-500" />
            <h1 className="text-sm font-medium tracking-wide">AI VALIDATION STUDIO</h1>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Badge variant="outline" className="border-zinc-800 bg-zinc-900 font-mono font-normal text-zinc-400">
            Model: Claude-3.5-Sonnet
          </Badge>
          <Badge variant="outline" className="border-red-900/50 bg-red-950/30 text-red-500">
            <ShieldWarning className="mr-1 h-3.5 w-3.5" weight="fill" />
            DISCREPANCY DETECTED
          </Badge>
        </div>
      </header>

      {/* 50/50 Split View */}
      <main className="flex flex-1 overflow-hidden">
        
        {/* Left Side: Document Viewer */}
        <section className="relative flex w-1/2 flex-col border-r border-zinc-800 bg-zinc-950">
          {/* Viewer Toolbar */}
          <div className="flex h-12 flex-none items-center gap-1 border-b border-zinc-800/50 bg-zinc-900/30 px-4">
            <Button variant="ghost" size="icon" className="h-8 w-8 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100">
              <MagnifyingGlassPlus className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="icon" className="h-8 w-8 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100">
              <MagnifyingGlassMinus className="h-4 w-4" />
            </Button>
            <Separator orientation="vertical" className="mx-1 h-4 bg-zinc-800" />
            <Button variant="ghost" size="icon" className="h-8 w-8 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100">
              <ArrowClockwise className="h-4 w-4" />
            </Button>
          </div>

          {/* Document Canvas */}
          <div className="relative flex flex-1 items-center justify-center overflow-hidden bg-zinc-900/80 p-8 shadow-inner">
             {/* Mock Texture */}
             <div className="absolute inset-0 opacity-[0.02]" style={{ 
              backgroundImage: 'repeating-linear-gradient(45deg, #000 25%, transparent 25%, transparent 75%, #000 75%, #000), repeating-linear-gradient(45deg, #000 25%, #fff 25%, #fff 75%, #000 75%, #000)', 
              backgroundPosition: '0 0, 10px 10px', 
              backgroundSize: '20px 20px' 
            }} />
            
            {/* The PDF Document Page Simulation */}
            <div className="relative flex aspect-[1/1.4] w-full max-w-lg flex-col items-center justify-center border border-zinc-800 bg-zinc-950 shadow-2xl">
              <span className="font-mono text-sm text-zinc-600">PDF Document Renders Here</span>
              
              {/* Highlight Bounding Box (AI target) */}
              <div className="absolute left-[10%] top-[40%] h-[20%] w-[80%] animate-pulse border-2 border-blue-500 bg-blue-500/10 opacity-70 transition-opacity duration-1000" />
              <div className="absolute left-[10%] top-[37%] bg-blue-500 px-1.5 py-0.5 font-mono text-[10px] font-bold tracking-wider text-white">
                TABLE_EXTRACTION_TARGET
              </div>
            </div>
          </div>
        </section>

        {/* Right Side: AI Extraction & Math Engine */}
        <section className="flex w-1/2 flex-col bg-zinc-950">
          <ScrollArea className="flex-1">
            <div className="space-y-8 p-8">
              
              {/* Title Section */}
              <div>
                <h2 className="text-2xl font-semibold tracking-tight text-zinc-100">Document Audit Report</h2>
                <p className="mt-2 text-sm text-zinc-400">
                  Automated N-Way reconciliation completed. System detected variances requiring human intervention.
                </p>
              </div>

              {/* Extracted Metadata Card */}
              <Card className="border-zinc-800 bg-zinc-900/30">
                <CardHeader className="pb-3">
                  <CardTitle className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-zinc-500">
                    <FileText className="h-4 w-4" />
                    Extracted Metadata
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
                    <div className="flex flex-col gap-1">
                      <span className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wider text-zinc-500">
                        <Buildings className="h-3 w-3" /> Vendor
                      </span>
                      <span className="text-sm font-medium text-zinc-200">Diwana Transit</span>
                    </div>
                    <div className="flex flex-col gap-1">
                      <span className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wider text-zinc-500">
                        <FileText className="h-3 w-3" /> Doc Type
                      </span>
                      <span className="text-sm font-medium text-zinc-200">Déclaration d&apos;Importation</span>
                    </div>
                    <div className="flex flex-col gap-1">
                      <span className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wider text-zinc-500">
                        <CalendarBlank className="h-3 w-3" /> Date
                      </span>
                      <span className="font-mono text-sm text-zinc-200">2026-05-04</span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Reconciliation Engine Table */}
              <div className="space-y-3">
                <h3 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-zinc-500">
                  <TableIcon className="h-4 w-4" />
                  Reconciliation Engine (N-Way Match)
                </h3>
                <div className="overflow-hidden rounded-lg border border-zinc-800">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-zinc-800 bg-zinc-900/50">
                        <th className="h-10 px-4 text-left align-middle text-xs font-medium text-zinc-500">Validation Point</th>
                        <th className="h-10 px-4 text-left align-middle text-xs font-medium text-zinc-500">Expected</th>
                        <th className="h-10 px-4 text-left align-middle text-xs font-medium text-zinc-500">Actual (OCR)</th>
                        <th className="h-10 px-4 text-left align-middle text-xs font-medium text-zinc-500">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {/* Row 1: MATCH */}
                      <tr className="border-b border-zinc-800/50 bg-zinc-950 transition-colors hover:bg-zinc-900/50">
                        <td className="p-4 align-middle font-medium text-zinc-300">Exported Pallets (PO)</td>
                        <td className="p-4 align-middle font-mono text-zinc-400">400</td>
                        <td className="p-4 align-middle font-mono text-zinc-400">400</td>
                        <td className="p-4 align-middle">
                          <Badge variant="outline" className="border-emerald-900/50 bg-emerald-950/30 text-emerald-400">
                            <CheckCircle className="mr-1 h-3.5 w-3.5" weight="fill" /> MATCH
                          </Badge>
                        </td>
                      </tr>
                      {/* Row 2: MISMATCH */}
                      <tr className="border-b border-zinc-800/50 bg-zinc-950 transition-colors hover:bg-zinc-900/50">
                        <td className="p-4 align-middle font-medium text-zinc-300">Imported Pallets (BL)</td>
                        <td className="p-4 align-middle font-mono text-zinc-400">400</td>
                        <td className="p-4 align-middle font-mono text-zinc-100 bg-red-950/20">
                          <span className="border-b-2 border-red-500/50 pb-0.5">300</span>
                        </td>
                        <td className="p-4 align-middle">
                          <Badge variant="outline" className="border-red-900/50 bg-red-950/30 text-red-400">
                            <XCircle className="mr-1 h-3.5 w-3.5" weight="fill" /> MISMATCH
                          </Badge>
                        </td>
                      </tr>
                      {/* Row 3: ACCEPTED */}
                      <tr className="bg-zinc-950 transition-colors hover:bg-zinc-900/50">
                        <td className="p-4 align-middle font-medium text-zinc-300">Documented Scrap (PV)</td>
                        <td className="p-4 align-middle font-mono text-zinc-400">0</td>
                        <td className="p-4 align-middle font-mono text-zinc-400">50</td>
                        <td className="p-4 align-middle">
                          <Badge variant="outline" className="border-amber-900/50 bg-amber-950/30 text-amber-400">
                            <ShieldCheck className="mr-1 h-3.5 w-3.5" weight="fill" /> ACCEPTED
                          </Badge>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Variance Alert Card */}
              <Card className="border-red-900/50 bg-red-950/20 shadow-none ring-1 ring-inset ring-red-900/50">
                <CardContent className="flex items-start gap-4 p-5">
                  <WarningOctagon className="mt-0.5 h-6 w-6 shrink-0 text-red-500" weight="fill" />
                  <div className="flex flex-col gap-1">
                    <h4 className="text-sm font-semibold tracking-wide text-red-400 uppercase">Variance Alert</h4>
                    <p className="text-sm leading-relaxed text-red-200/90">
                      <strong>UNACCOUNTED INVENTORY: -50 Pallets.</strong> Potential Customs Liability: €12,500. Action Required.
                    </p>
                  </div>
                </CardContent>
              </Card>

            </div>
          </ScrollArea>

          {/* Sticky Bottom Action Bar */}
          <div className="flex flex-none items-center justify-between border-t border-zinc-800 bg-zinc-950/80 p-6 backdrop-blur-sm">
             <div className="font-mono text-xs text-zinc-500">
               Audit generated by Ironclad Engine.
             </div>
             <div className="flex items-center gap-3">
               <Button variant="ghost" className="h-10 text-zinc-400 hover:bg-zinc-900 hover:text-zinc-100">
                 Force Clear
               </Button>
               <Button className="h-10 gap-2 bg-red-600 font-medium text-white hover:bg-red-500">
                 <XCircle className="h-4 w-4" weight="bold" />
                 Reject Document
               </Button>
             </div>
          </div>
        </section>

      </main>
    </div>
  )
}
