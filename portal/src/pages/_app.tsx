import { Session } from "@supabase/auth-helpers-nextjs";
import type { AppProps } from "next/app";
import "@/styles/globals.css";

function App({ Component, pageProps }: AppProps<{ initialSession: Session }>) {
  return <Component {...pageProps} />;
}

export default App;
