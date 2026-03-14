"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Plus,
  Search,
  ShieldCheck,
} from "lucide-react";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";

const NAV_ITEMS = [
  {
    label: "Dashboard",
    icon: LayoutDashboard,
    href: "/dashboard",
    testId: "sidebar-link-dashboard",
  },
  {
    label: "Browse Agents",
    icon: Search,
    href: "/browse",
    testId: "sidebar-link-browse",
  },
  {
    label: "Register Agent",
    icon: Plus,
    href: "/dashboard/register",
    testId: "sidebar-link-register",
  },
  {
    label: "Verify Agent",
    icon: ShieldCheck,
    href: "/dashboard/verify",
    testId: "sidebar-link-verify",
  },
] as const;

export function AppSidebar() {
  const pathname = usePathname();

  return (
    <Sidebar className="bg-background border-r border-sidebar-border font-sans">
      <SidebarContent data-testid="app-sidebar">
        <SidebarGroup>
          <SidebarGroupLabel>Navigation</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {NAV_ITEMS.map((item) => {
                const isActive =
                  pathname === item.href ||
                  (item.href !== "/dashboard" && pathname.startsWith(item.href));
                return (
                  <SidebarMenuItem key={item.href}>
                    <SidebarMenuButton asChild isActive={isActive} tooltip={item.label}>
                      <Link
                        href={item.href}
                        data-testid={item.testId}
                        className="flex items-center gap-2"
                      >
                        <item.icon className="size-4 shrink-0" />
                        <span>{item.label}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
    </Sidebar>
  );
}
