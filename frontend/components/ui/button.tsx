import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none",
  {
    variants: {
      variant: {
        default: "bg-[hsl(var(--accent))] text-white hover:opacity-90",
        outline: "border border-[hsl(var(--border))] bg-transparent hover:bg-[hsl(var(--muted)/0.1)]",
        ghost: "bg-transparent hover:bg-[hsl(var(--muted)/0.1)]",
        destructive: "bg-red-600 text-white hover:bg-red-700",
      },
      size: { sm: "h-8 px-3", md: "h-10 px-4", lg: "h-11 px-6" },
    },
    defaultVariants: { variant: "default", size: "md" },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => (
    <button ref={ref} className={cn(buttonVariants({ variant, size }), className)} {...props} />
  )
);
Button.displayName = "Button";
