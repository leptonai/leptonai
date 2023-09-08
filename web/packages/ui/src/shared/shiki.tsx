import {
  createContext,
  FC,
  PropsWithChildren,
  useContext,
  useMemo,
  useState,
} from "react";
import {
  getHighlighter as getShikiHighlighter,
  Highlighter,
  renderToHtml,
  setCDN as setShikiCDN,
} from "shiki";
import { isBrowser } from "@lepton/ui/utils";

export type Languages =
  | "bash"
  | "python"
  | "json"
  | "css"
  | "cpp"
  | "c"
  | "go"
  | "html"
  | "js"
  | "ts"
  | "java"
  | "sql"
  | "yaml";

export function normalizeLanguage(language: string): Languages | undefined {
  switch (language) {
    case "shell":
    case "powershell":
    case "bash":
    case "sh":
    case "bat":
      return "bash";
    case "python":
    case "py":
      return "python";
    case "json":
      return "json";
    case "css":
      return "css";
    case "cpp":
      return "cpp";
    case "c":
      return "c";
    case "go":
    case "golang":
      return "go";
    case "html":
      return "html";
    case "typescript":
    case "ts":
      return "ts";
    case "javascript":
    case "js":
      return "js";
    case "java":
      return "java";
    case "sql":
      return "sql";
    case "yaml":
      return "yaml";
    default:
      return void 0;
  }
}

export const setCDNInBrowser = (cdn: string) => {
  if (isBrowser()) {
    setShikiCDN(cdn);
  }
};

export const ShikiContext = createContext<{
  setThemeMode: (mode: "dark" | "light") => void;
  themeMode: "dark" | "light";
  getHighlighter: () => Promise<Highlighter>;
  renderToHtml: typeof renderToHtml;
}>({
  setThemeMode: () => void 0,
  themeMode: "light",
  getHighlighter: () => Promise.reject(new Error("Not Implemented")),
  renderToHtml,
});

export const ShikiProvider: FC<PropsWithChildren> = ({ children }) => {
  const [highlighter, setHighlighter] = useState<Promise<Highlighter>>();
  const [themeMode, setThemeMode] = useState<"dark" | "light">("light");

  const getHighlighter = useMemo(() => {
    return () => {
      if (highlighter) {
        return highlighter;
      } else {
        const _highlighter = getShikiHighlighter({
          themes: ["github-dark", "github-light"],
          langs: [
            "bash",
            "python",
            "json",
            "css",
            "cpp",
            "c",
            "go",
            "html",
            "js",
            "ts",
            "java",
            "sql",
            "yaml",
          ],
        });
        setHighlighter(_highlighter);
        return _highlighter;
      }
    };
  }, [highlighter]);

  return (
    <ShikiContext.Provider
      value={{
        setThemeMode,
        themeMode,
        getHighlighter,
        renderToHtml,
      }}
    >
      {children}
    </ShikiContext.Provider>
  );
};

export const useBrowserShiki = () => {
  return useContext(ShikiContext);
};
