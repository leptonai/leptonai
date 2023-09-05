import { SendAltFilled, StopFilledAlt } from "@carbon/icons-react";
import {
  forwardRef,
  ForwardRefExoticComponent,
  ReactNode,
  RefAttributes,
  useEffect,
  useImperativeHandle,
  useRef,
} from "react";
import { Textarea } from "@lepton/ui/components/textarea";
import { Button } from "@lepton/ui/components/button";

export interface PromptInputRef {
  focus: () => void;
}

export const PromptInput = forwardRef<
  PromptInputRef,
  {
    disabled?: boolean;
    loading: boolean;
    value: string;
    onChange: (v: string) => void;
    onSubmit: () => void;
    submitText?: string;
    submitIcon?: ForwardRefExoticComponent<
      RefAttributes<SVGSVGElement> & { className?: string }
    >;
    onCancel: () => void;
    extra?: ReactNode;
    maxRows?: number;
    className?: string;
  }
>(
  (
    {
      disabled = false,
      value,
      onChange,
      loading,
      onCancel,
      onSubmit,
      extra,
      className,
      submitText = "Send",
      submitIcon: SubmitIcon = SendAltFilled,
      maxRows = 2,
    },
    ref
  ) => {
    const inputRef = useRef<HTMLTextAreaElement>(null);
    const compositionState = useRef(false);

    useImperativeHandle(
      ref,
      () => ({
        focus: () => {
          inputRef.current?.focus();
        },
      }),
      []
    );

    useEffect(() => {
      inputRef.current?.select();
    }, []);
    return (
      <div
        onClick={() => inputRef.current?.focus()}
        className={`${className} flex flex-col border bg-muted rounded ring-offset-background focus-within:ring-ring focus-within:outline-none focus-within:ring-1 focus-within:ring-offset-1`}
      >
        <div className="grow">
          <Textarea
            className="border-0 resize-none bg-transparent shadow-none focus-visible:outline-none focus-visible:ring-0 focus-visible:ring-offset-0"
            rows={maxRows}
            disabled={disabled}
            ref={inputRef}
            placeholder="Send a message"
            value={value}
            onCompositionStart={() => (compositionState.current = true)}
            onCompositionEnd={() => (compositionState.current = false)}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={(e) => {
              if (
                e.key === "Enter" &&
                !e.shiftKey &&
                !compositionState.current
              ) {
                e.preventDefault();
                if (!loading) {
                  onSubmit();
                }
              }
            }}
          />
        </div>
        <div className="shrink flex flex-row-reverse">
          <div className="space-x-2 m-2" onClick={(e) => e.stopPropagation()}>
            {extra}

            {!loading ? (
              <Button size="sm" disabled={disabled} onClick={onSubmit}>
                <SubmitIcon className="mr-2 h-3 w-3" />
                {submitText}
              </Button>
            ) : (
              <Button size="sm" onClick={onCancel}>
                <StopFilledAlt className="mr-2 h-3 w-3" /> Stop
              </Button>
            )}
          </div>
        </div>
      </div>
    );
  }
);

PromptInput.displayName = "PromptInput";
