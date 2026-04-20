"use client"

import { use } from "react"
import Link from "next/link"
import { ArrowLeftIcon, ShieldWarningIcon, CheckCircleIcon, XCircleIcon } from "@phosphor-icons/react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { SidebarTrigger } from "@/components/ui/sidebar"

const mockLineItems = [
  { id: "001", description: "Industrial Sensors (12V)", qtyPO: 50, qtyGR: 50, qtyInv: 50, unitPrice: "12.00 MAD", isDiscrepancy: false },
  { id: "002", description: "Label Printer Ribbons", qtyPO: 100, qtyGR: 96, qtyInv: 100, unitPrice: "4.50 MAD", isDiscrepancy: true },
  { id: "003", description: "Maintenance Kit B", qtyPO: 2, qtyGR: 2, qtyInv: 2, unitPrice: "140.00 MAD", isDiscrepancy: false },
]

export default function AuditMatrixPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 w-full overflow-x-hidden">
      <div className="mx-auto max-w-7xl px-6 py-8">
        
        {/* Header Section */}
        <header className="mb-8 flex items-start justify-between">
          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-2">
              <SidebarTrigger className="-ml-2 hover:bg-zinc-800 text-zinc-400 hover:text-zinc-100" />
              <Link href="/" className="inline-flex items-center gap-2 text-sm text-zinc-500 hover:text-zinc-300">
                <ArrowLeftIcon className="h-4 w-4" />
                <span>Back to Command Center</span>
              </Link>
            </div>
            <div className="flex items-center gap-4">
              <h1 className="text-2xl font-semibold tracking-tight">{id}</h1>
              <Badge variant="outline" className="bg-red-950/50 text-red-400 border-red-800/50 gap-1.5 px-2.5 py-1">
                <ShieldWarningIcon weight="fill" className="h-3.5 w-3.5" />
                BLOCKED_DISCREPANCY
              </Badge>
            </div>
            <div className="flex gap-4 text-sm text-zinc-400">
              <span>Vendor: <strong className="text-zinc-200">LABEL TECH</strong></span>
              <span>•</span>
              <span>Total: <strong className="text-zinc-200 font-mono">960.22 MAD</strong></span>
              <span>•</span>
              <span>Date: <strong className="text-zinc-200 font-mono">2021-09-17</strong></span>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <Button variant="ghost" className="h-10 text-red-400 hover:text-red-300 hover:bg-red-950/50 gap-2 border border-red-900/30">
              <XCircleIcon className="h-5 w-5" weight="fill" />
              Reject Invoice
            </Button>
            <Button className="h-10 gap-2 bg-zinc-100 text-zinc-950 hover:bg-zinc-200">
              <CheckCircleIcon className="h-5 w-5" weight="fill" />
              Force Approve
            </Button>
          </div>
        </header>

        {/* Audit Resolution Matrix */}
        <div className="grid lg:grid-cols-3 gap-6">
          
          {/* Column 1: System of Record (PO) */}
          <Card className="border-zinc-800 bg-zinc-900/30 text-zinc-100 overflow-hidden">
            <CardHeader className="border-b border-zinc-800 bg-zinc-900/50 pb-4">
              <CardTitle className="text-sm font-medium text-zinc-400 uppercase tracking-wider">
                1. Purchase Order
              </CardTitle>
              <p className="text-xs text-zinc-500 mt-1">Requested by Procurement</p>
            </CardHeader>
            <CardContent className="p-0">
              {mockLineItems.map((item, idx) => (
                <div key={`po-${item.id}`} className="p-4 border-b border-zinc-800/50 last:border-0 hover:bg-zinc-900/40 transition-colors">
                  <div className="flex justify-between items-start mb-2">
                    <span className="text-sm font-medium">{item.description}</span>
                    <span className="text-xs font-mono text-zinc-500">{item.id}</span>
                  </div>
                  <div className="flex justify-between items-center mt-3">
                    <div className="text-xs text-zinc-500">Qty Ordered</div>
                    <div className="font-mono text-sm">{item.qtyPO}</div>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Column 2: Reality (Goods Receipt) */}
          <Card className="border-zinc-800 bg-zinc-900/30 text-zinc-100 overflow-hidden relative">
            {/* Contextual Discrepancy Highlight Layer */}
            <div className="absolute inset-0 pointer-events-none" style={{
              background: 'linear-gradient(180deg, transparent 40%, rgba(248, 113, 113, 0.03) 50%, transparent 60%)'
            }} />
            <CardHeader className="border-b border-zinc-800 bg-zinc-900/50 pb-4">
              <CardTitle className="text-sm font-medium text-zinc-400 uppercase tracking-wider">
                2. Goods Receipt
              </CardTitle>
              <p className="text-xs text-zinc-500 mt-1">Received at Warehouse</p>
            </CardHeader>
            <CardContent className="p-0 relative z-10">
              {mockLineItems.map((item, idx) => (
                <div key={`gr-${item.id}`} className={`p-4 border-b border-zinc-800/50 last:border-0 transition-colors ${item.isDiscrepancy ? 'bg-red-950/20' : 'hover:bg-zinc-900/40'}`}>
                  <div className="flex justify-between items-start mb-2">
                    <span className={`text-sm font-medium ${item.isDiscrepancy ? 'text-red-200' : ''}`}>{item.description}</span>
                  </div>
                  <div className="flex justify-between items-center mt-3">
                    <div className={`text-xs ${item.isDiscrepancy ? 'text-red-400/70' : 'text-zinc-500'}`}>Qty Received</div>
                    <div className={`font-mono text-sm ${item.isDiscrepancy ? 'text-red-400 font-bold bg-red-950/50 px-2 py-0.5 rounded border border-red-900/50' : ''}`}>
                      {item.qtyGR}
                    </div>
                  </div>
                  {item.isDiscrepancy && (
                    <div className="mt-2 text-[11px] text-red-400 flex items-center gap-1">
                      <ShieldWarningIcon weight="fill" />
                      Missing {item.qtyPO - item.qtyGR} units
                    </div>
                  )}
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Column 3: The Claim (Vendor Invoice) */}
          <Card className="border-zinc-800 bg-zinc-900/30 text-zinc-100 overflow-hidden relative">
            <CardHeader className="border-b border-zinc-800 bg-zinc-900/50 pb-4">
              <CardTitle className="text-sm font-medium text-zinc-400 uppercase tracking-wider flex items-center gap-2">
                3. Vendor Invoice
                <Badge variant="secondary" className="bg-zinc-800 text-zinc-300 text-[10px] px-1.5 py-0">OCR EXTRACTED</Badge>
              </CardTitle>
              <p className="text-xs text-zinc-500 mt-1">Billed by Vendor</p>
            </CardHeader>
            <CardContent className="p-0">
              {mockLineItems.map((item, idx) => (
                <div key={`inv-${item.id}`} className={`p-4 border-b border-zinc-800/50 last:border-0 transition-colors ${item.isDiscrepancy ? 'bg-zinc-900/80 border-l-[3px] border-l-red-500' : 'hover:bg-zinc-900/40'}`}>
                  <div className="flex justify-between items-start mb-2">
                    <span className="text-sm font-medium">{item.description}</span>
                  </div>
                  <div className="flex justify-between items-center mt-3">
                    <div className={`text-xs ${item.isDiscrepancy ? 'text-zinc-400' : 'text-zinc-500'}`}>Qty Billed</div>
                    <div className={`font-mono text-sm ${item.isDiscrepancy ? 'line-through text-red-300 opacity-70' : ''}`}>
                      {item.qtyInv}
                    </div>
                  </div>
                  <div className="flex justify-between items-center mt-1">
                    <div className="text-xs text-zinc-500">Unit Price</div>
                    <div className="font-mono text-xs text-zinc-400">{item.unitPrice}</div>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
          
        </div>

      </div>
    </div>
  )
}
