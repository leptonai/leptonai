import { Injectable } from "injection-js";
import { H } from "highlight.run";

@Injectable()
export class TrackerService {
  error(
    error: Error,
    message: "API_ERROR" | "JS_ERROR",
    payload: Record<string, string>
  ) {
    if (import.meta.env.VITE_HIGHLIGHT_PROJECT_ID) {
      H.consumeError(error, message, payload);
    }
  }

  identify(id: string, payload: Record<string, string>) {
    if (import.meta.env.VITE_HIGHLIGHT_PROJECT_ID) {
      H.identify(id, payload);
    }
  }
}
