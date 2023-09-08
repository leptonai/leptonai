import { H } from "@highlight-run/node";
import { NextApiHandler, NextApiRequest, NextApiResponse } from "next";

H.init({
  projectID: process.env.HIGHLIGHT_PROJECT_ID || "",
  manualStart: !process.env.HIGHLIGHT_PROJECT_ID,
});

export const withLogging =
  (fn: NextApiHandler): NextApiHandler =>
  async (req: NextApiRequest, res: NextApiResponse) => {
    const start = Date.now();
    const method = req.method;
    const origin = req.headers.origin;
    const pathname = req.url;
    const reqHeaders = { ...req.headers };
    const { secureSessionId, requestId } = H.parseHeaders(reqHeaders) || {};
    const reqBody = req.body;
    delete reqHeaders["cookie"];
    try {
      return await fn(req, res);
    } catch (e) {
      if (e instanceof Error) {
        H.consumeError(e);
        await H.flush();
      }
      res.statusCode = 500;
      res.statusMessage = "Internal Server Error";
      throw e;
    } finally {
      const delta = `${(Date.now() - start) / 1000}s`;
      const status = res.statusCode;
      const statusMessage = res.statusMessage;
      if (status >= 500) {
        H.consumeError(
          new Error(`SERVER_ERROR ${pathname} ${method} ${statusMessage}`),
          secureSessionId,
          requestId,
          {
            delta,
            status,
            method,
            origin,
            pathname,
            statusMessage,
            reqHeaders: JSON.stringify(reqHeaders, null, 2),
            reqBody: JSON.stringify(reqBody, null, 2),
          }
        );
        await H.flush();
      }
      if (secureSessionId) {
        H.recordMetric(
          secureSessionId,
          "latency",
          (Date.now() - start) * 1000000,
          requestId
        );
        await H.flush();
      }
    }
  };
