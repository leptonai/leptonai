import { useMonaco } from "@monaco-editor/react";
import { useEffect } from "react";

export const useSetupMonaco = () => {
  const monaco = useMonaco();

  useEffect(() => {
    if (monaco) {
      monaco.editor.defineTheme("lepton", {
        base: "vs-dark",
        inherit: true,
        rules: [],
        colors: {
          "editor.background": "#1e1f29",
        },
      });
    }
  }, [monaco]);
};
