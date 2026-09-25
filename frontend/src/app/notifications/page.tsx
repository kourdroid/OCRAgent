"use client";

import * as React from "react";
import Link from "next/link";
import { Bell, Check, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { listNotifications, markNotificationRead } from "@/lib/api";
import { DELASSUS_CLIENT_ID } from "@/lib/clients";
import type { NotificationItem } from "@/lib/types";

export default function NotificationsPage() {
  const [items, setItems] = React.useState<NotificationItem[]>([]);
  const [error, setError] = React.useState<string | null>(null);
  const load = React.useCallback(async () => {
    try { setItems(await listNotifications(DELASSUS_CLIENT_ID)); setError(null); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Notifications could not be loaded"); }
  }, []);
  React.useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);
  async function read(item: NotificationItem) {
    await markNotificationRead(item.notification_id, DELASSUS_CLIENT_ID);
    await load();
  }
  return <div className="min-h-screen bg-zinc-950 text-zinc-100"><header className="border-b border-zinc-800"><div className="flex min-h-16 items-center justify-between px-5"><div className="flex items-center gap-3"><SidebarTrigger className="text-zinc-400" /><div><h1 className="text-lg font-semibold">Notification inbox</h1><p className="text-xs text-zinc-500">Processing, review, and ruleset events</p></div></div><Button variant="outline" size="icon" title="Refresh notifications" onClick={() => void load()} className="border-zinc-800"><RefreshCw className="h-4 w-4" /></Button></div></header><main className="mx-auto max-w-4xl px-5 py-6">{error && <p className="border border-red-900 p-3 text-sm text-red-300">{error}</p>}<div className="divide-y divide-zinc-800 border-y border-zinc-800">{items.map((item) => <div key={item.notification_id} className={`flex gap-4 p-4 ${item.read_at ? "opacity-60" : ""}`}><Bell className={`mt-0.5 h-4 w-4 ${item.severity === "critical" ? "text-red-400" : item.severity === "warning" ? "text-amber-400" : "text-sky-400"}`} /><div className="min-w-0 flex-1"><p className="text-sm font-medium">{item.title}</p><p className="mt-1 text-sm text-zinc-400">{item.message}</p><p className="mt-2 font-mono text-[10px] text-zinc-600">{new Date(item.created_at).toLocaleString()}</p></div>{item.case_id && <Button render={<Link href={`/dossiers/${item.case_id}`} />} variant="outline" size="sm" className="border-zinc-700">Open</Button>}{!item.read_at && <Button variant="ghost" size="icon" title="Mark as read" onClick={() => void read(item)} className="text-zinc-400"><Check className="h-4 w-4" /></Button>}</div>)}{items.length === 0 && <p className="p-5 text-sm text-zinc-600">No notifications.</p>}</div></main></div>;
}
