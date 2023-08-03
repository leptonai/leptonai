import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export async function middleware(req: NextRequest) {
  const res = NextResponse.next();

  if (req.nextUrl.pathname === "/api/auth/logout") {
    req.cookies.delete(["supabase-auth-token", "sb-oauth-auth-token"]);
  }

  return res;
}

export const config = {
  matcher: "/api/auth/logout",
};
