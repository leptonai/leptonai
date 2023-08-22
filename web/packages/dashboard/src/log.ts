import { H } from "highlight.run";

H.init(import.meta.env.VITE_HIGHLIGHT_PROJECT_ID || "", {
  environment: import.meta.env.MODE,
  manualStart: !import.meta.env.VITE_HIGHLIGHT_PROJECT_ID,
  tracingOrigins: ["localhost", "portal.daily.lepton.ai", "portal.lepton.ai"],
  reportConsoleErrors: true,
  enableStrictPrivacy: true,
  networkRecording: {
    enabled: true,
    recordHeadersAndBody: true,
    urlBlocklist: [
      // insert full or partial urls that you don't want to record here
      // Out of the box, Highlight will not record these URLs (they can be safely removed):
    ],
  },
});
