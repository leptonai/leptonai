import { StrictMode } from "react";
import ReactDOM from "react-dom/client";
import App from "@lepton-dashboard/app.tsx";
import "./index.css";
import dayjs from "dayjs";
import LocalizedFormat from "dayjs/plugin/localizedFormat";
import relativeTime from "dayjs/plugin/relativeTime";

dayjs.extend(LocalizedFormat);
dayjs.extend(relativeTime);

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <StrictMode>
    <App />
  </StrictMode>
);
