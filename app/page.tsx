"use client"

import { MagnifyingGlassIcon, UploadSimpleIcon, DotsThreeIcon } from "@phosphor-icons/react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

const invoices = [
  {
    id: "FA2109-0333",
    vendor: "LABEL TECH",
    type: "INVOICE",
    amount: "960.22 MAD",
    date: "2021-09-17",
    status: "BLOCKED_DISCREPANCY",
  },
  {
    id: "FA2109-0334",
    vendor: "DHL Express",
    type: "INVOICE",
    amount: "1,245.80 MAD",
    date: "2021-09-18",
    status: "CLEARED",
  },
  {
    id: "FA2109-0335",
    vendor: "Maroc Telecom",
    type: "INVOICE",
    amount: "3,892.00 MAD",
    date: "2021-09-19",
    status: "WAITING_WAREHOUSE",
  },
  {
    id: "FA2109-0336",
    vendor: "Ooredoo",
    type: "INVOICE",
    amount: "756.45 MAD",
    date: "2021-09-20",
    status: "CLEARED",
  },
  {
    id: "FA2109-0337",
    vendor: "Air Liquide",
    type: "INVOICE",
    amount: "12,450.00 MAD",
    date: "2021-09-21",
    status: "BLOCKED_DISCREPANCY",
  },
]

const statusConfig = {
  CLEARED: {
    label: "Cleared",
    className: "bg-emerald-950/50 text-emerald-400 border-emerald-800/50",
  },
  BLOCKED_DISCREPANCY: {
    label: "Blocked",
    className: "bg-red-950/50 text-red-400 border-red-800/50",
  },
  WAITING_WAREHOUSE: {
    label: "Awaiting",
    className: "bg-amber-950/50 text-amber-400 border-amber-800/50",
  },
}

export default function CommandCenterPage() {
  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <div className="mx-auto max-w-7xl px-6 py-8">
        <header className="mb-8 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-zinc-800">
              <div className="h-4 w-4 rounded-sm bg-gradient-to-br from-zinc-100 to-zinc-400" />
            </div>
            <h1 className="text-xl font-semibold tracking-tight">Ironclad Command</h1>
          </div>
          <div className="flex items-center gap-4">
            <div className="relative w-80">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
              <Input
                placeholder="Search POs, Invoices..."
                className="h-10 border-zinc-800 bg-zinc-900/50 pl-10 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-zinc-700 focus:ring-zinc-700"
              />
            </div>
            <Button className="h-10 gap-2 bg-zinc-100 text-zinc-950 hover:bg-zinc-200">
              <UploadSimpleIcon className="h-4 w-4" weight="bold" />
              <span className="text-sm font-medium">Upload Documents</span>
            </Button>
          </div>
        </header>

        <div className="mb-6">
          <Tabs defaultValue="action" className="w-full">
            <TabsList className="h-auto gap-1 border-b border-zinc-800 bg-transparent p-0">
              <TabsTrigger
                value="action"
                className="relative h-9 rounded-none border-b-2 border-transparent px-4 text-sm font-medium text-zinc-400 data-[state=active]:border-zinc-100 data-[state=active]:text-zinc-100 data-[state=active]:shadow-none"
              >
                Action Required
              </TabsTrigger>
              <TabsTrigger
                value="warehouse"
                className="relative h-9 rounded-none border-b-2 border-transparent px-4 text-sm font-medium text-zinc-400 data-[state=active]:border-zinc-100 data-[state=active]:text-zinc-100 data-[state=active]:shadow-none"
              >
                Awaiting Warehouse
              </TabsTrigger>
              <TabsTrigger
                value="cleared"
                className="relative h-9 rounded-none border-b-2 border-transparent px-4 text-sm font-medium text-zinc-400 data-[state=active]:border-zinc-100 data-[state=active]:text-zinc-100 data-[state=active]:shadow-none"
              >
                Cleared
              </TabsTrigger>
            </TabsList>
          </Tabs>
        </div>

        <div className="overflow-hidden rounded-lg border border-zinc-800">
          <Table>
            <TableHeader>
              <TableRow className="border-zinc-800 hover:bg-transparent">
                <TableHead className="h-11 border-b border-zinc-800 bg-zinc-900/30 px-4 text-xs font-medium uppercase tracking-wider text-zinc-500">
                  ID
                </TableHead>
                <TableHead className="h-11 border-b border-zinc-800 bg-zinc-900/30 px-4 text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Vendor
                </TableHead>
                <TableHead className="h-11 border-b border-zinc-800 bg-zinc-900/30 px-4 text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Type
                </TableHead>
                <TableHead className="h-11 border-b border-zinc-800 bg-zinc-900/30 px-4 text-right text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Amount
                </TableHead>
                <TableHead className="h-11 border-b border-zinc-800 bg-zinc-900/30 px-4 text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Date
                </TableHead>
                <TableHead className="h-11 border-b border-zinc-800 bg-zinc-900/30 px-4 text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Status
                </TableHead>
                <TableHead className="h-11 border-b border-zinc-800 bg-zinc-900/30 px-4 text-right text-xs font-medium uppercase tracking-wider text-zinc-500">
                  <span className="sr-only">Actions</span>
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {invoices.map((invoice) => {
                const config = statusConfig[invoice.status as keyof typeof statusConfig]
                return (
                  <TableRow
                    key={invoice.id}
                    className="border-zinc-800/50 transition-colors hover:bg-zinc-900/30 data-[state=selected]:bg-zinc-900/50"
                  >
                    <TableCell className="px-4 py-3 font-mono text-sm text-zinc-300">
                      {invoice.id}
                    </TableCell>
                    <TableCell className="px-4 py-3 text-sm text-zinc-100">
                      {invoice.vendor}
                    </TableCell>
                    <TableCell className="px-4 py-3">
                      <span className="inline-flex items-center rounded-md bg-zinc-800/50 px-2 py-0.5 text-xs font-medium text-zinc-400">
                        {invoice.type}
                      </span>
                    </TableCell>
                    <TableCell className="px-4 py-3 text-right font-mono text-sm text-zinc-100">
                      {invoice.amount}
                    </TableCell>
                    <TableCell className="px-4 py-3 font-mono text-sm text-zinc-400">
                      {invoice.date}
                    </TableCell>
                    <TableCell className="px-4 py-3">
                      <Badge
                        variant="outline"
                        className={`rounded-md border px-2 py-0.5 text-xs font-medium ${config.className}`}
                      >
                        {config.label}
                      </Badge>
                    </TableCell>
                    <TableCell className="px-4 py-3 text-right">
                      <Button
                        variant="ghost"
                        size="icon-xs"
                        className="h-8 w-8 text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/50"
                      >
                        <DotsThreeIcon className="h-4 w-4" weight="bold" />
                      </Button>
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </div>
      </div>
    </div>
  )
}
