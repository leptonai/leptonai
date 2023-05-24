import ReactDOM from "react-dom/client";
import App from "@lepton-dashboard/app";
import "./index.css";
import "xterm/css/xterm.css";
import dayjs from "dayjs";
import LocalizedFormat from "dayjs/plugin/localizedFormat";
import relativeTime from "dayjs/plugin/relativeTime";
import { StrictMode } from "react";

dayjs.extend(LocalizedFormat);
dayjs.extend(relativeTime);

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <StrictMode>
    <App />
  </StrictMode>
);
