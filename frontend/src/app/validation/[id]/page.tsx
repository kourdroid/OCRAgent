"use client"

import * as React from "react"
import { use } from "react"
import Link from "next/link"
import { ArrowLeftIcon, FilePdfIcon, CheckCircleIcon, CpuIcon, CaretDownIcon, ListDashesIcon } from "@phosphor-icons/react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { SidebarTrigger, useSidebar } from "@/components/ui/sidebar"

const mockSchemaFields = [
  { key: "vendorName", label: "Vendor Name", value: "Label Tech S.A.R.L", confidence: 99, type: "string" },
  { key: "invoiceNumber", label: "Invoice Number", value: "FA2109-0333", confidence: 98, type: "string" },
  { key: "invoiceDate", label: "Invoice Date", value: "2021-09-17", confidence: 99, type: "date" },
  { key: "taxId", label: "Tax Identifier (ICE)", value: "001552366000088", confidence: 85, type: "string" },
  { key: "subTotal", label: "Subtotal Amount", value: "800.18", confidence: 96, type: "number" },
  { key: "taxAmount", label: "Tax (VAT 20%)", value: "160.04", confidence: 95, type: "number" },
  { key: "totalAmount", label: "Total Amount", value: "960.22", confidence: 97, type: "number" },
]

export default function ValidationStudioPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const vendorName = id.replace(/-/g, ' ').toUpperCase()
  const { setOpen } = useSidebar()
  
  // Collapse sidebar on mount for studio immersion
  React.useEffect(() => {
    setOpen(false)
  }, [setOpen])

  return (
    <div className="h-screen w-full bg-zinc-950 text-zinc-100 flex flex-col overflow-hidden">
      
      {/* Top Application Bar */}
      <header className="flex-none h-14 border-b border-zinc-800 bg-zinc-950 px-4 flex items-center justify-between z-10 w-full overflow-hidden">
        <div className="flex items-center gap-4">
          <SidebarTrigger className="-ml-2 hover:bg-zinc-800 text-zinc-400 hover:text-zinc-100" />
          <Separator orientation="vertical" className="h-4 bg-zinc-800 hidden md:block" />
          <Link href="/" className="text-zinc-500 hover:text-zinc-300 transition-colors">
            <ArrowLeftIcon className="h-5 w-5" />
          </Link>
          <Separator orientation="vertical" className="h-6 bg-zinc-800" />
          <div className="flex items-center gap-2">
            <CpuIcon className="h-5 w-5 text-emerald-500" />
            <h1 className="text-sm font-medium tracking-wide">AI VALIDATION STUDIO</h1>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Badge variant="outline" className="bg-zinc-900 border-zinc-800 text-zinc-400 font-mono font-normal">
            Model: Claude-3.5-Sonnet
          </Badge>
          <Badge variant="outline" className="bg-amber-950/30 text-amber-500 border-amber-900/50">
            Awaiting Human Verification
          </Badge>
        </div>
      </header>

      {/* 50/50 Split View */}
      <main className="flex-1 flex overflow-hidden">
        
        {/* Left Side: Mock Document/PDF Viewer */}
        <section className="w-1/2 border-r border-zinc-800 bg-zinc-900/50 p-6 flex flex-col relative">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xs font-semibold text-zinc-500 uppercase tracking-widest flex items-center gap-2">
              <FilePdfIcon className="h-4 w-4" />
              Source Document
            </h2>
            <div className="text-xs font-mono text-zinc-600">Scan_FA2109-0333.pdf</div>
          </div>
          
          <div className="flex-1 border border-zinc-800 bg-zinc-950 rounded-lg flex items-center justify-center relative overflow-hidden shadow-inner">
            {/* Mock watermark/texture */}
            <div className="absolute inset-0 opacity-[0.02]" style={{ 
              backgroundImage: 'repeating-linear-gradient(45deg, #000 25%, transparent 25%, transparent 75%, #000 75%, #000), repeating-linear-gradient(45deg, #000 25%, #fff 25%, #fff 75%, #000 75%, #000)', 
              backgroundPosition: '0 0, 10px 10px', 
              backgroundSize: '20px 20px' 
            }} />
            
            <div className="text-center z-10 flex flex-col items-center">
              <FilePdfIcon className="h-16 w-16 text-zinc-800 mb-4" weight="light" />
              <p className="text-zinc-600 font-mono text-sm max-w-sm px-6">
                PDF rasterization disabled for UI prototype. Imagine a heavily degraded, ink-stained invoice from {vendorName} sitting right here.
              </p>
            </div>
          </div>
        </section>

        {/* Right Side: AI Schema Generation */}
        <section className="w-1/2 bg-zinc-950 flex flex-col">
          <div className="flex-none p-6 pb-2">
            <h2 className="text-xs font-semibold text-emerald-500 uppercase tracking-widest flex items-center gap-2">
              <CheckCircleIcon className="h-4 w-4" />
              Extracted Payload Map
            </h2>
            <p className="text-xs text-zinc-500 mt-2">
              The AI engine has dynamically mapped this unseen vendor layout to our Ironclad standard registry model. Please review low-confidence extractions.
            </p>
          </div>

          <ScrollArea className="flex-1 px-6">
            <div className="py-4 space-y-6">
              
              {/* Iteration over flat fields */}
              <div className="space-y-4">
                <h3 className="text-sm font-medium text-zinc-300 border-b border-zinc-800 pb-2">Header Attributes</h3>
                <div className="grid gap-4">
                  {mockSchemaFields.map((field) => (
                    <div key={field.key} className="flex gap-4 items-start group">
                      <div className="w-1/3 pt-2.5">
                        <label className="text-xs font-mono text-zinc-400 block truncate" title={field.key}>
                          {field.key}
                        </label>
                      </div>
                      <div className="w-2/3 relative">
                        <Input 
                          defaultValue={field.value}
                          className="bg-zinc-900 border-zinc-800 focus-visible:ring-emerald-500 font-mono text-sm"
                        />
                        <div className="absolute right-3 top-2.5 flex items-center">
                          {/* Confidence indicator */}
                          <div className={`text-[10px] px-1.5 py-0.5 rounded font-mono ${
                            field.confidence > 98 ? 'bg-emerald-950/50 text-emerald-400 border border-emerald-900/50' : 
                            field.confidence > 90 ? 'bg-zinc-800 text-zinc-300 border border-zinc-700' :
                            'bg-amber-950/50 text-amber-400 border border-amber-900/50'
                          }`}>
                            {field.confidence}%
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Mock Line Items Array */}
              <div className="space-y-4 pt-4">
                <h3 className="text-sm font-medium text-zinc-300 border-b border-zinc-800 pb-2 flex items-center justify-between">
                  <span>Line Items Array</span>
                  <Badge variant="outline" className="bg-zinc-900 text-zinc-500 border-zinc-800 rounded-full px-2 py-0">3 elements</Badge>
                </h3>
                <div className="border border-zinc-800 rounded-md bg-zinc-900/30 overflow-hidden text-sm">
                  <div className="flex items-center justify-between p-3 border-b border-zinc-800/50 bg-zinc-900/50">
                     <div className="flex items-center gap-2 text-zinc-300">
                       <ListDashesIcon /> [{`{`} "description", "qty", "unitPrice" {`}`}, ...]
                     </div>
                     <CaretDownIcon className="text-zinc-500" />
                  </div>
                  <div className="p-4 text-xs font-mono text-zinc-500 leading-relaxed bg-zinc-950/50">
                    // The system correctly mapped the nested grid.<br/>
                    // Validated structurally against standard schema.
                  </div>
                </div>
              </div>

            </div>
          </ScrollArea>

          {/* Sticky Bottom Bar */}
          <div className="flex-none p-4 border-t border-zinc-800 bg-zinc-950/80 backdrop-blur-sm flex justify-between items-center">
            <div className="text-xs text-zinc-500 font-mono">
              Action registers deterministic template to DB.
            </div>
            <Button className="bg-emerald-600 hover:bg-emerald-500 text-white gap-2 font-medium">
              <CheckCircleIcon weight="bold" className="h-4 w-4" />
              Approve Layout & Persist
            </Button>
          </div>
        </section>

      </main>
    </div>
  )
}
