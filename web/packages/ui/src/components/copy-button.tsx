import { FC, HTMLAttributes, useEffect, useState } from "react";
import { Button } from "@lepton/ui/components/button";
import { cn } from "@lepton/ui/utils";
import { CheckIcon, CopyIcon } from "@radix-ui/react-icons";

export interface CopyButtonProps extends HTMLAttributes<HTMLButtonElement> {
  value: string;
}

export async function copyToClipboardWithMeta(value: string) {
  void navigator.clipboard.writeText(value);
}

export const CopyButton: FC<CopyButtonProps> = ({
  value,
  className,
  ...props
}) => {
  const [hasCopied, setHasCopied] = useState(false);

  useEffect(() => {
    setTimeout(() => {
      setHasCopied(false);
    }, 2000);
  }, [hasCopied]);

  return (
    <Button
      size="icon"
      variant="secondary"
      className={cn("relative z-10 h-6 w-6", className)}
      onClick={() => {
        void copyToClipboardWithMeta(value);
        setHasCopied(true);
      }}
      {...props}
    >
      <span className="sr-only">Copy</span>
      {hasCopied ? (
        <CheckIcon className="h-3 w-3" />
      ) : (
        <CopyIcon className="h-3 w-3" />
      )}
    </Button>
  );
};
