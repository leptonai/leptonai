import React from "react";
import { Session } from "@supabase/auth-helpers-nextjs";
import type { AppProps } from "next/app";
import "@lepton/ui/styles/globals.css";
import "@/styles/globals.css";

function App({ Component, pageProps }: AppProps<{ initialSession: Session }>) {
  return <Component {...pageProps} />;
}

export default App;
