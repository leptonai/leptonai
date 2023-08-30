import ReactDOM from "react-dom/client";
import App from "@lepton-dashboard/app";
import "./index.css";
import "xterm/css/xterm.css";
import dayjs from "dayjs";
import LocalizedFormat from "dayjs/plugin/localizedFormat";
import relativeTime from "dayjs/plugin/relativeTime";
import timezone from "dayjs/plugin/timezone";
import utc from "dayjs/plugin/utc";
import { StrictMode } from "react";
import { Analytics } from "@vercel/analytics/react";
import "@lepton/ui/styles/globals.css";
import { setCDNInBrowser } from "@lepton/ui/shared/shiki";

dayjs.extend(utc);
dayjs.extend(timezone);
dayjs.extend(LocalizedFormat);
dayjs.extend(relativeTime);
setCDNInBrowser("/shiki/");

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <StrictMode>
    <App />
    <Analytics />
  </StrictMode>
);
