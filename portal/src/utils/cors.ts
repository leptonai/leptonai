import { NextApiHandler, NextApiRequest, NextApiResponse } from "next";

const allowOrigin = (origin?: string): origin is string => {
  if (!origin) {
    return false;
  }

  // use regex to allow all subdomains of lepton.ai and preview domains on vercel
  const allowedOrigins = [
    /^https:\/\/(.+\.)?lepton\.ai$/i,
    /^https:\/\/lepton-.+-leptonai\.vercel\.app$/i,
  ];

  if (process.env.NODE_ENV !== "production") {
    return true;
  }

  return allowedOrigins.some((allowedOrigin) => allowedOrigin.test(origin));
};

export const cors =
  (fn: NextApiHandler): NextApiHandler =>
  async (req: NextApiRequest, res: NextApiResponse) => {
    res.setHeader("Access-Control-Allow-Credentials", "true");

    res.setHeader("Cache-Control", "no-store");

    if (allowOrigin(req.headers.origin)) {
      res.setHeader("Access-Control-Allow-Origin", req.headers.origin);
    }

    res.setHeader(
      "Access-Control-Allow-Methods",
      "GET,OPTIONS,PATCH,DELETE,POST,PUT",
    );
    res.setHeader(
      "Access-Control-Allow-Headers",
      "X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version",
    );
    if (req.method === "OPTIONS") {
      res.status(200).end();
      return;
    }
    return await fn(req, res);
  };
