import { afterEach, describe, expect, it } from "vitest";
import { VISITOR_COOKIE, isVisitorId, readVisitorCookie } from "./visitor";

function setCookie(value: string) {
  document.cookie = `${VISITOR_COOKIE}=${value}; path=/`;
}

afterEach(() => {
  document.cookie = `${VISITOR_COOKIE}=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT`;
});

describe("visitor id", () => {
  it("accepts a 32-hex id and rejects anything else", () => {
    expect(isVisitorId("a".repeat(32))).toBe(true);
    expect(isVisitorId("A".repeat(32))).toBe(false); // uppercase is not what we mint
    expect(isVisitorId("a".repeat(31))).toBe(false);
    expect(isVisitorId("../../etc/passwd")).toBe(false);
    expect(isVisitorId(undefined)).toBe(false);
  });

  it("reads the cookie the middleware sets", () => {
    const id = "0123456789abcdef0123456789abcdef";
    setCookie(id);
    expect(readVisitorCookie()).toBe(id);
  });

  it("ignores a tampered cookie instead of forwarding it", () => {
    setCookie("not-an-id");
    expect(readVisitorCookie()).toBeNull();
  });

  it("returns null when no cookie is present", () => {
    expect(readVisitorCookie()).toBeNull();
  });
});
