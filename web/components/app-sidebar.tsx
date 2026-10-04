"use client";

import { MessageSquare, Phone, Plus, Trash2 } from "lucide-react";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuAction,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from "@/components/ui/sidebar";
import type { Chat } from "@/lib/types";

function groupByDay(chats: Chat[]): [string, Chat[]][] {
  const startOfToday = new Date().setHours(0, 0, 0, 0);
  const day = 86_400_000;
  const groups: Record<string, Chat[]> = { Today: [], Yesterday: [], "Previous 7 days": [], Older: [] };
  for (const c of chats) {
    const age = startOfToday - c.createdAt;
    const key = age <= 0 ? "Today" : age <= day ? "Yesterday" : age <= 7 * day ? "Previous 7 days" : "Older";
    groups[key].push(c);
  }
  return Object.entries(groups).filter(([, list]) => list.length > 0);
}

export function AppSidebar({
  chats,
  activeId,
  onSelect,
  onNew,
  onDelete,
}: {
  chats: Chat[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
}) {
  return (
    <Sidebar>
      <SidebarHeader>
        <div className="flex items-center gap-2 px-2 py-1.5">
          <span className="text-2xl" aria-hidden>
            🌾
          </span>
          <div className="leading-tight">
            <div className="font-semibold">KisanMitra AI</div>
            <div className="text-xs text-muted-foreground">Farmer&apos;s friend</div>
          </div>
        </div>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton onClick={onNew} className="font-medium">
              <Plus />
              New chat
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent>
        {groupByDay(chats).map(([label, list]) => (
          <SidebarGroup key={label}>
            <SidebarGroupLabel>{label}</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {list.map((c) => (
                  <SidebarMenuItem key={c.id}>
                    <SidebarMenuButton isActive={c.id === activeId} onClick={() => onSelect(c.id)}>
                      <MessageSquare />
                      <span className="truncate">{c.title}</span>
                    </SidebarMenuButton>
                    <SidebarMenuAction showOnHover aria-label={`Delete chat: ${c.title}`} onClick={() => onDelete(c.id)}>
                      <Trash2 />
                    </SidebarMenuAction>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        ))}
        {chats.length === 0 && <p className="px-4 py-2 text-sm text-muted-foreground">Your chats will appear here.</p>}
      </SidebarContent>

      <SidebarFooter>
        <div className="flex items-center gap-2 rounded-lg bg-sidebar-accent px-3 py-2 text-xs">
          <Phone className="size-4 shrink-0 text-primary" />
          <div>
            <div className="font-medium">Kisan Call Centre</div>
            <div className="text-muted-foreground">1800-180-1551 (free)</div>
          </div>
        </div>
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}
