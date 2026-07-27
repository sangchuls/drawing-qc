import { NextResponse } from "next/server";
import { createUploadToken } from "@/lib/auth";

// Protected by middleware (requires a valid session cookie already).
// Issues a short-lived token the browser attaches when uploading directly
// to the FastAPI backend, so the backend can confirm the request came
// through our password gate without needing to call back into Next.js.
export async function POST() {
  const token = await createUploadToken();
  return NextResponse.json({ token });
}
