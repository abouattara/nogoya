import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

// The App Router isn't mounted in jsdom, so every navigation hook is stubbed
// here. Individual tests can still override this mock when they assert on
// navigation.
export const routerMock = {
  push: vi.fn(),
  replace: vi.fn(),
  refresh: vi.fn(),
  back: vi.fn(),
  forward: vi.fn(),
  prefetch: vi.fn(),
};

vi.mock("next/navigation", () => ({
  useRouter: () => routerMock,
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => "/",
  notFound: vi.fn(),
}));

// next/image renders a plain <img> in tests — jsdom has no image pipeline.
vi.mock("next/image", () => ({
  default: ({ src, alt, ...rest }: { src: string; alt: string; fill?: boolean }) => {
    const { fill: _fill, ...imgProps } = rest as Record<string, unknown>;
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={typeof src === "string" ? src : ""} alt={alt} {...imgProps} />;
  },
}));

// jsdom implements neither of these; components guard on them.
if (!window.HTMLMediaElement.prototype.play) {
  window.HTMLMediaElement.prototype.play = vi.fn().mockResolvedValue(undefined);
}
window.HTMLMediaElement.prototype.pause = vi.fn();
