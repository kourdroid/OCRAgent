"use client"

import * as React from "react"
import { usePathname } from "next/navigation"
import Link from "next/link"
import { Bell, Files, ShieldCheck, SlidersHorizontal, type LucideIcon } from "lucide-react"

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

type NavItem = {
  title: string;
  url: string;
  icon: LucideIcon;
  badge?: string;
};

const navItems: NavItem[] = [
  {
    title: "Dossiers",
    url: "/dossiers",
    icon: Files,
  },
  {
    title: "Paramètres",
    url: "/admin",
    icon: SlidersHorizontal,
  },
  {
    title: "Notifications",
    url: "/notifications",
    icon: Bell,
  },
]

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const pathname = usePathname()

  function isActive(url: string): boolean {
    if (url === "/" && pathname === "/") return true
    if (url !== "/" && pathname.startsWith(url)) return true
    return false
  }

  return (
    <Sidebar className="border-r border-slate-200 bg-white shadow-[8px_0_28px_rgba(15,23,42,0.03)]" {...props}>
      <SidebarHeader className="h-20 shrink-0 border-b border-slate-200 bg-white px-5 py-4">
        <div className="flex items-center">
        <div className="mr-3 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-blue-600 text-white shadow-sm">
          <ShieldCheck className="h-4 w-4" />
        </div>
        <div className="flex flex-col flex-1 truncate">
          <span className="truncate text-sm font-semibold tracking-tight text-slate-900">Ironclad</span>
          <span className="truncate text-[10px] font-medium tracking-wide text-slate-500">GESTION DOCUMENTAIRE</span>
        </div>
        </div>
      </SidebarHeader>
      
      <SidebarContent className="bg-white px-3 pt-5">
        <SidebarGroup>
          <SidebarGroupLabel className="mb-2 text-xs font-medium uppercase tracking-wider text-slate-400">
            Espace de travail
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {navItems.map((item) => {
                const active = isActive(item.url)
                return (
                  <SidebarMenuItem key={item.title}>
                    <SidebarMenuButton 
                      render={<Link href={item.url} />}
                      isActive={active} 
                      tooltip={item.title}
                      className="rounded-lg px-3 text-slate-600 hover:bg-slate-50 hover:text-slate-900 active:bg-blue-50 data-[active=true]:bg-blue-50 data-[active=true]:text-blue-700 data-[active=true]:font-semibold font-medium transition-colors"
                    >
                      <item.icon className="h-4 w-4 shrink-0" />
                      <span>{item.title}</span>
                      {item.badge && (
                        <span className="ml-auto rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[10px] text-slate-500">
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
