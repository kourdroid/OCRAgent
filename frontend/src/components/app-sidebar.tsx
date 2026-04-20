"use client"

import * as React from "react"
import { usePathname } from "next/navigation"
import Link from "next/link"
import {
  Buildings,
  FileCode,
  GearSix,
  SquaresFour,
  ShieldCheck,
} from "@phosphor-icons/react"

import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from "@/components/ui/sidebar"

// Sample navigation data
const navItems = [
  {
    title: "Command Center",
    url: "/",
    icon: SquaresFour,
  },
  {
    title: "Vendor Registry",
    url: "#",
    icon: Buildings,
    badge: "142",
  },
  {
    title: "Extraction Schemas",
    url: "#",
    icon: FileCode,
  },
  {
    title: "System Settings",
    url: "#",
    icon: GearSix,
  },
]

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const pathname = usePathname()

  return (
    <Sidebar className="border-r border-zinc-800 bg-zinc-950" {...props}>
      <SidebarHeader className="border-b border-zinc-800 bg-zinc-950 px-4 py-4 h-16 shrink-0 flex flex-row items-center">
        <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded bg-emerald-600/20 text-emerald-500 mr-3 border border-emerald-500/20">
          <ShieldCheck weight="fill" className="h-4 w-4" />
        </div>
        <div className="flex flex-col flex-1 truncate">
          <span className="truncate text-sm font-semibold tracking-tight text-zinc-100">Ironclad OCR</span>
          <span className="truncate text-[10px] text-zinc-500 font-mono tracking-wider">v5.0 SOVEREIGN</span>
        </div>
      </SidebarHeader>
      
      <SidebarContent className="bg-zinc-950 pt-4">
        <SidebarGroup>
          <SidebarGroupLabel className="text-zinc-500 text-xs font-mono uppercase tracking-wider mb-2">
            Operations
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {navItems.map((item) => {
                // simple active state check for root vs others
                const isActive = item.url === "/" ? pathname === "/" : pathname.startsWith(item.url)
                return (
                  <SidebarMenuItem key={item.title}>
                    <SidebarMenuButton 
                      render={<Link href={item.url} />}
                      isActive={isActive} 
                      tooltip={item.title}
                      className="text-zinc-400 hover:text-zinc-100 hover:bg-zinc-900 active:bg-zinc-800/50 data-[active=true]:bg-zinc-900 data-[active=true]:text-zinc-100 font-medium transition-colors"
                    >
                      <item.icon className="h-4 w-4 shrink-0" weight={isActive ? "fill" : "regular"} />
                      <span>{item.title}</span>
                      {item.badge && (
                        <span className="ml-auto bg-zinc-800 text-zinc-300 text-[10px] font-mono px-1.5 py-0.5 rounded">
                          {item.badge}
                        </span>
                      )}
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                )
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      
      <SidebarRail />
    </Sidebar>
  )
}
