import { cn } from "@/lib/utils";

export function Badge({ className, variant = "default", ...props }: React.HTMLAttributes<HTMLSpanElement> & {
  variant?: "default" | "success" | "warning" | "destructive" | "muted";
}) {
  const styles = {
    default: "bg-[hsl(var(--accent))] text-white",
    success: "bg-green-600 text-white",
    warning: "bg-yellow-500 text-black",
    destructive: "bg-red-600 text-white",
    muted: "bg-[hsl(var(--muted)/0.2)] text-[hsl(var(--fg))]",
  }[variant];
  return (
    <span
      className={cn("inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium", styles, className)}
      {...props}
    />
  );
}
