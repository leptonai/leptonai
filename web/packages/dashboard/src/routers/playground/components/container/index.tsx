import { Copy, Share } from "@carbon/icons-react";
import { FC, ReactNode, useCallback } from "react";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@lepton/ui/components/popover";
import { Input } from "@lepton/ui/components/input";
import { Button } from "@lepton/ui/components/button";
import { useToast } from "@lepton/ui/hooks/use-toast";
import { Skeleton } from "@lepton/ui/components/skeleton";
import { Delay } from "@lepton/ui/components/delay";

export const Container: FC<{
  icon: ReactNode;
  title: ReactNode;
  content: ReactNode;
  option: ReactNode;
  extra?: ReactNode;
  loading: boolean;
}> = ({ icon, title, extra, content, option, loading }) => {
  const { toast } = useToast();

  const copy = useCallback(() => {
    void navigator.clipboard.writeText(location.href);
    toast({
      description: "Copied to clipboard",
    });
  }, [toast]);
  return (
    <div className="flex flex-col flex-auto max-w-screen-xl p-4 sm:p-8 w-full min-h-full mx-auto">
      <div className="flex flex-auto flex-col border border-border rounded-md overflow-hidden bg-background">
        <div className="flex items-center justify-between py-2 px-4 border-b border-border">
          <div className="space-x-4 flex items-center">
            {icon}
            {title}
          </div>
          <div className="space-x-4 flex items-center">
            {extra}
            <Popover>
              <PopoverTrigger asChild>
                <Button variant="ghost" size="sm">
                  <Share className="w-3 h-3 md:mr-2" />
                  <span className="hidden md:inline">Share</span>
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-90">
                <div className="space-y-2">
                  <p className="text-sm text-muted-foreground">
                    Anyone who has this link will be able to view this
                  </p>
                  <div className="space-x-2 flex items-center">
                    <Input
                      className="flex-auto"
                      value={location.href}
                      readOnly
                    />
                    <Button onClick={copy}>
                      <Copy className="w-3 h-3" />
                    </Button>
                  </div>
                </div>
              </PopoverContent>
            </Popover>
          </div>
        </div>
        <div className="flex flex-auto h-full flex-col items-stretch md:flex-row gap-2">
          <div className="p-4 flex grow border-border border-0 md:border-r">
            {loading ? (
              <Delay delay={300}>
                <div className="space-y-2 flex-1">
                  <Skeleton className="h-20 w-full" />
                  <Skeleton className="h-10 w-full" />
                </div>
              </Delay>
            ) : (
              content
            )}
          </div>
          <div className="p-4 w-full md:w-2/6 lg:w-1/4">
            {loading ? (
              <Delay delay={300}>
                <div className="space-y-2 flex-1">
                  <Skeleton className="h-8 w-full" />
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-8 w-full" />
                  <Skeleton className="h-4 w-full" />
                </div>
              </Delay>
            ) : (
              option
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
