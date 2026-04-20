"use client";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { QK, STALE } from "@/lib/query";
import { Badge } from "@/components/ui/badge";

export function HealthBadge() {
  const { data, isError } = useQuery({
    queryKey: QK.health,
    queryFn: api.health,
    refetchInterval: STALE.health,
    staleTime: STALE.health,
  });

  if (isError || !data) return <Badge variant="destructive">API offline</Badge>;
  const variant = data.status === "ok" ? "success" : "warning";
  const spent = `₹${data.llm_budget_spent_today.toFixed(2)}/${data.daily_cap_inr.toFixed(0)}`;
  return <Badge variant={variant}>API {data.status} · {spent}</Badge>;
}
