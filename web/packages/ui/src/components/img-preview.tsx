import { forwardRef, ImgHTMLAttributes, useRef, useState } from "react";
import {
  Root,
  Trigger,
  Portal,
  Overlay,
  Content,
  Close,
} from "@radix-ui/react-dialog";
import { cn } from "@lepton/ui/utils";
import { Cross2Icon } from "@radix-ui/react-icons";

export interface ImgPreviewProps extends ImgHTMLAttributes<HTMLImageElement> {
  alt: string;
  src: string;
}

export const ImgPreview = forwardRef<HTMLImageElement, ImgPreviewProps>(
  ({ alt, className, ...props }, ref) => {
    const [open, setOpen] = useState(false);
    const previewImageRef = useRef<HTMLImageElement>(null);
    return (
      <Root open={open} onOpenChange={setOpen}>
        <Trigger asChild>
          <img
            className={cn("cursor-pointer", className)}
            ref={ref}
            alt={alt}
            {...props}
          />
        </Trigger>
        <Portal>
          <Overlay className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
          <Content
            className="w-full h-full fixed left-[50%] top-[50%] z-50 translate-x-[-50%] translate-y-[-50%] duration-200 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[state=closed]:slide-out-to-left-1/2 data-[state=closed]:slide-out-to-top-[48%] data-[state=open]:slide-in-from-left-1/2 data-[state=open]:slide-in-from-top-[48%]"
            onClick={(e) => {
              if (e.target !== previewImageRef.current) {
                setOpen(false);
              }
            }}
          >
            <div className="absolute inset-0 flex justify-center items-center">
              <img
                className="max-w-full h-auto"
                ref={previewImageRef}
                alt={alt}
                {...props}
              />
            </div>
            <Close className="fixed right-4 top-4 z-50 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:pointer-events-none data-[state=open]:bg-accent data-[state=open]:text-muted-foreground">
              <Cross2Icon className="h-5 w-5" />
              <span className="sr-only">Close</span>
            </Close>
          </Content>
        </Portal>
      </Root>
    );
  }
);

ImgPreview.displayName = "ImgPreview";
