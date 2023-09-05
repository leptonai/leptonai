import { cn } from "@lepton/ui/utils";
import { HTMLAttributes } from "react";

export const Typography = {
  Code: ({ className, ...props }: HTMLAttributes<HTMLElement>) => (
    <code
      className={cn(
        "relative rounded bg-muted border px-[0.2rem] py-[0.1rem] font-mono text-xs",
        className
      )}
      {...props}
    />
  ),
};
