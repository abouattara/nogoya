import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { NotificationBell } from "./NotificationBell";
import { renderWithProviders } from "@/test-utils";
import type { AppNotification } from "@/lib/types";

const apiFetch = vi.hoisted(() => vi.fn());
vi.mock("@/lib/client-api", () => ({ apiFetch, ApiError: class extends Error {} }));

function notification(overrides: Partial<AppNotification> = {}): AppNotification {
  return {
    id: 1,
    type: "new_message",
    title: "Nouveau message de Issa",
    message: "Bonjour, encore disponible ?",
    url: "/compte/messages/3",
    data: {},
    is_read: false,
    read_at: null,
    created_at: new Date().toISOString(),
    ...overrides,
  };
}

function mockEndpoints({ unread = 2, items = [notification()] } = {}) {
  apiFetch.mockImplementation((path: string) => {
    if (path.includes("unread-count")) return Promise.resolve({ unread_count: unread });
    if (path.includes("read-all")) return Promise.resolve({ marked_read: unread });
    if (path.endsWith("/read/")) return Promise.resolve(notification({ is_read: true }));
    return Promise.resolve({ count: items.length, next: null, previous: null, results: items });
  });
}

describe("NotificationBell", () => {
  it("shows the unread badge coming from the API", async () => {
    mockEndpoints({ unread: 3 });
    renderWithProviders(<NotificationBell />);

    await waitFor(() => expect(screen.getByText("3")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: /3 non lues/i })).toBeInTheDocument();
  });

  it("caps the badge at 9+", async () => {
    mockEndpoints({ unread: 42 });
    renderWithProviders(<NotificationBell />);

    await waitFor(() => expect(screen.getByText("9+")).toBeInTheDocument());
  });

  it("hides the badge when everything is read", async () => {
    mockEndpoints({ unread: 0 });
    renderWithProviders(<NotificationBell />);

    await waitFor(() => expect(screen.getByRole("button", { name: "Notifications" })).toBeInTheDocument());
    expect(screen.queryByText("0")).not.toBeInTheDocument();
  });

  it("opens the panel and lists recent notifications", async () => {
    mockEndpoints();
    renderWithProviders(<NotificationBell />);

    await userEvent.click(screen.getByRole("button", { name: /notifications/i }));

    await waitFor(() => expect(screen.getByText("Nouveau message de Issa")).toBeInTheDocument());
    expect(screen.getByRole("link", { name: /voir toutes les notifications/i })).toHaveAttribute(
      "href",
      "/notifications"
    );
  });

  it("marks everything as read from the panel", async () => {
    mockEndpoints();
    renderWithProviders(<NotificationBell />);

    await userEvent.click(screen.getByRole("button", { name: /notifications/i }));
    await waitFor(() => screen.getByText(/tout marquer comme lu/i));
    await userEvent.click(screen.getByText(/tout marquer comme lu/i));

    expect(apiFetch).toHaveBeenCalledWith("/api/v1/notifications/read-all/", { method: "POST" });
  });

  it("shows an empty state when there is nothing to read", async () => {
    mockEndpoints({ unread: 0, items: [] });
    renderWithProviders(<NotificationBell />);

    await userEvent.click(screen.getByRole("button", { name: /notifications/i }));
    await waitFor(() =>
      expect(screen.getByText(/aucune notification pour le moment/i)).toBeInTheDocument()
    );
  });
});
