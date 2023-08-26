import React from "react";
import { Session } from "@supabase/auth-helpers-nextjs";
import type { AppProps } from "next/app";
import { ThemeProvider } from "@/components/theme-provider";
import "@lepton/ui/styles/globals.css";
import "@/styles/globals.css";

function App({ Component, pageProps }: AppProps<{ initialSession: Session }>) {
  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
      <Component {...pageProps} />
    </ThemeProvider>
  );
}

export default App;
