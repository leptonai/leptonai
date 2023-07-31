import { NextApiHandler, NextApiRequest, NextApiResponse } from "next";

const allowOrigin = (origin?: string): origin is string => {
  if (!origin) {
    return false;
  }
  if (process.env.NODE_ENV === "production") {
    return ["https://dashboard.lepton.ai", "https://lepton.ai"].includes(
      origin,
    );
  }
  return origin.includes("localhost") || origin.includes("leptonai.vercel.app");
};

export const cors =
  (fn: NextApiHandler): NextApiHandler =>
  async (req: NextApiRequest, res: NextApiResponse) => {
    res.setHeader("Access-Control-Allow-Credentials", "true");

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
