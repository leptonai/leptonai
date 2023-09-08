/* eslint-disable react/prop-types */
import * as React from "react";

import { cn } from "@lepton/ui/utils";
import { useEffect, useMemo } from "react";

export interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  className?: string;
  minRows?: number;
  maxRows?: number;
}

// px-2 is 8px * 2
const gap = 16;

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, rows, maxRows, minRows, value, onChange, ...props }, ref) => {
    const cName = useMemo(
      () =>
        cn(
          "flex min-h-[60px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50",
          className
        ),
      [className]
    );
    const measurementRef = React.useRef<HTMLTextAreaElement>(null);
    const textareaRef = React.useRef<HTMLTextAreaElement | null>(null);
    const debounceRef = React.useRef<number | null>(null);
    const autosized = useMemo(() => {
      if (rows) {
        return false;
      }
      return minRows !== undefined || maxRows !== undefined;
    }, [rows, minRows, maxRows]);

    const getLineHeight = React.useCallback(() => {
      if (!autosized) {
        return 0;
      }
      if (measurementRef.current) {
        return measurementRef.current.clientHeight;
      }
    }, [autosized]);

    const debounce = React.useCallback((fn: () => void, delay: number) => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
      debounceRef.current = window.setTimeout(
        () => {
          fn();
          debounceRef.current = null;
        },
        debounceRef.current ? delay : 0
      );
    }, []);

    const fitTextarea = React.useCallback(() => {
      if (!autosized || !textareaRef.current) {
        return;
      }
      const lineHeight = getLineHeight();
      if (!lineHeight) {
        return;
      }
      const overflow = textareaRef.current.style.overflow;
      textareaRef.current.style.overflow = "hidden";
      textareaRef.current.style.height = "auto";
      const { placeholder, scrollHeight } = textareaRef.current;
      textareaRef.current.placeholder = "";
      let height =
        Math.round((scrollHeight - gap) / lineHeight) * lineHeight + gap;
      const maxHeight = maxRows ? maxRows * lineHeight + gap : undefined;
      const minHeight = minRows ? minRows * lineHeight + gap : undefined;

      if (maxHeight) {
        textareaRef.current.style.maxHeight = `${maxHeight}px`;
        if (height > maxHeight) {
          height = maxHeight;
        }
      }

      if (minHeight) {
        textareaRef.current.style.minHeight = `${minHeight}px`;
        if (height < minHeight) {
          height = minHeight;
        }
      }

      textareaRef.current.style.height = `${height}px`;
      textareaRef.current.style.overflow = overflow;
      textareaRef.current.placeholder = placeholder;
    }, [autosized, getLineHeight, maxRows, minRows]);

    React.useLayoutEffect(() => {
      if (!autosized) {
        return;
      }
      const measurement = measurementRef.current;
      if (!measurement) {
        return;
      }
      fitTextarea();
    }, [autosized, fitTextarea]);

    useEffect(() => {
      debounce(fitTextarea, 100);
    }, [value, debounce, fitTextarea]);

    return (
      <>
        <textarea
          className={cName}
          ref={(r) => {
            textareaRef.current = r;
            if (ref) {
              if (typeof ref === "function") {
                ref(r);
              } else {
                ref.current = r;
              }
            }
          }}
          onChange={(e) => {
            if (onChange) {
              onChange(e);
            }
            fitTextarea();
          }}
          value={value}
          {...props}
        />
        {autosized && (
          <textarea
            className={cName}
            ref={measurementRef}
            style={{
              ...props.style,
              position: "absolute",
              top: -10000,
              left: -10000,
              visibility: "hidden",
              overflow: "hidden",
              border: "none",
              padding: 0,
              height: "initial",
              minHeight: "initial",
              maxHeight: "initial",
            }}
            rows={1}
          />
        )}
      </>
    );
  }
);
Textarea.displayName = "Textarea";

export { Textarea };
