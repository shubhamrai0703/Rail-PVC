import { AppShell } from "@/components/shell/AppShell";

export default function AppGroupLayout({ children }: { children: React.ReactNode }) {
  // P4-001 will add the auth guard here (redirect to /login when no session).
  return <AppShell>{children}</AppShell>;
}
