import { Injectable } from "injection-js";
import va from "@vercel/analytics";

@Injectable()
export class EventTrackerService {
  track(event: "API_ERROR" | "JS_ERROR", message: Record<string, string>) {
    va.track(event, message);
  }
}
