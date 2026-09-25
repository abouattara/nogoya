"use client";

import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";
import { Spinner } from "@/components/ui/Feedback";
import { useAuthStore, type SessionUser } from "@/store/auth-store";

export function RequireAuth({
  children,
  role,
}: {
  children: (user: SessionUser) => ReactNode;
  role?: "supplier" | "visitor";
}) {
  const { user, status } = useAuthStore();
  const router = useRouter();

  useEffect(() => {
    if (status === "ready" && !user) router.replace("/login");
    if (status === "ready" && user && role && user.role !== role) router.replace("/compte");
  }, [status, user, role, router]);

  if (status !== "ready" || !user) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <Spinner className="h-6 w-6 text-brand" />
      </div>
    );
  }
  if (role && user.role !== role) return null;

  return <>{children(user)}</>;
}
