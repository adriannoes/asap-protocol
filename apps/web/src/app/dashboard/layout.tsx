import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/layout/app-sidebar";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <SidebarProvider>
      <AppSidebar />
      <main className="flex-1" data-testid="dashboard-main">
        <SidebarTrigger
          className="lg:hidden"
          data-testid="sidebar-mobile-trigger"
        />
        {children}
      </main>
    </SidebarProvider>
  );
}
