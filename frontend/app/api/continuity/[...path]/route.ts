import type { NextRequest } from "next/server";

async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const apiUrl = process.env.CONTINUITY_API_URL ?? "http://localhost:8000";
  const target = new URL(`${apiUrl}/${path.join("/")}`);
  target.search = request.nextUrl.search;
  const body = request.method === "GET" || request.method === "HEAD" ? undefined : await request.text();
  const response = await fetch(target, {
    method: request.method,
    headers: { "Content-Type": request.headers.get("content-type") ?? "application/json" },
    body,
    cache: "no-store"
  });
  return new Response(response.body, { status: response.status, headers: { "Content-Type": response.headers.get("content-type") ?? "application/json" } });
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
