import { Languages } from "@lepton/ui/shared/shiki";
import {
  FC,
  PropsWithChildren,
  ReactNode,
  useCallback,
  useMemo,
  useState,
} from "react";
import {
  CodeBlock,
  createStringLiteralSecretTokenMasker,
} from "@lepton/ui/components/code-block";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@lepton/ui/components/dialog";
import { Button } from "@lepton/ui/components/button";
import { useToast } from "@lepton/ui/hooks/use-toast";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@lepton/ui/components/tabs";

const languageMap: { [key: string]: Languages } = {
  Python: "python",
  HTTP: "bash",
  "Node.js": "js",
} as const;

export const CodeAPIDialogContent: FC<
  {
    codes: { language: string; code: string }[];
    open: boolean;
    onOpenChange: (open: boolean) => void;
    maskString?: string;
    title?: ReactNode;
  } & PropsWithChildren
> = ({ title, codes, maskString, onOpenChange, open }) => {
  const { toast } = useToast();
  const [language, setLanguage] = useState(codes[0].language);
  const activeCode = useMemo(
    () => codes.find((c) => c.language === language)!.code,
    [language, codes]
  );
  const highlightLanguage: Languages = useMemo(() => {
    return languageMap[language] || "bash";
  }, [language]);
  const copy = useCallback(() => {
    void navigator.clipboard.writeText(activeCode);
    void toast({
      description: <>Copied to clipboard</>,
    });
  }, [activeCode, toast]);
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>
        <Tabs
          value={language}
          onValueChange={setLanguage}
          className="w-full overflow-hidden"
        >
          <TabsList>
            {codes.map((c) => (
              <TabsTrigger key={c.language} value={c.language}>
                {c.language}
              </TabsTrigger>
            ))}
          </TabsList>
          {codes.map((c) => (
            <TabsContent
              key={c.language}
              value={c.language}
              className="h-[300px] border bg-muted rounded"
            >
              <CodeBlock
                transparentBg
                copyable
                tokenMask={createStringLiteralSecretTokenMasker(
                  maskString || "",
                  {
                    startAt: 3,
                    endAt: 3,
                    template:
                      highlightLanguage === "bash"
                        ? (quote, secret) =>
                            `${quote}Authorization: Bearer ${secret}${quote}`
                        : undefined,
                  }
                )}
                code={activeCode}
                language={highlightLanguage}
              />
            </TabsContent>
          ))}
        </Tabs>
        <DialogFooter className="flex space-x-0 space-y-2 sm:space-y-0">
          <Button
            variant="secondary"
            onClick={() => onOpenChange(false)}
            className="mt-2 sm:mt-0"
          >
            Close
          </Button>
          <Button onClick={copy}>Copy to Clipboard</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
