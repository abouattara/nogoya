export const REFRESH_COOKIE = "nogoya_refresh";

export const refreshCookieOptions = {
  httpOnly: true,
  sameSite: "lax" as const,
  secure: process.env.NODE_ENV === "production",
  path: "/",
  maxAge: 60 * 60 * 24 * 14, // 14 days — matches SIMPLE_JWT REFRESH_TOKEN_LIFETIME
};
