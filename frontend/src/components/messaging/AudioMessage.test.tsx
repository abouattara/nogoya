import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AudioMessage } from "./AudioMessage";

const apiFetchBlob = vi.hoisted(() => vi.fn());
vi.mock("@/lib/client-api", () => ({
  apiFetchBlob,
  ApiError: class extends Error {},
}));

describe("AudioMessage", () => {
  const src = "http://127.0.0.1:8000/api/v1/conversations/1/messages/5/audio/";

  beforeEach(() => {
    apiFetchBlob.mockReset();
    apiFetchBlob.mockResolvedValue(new Blob(["fake-audio"], { type: "audio/webm" }));
    global.URL.createObjectURL = vi.fn().mockReturnValue("blob:fake");
    global.URL.revokeObjectURL = vi.fn();
  });

  it("shows the duration handed down by the API before metadata loads", () => {
    render(<AudioMessage src={src} duration={78} />);

    expect(screen.getByText("0:00 / 1:18")).toBeInTheDocument();
  });

  it("downloads the clip with the access token, not as a bare <audio src>", async () => {
    // The endpoint is participant-only; a plain media request carries no
    // Authorization header and came back 401.
    window.HTMLMediaElement.prototype.play = vi.fn().mockResolvedValue(undefined);
    const { container } = render(<AudioMessage src={src} duration={12} />);

    expect(container.querySelector("audio")).not.toHaveAttribute("src");

    await userEvent.click(screen.getByRole("button", { name: /écouter le message vocal/i }));

    await waitFor(() => expect(apiFetchBlob).toHaveBeenCalledWith(src));
  });

  it("plays and pauses from the same control", async () => {
    const play = vi.fn().mockResolvedValue(undefined);
    const pause = vi.fn();
    window.HTMLMediaElement.prototype.play = play;
    window.HTMLMediaElement.prototype.pause = pause;

    render(<AudioMessage src={src} duration={12} />);

    await userEvent.click(screen.getByRole("button", { name: /écouter le message vocal/i }));
    await waitFor(() => expect(play).toHaveBeenCalled());

    await waitFor(() => screen.getByRole("button", { name: /mettre en pause/i }));
    await userEvent.click(screen.getByRole("button", { name: /mettre en pause/i }));
    expect(pause).toHaveBeenCalled();
  });

  it("fetches the clip only once, however often it is replayed", async () => {
    window.HTMLMediaElement.prototype.play = vi.fn().mockResolvedValue(undefined);
    window.HTMLMediaElement.prototype.pause = vi.fn();

    render(<AudioMessage src={src} duration={12} />);
    const play = screen.getByRole("button", { name: /écouter le message vocal/i });

    await userEvent.click(play);
    await waitFor(() => screen.getByRole("button", { name: /mettre en pause/i }));
    await userEvent.click(screen.getByRole("button", { name: /mettre en pause/i }));
    await userEvent.click(screen.getByRole("button", { name: /écouter le message vocal/i }));

    await waitFor(() => expect(apiFetchBlob).toHaveBeenCalledTimes(1));
  });

  it("surfaces an error instead of a dead player when the download fails", async () => {
    apiFetchBlob.mockRejectedValue(new Error("401"));

    render(<AudioMessage src={src} duration={12} />);
    await userEvent.click(screen.getByRole("button", { name: /écouter/i }));

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(/indisponible/i));
  });

  it("surfaces an error instead of a dead player when playback fails", async () => {
    window.HTMLMediaElement.prototype.play = vi.fn().mockRejectedValue(new Error("no codec"));

    render(<AudioMessage src={src} duration={12} />);
    await userEvent.click(screen.getByRole("button", { name: /écouter/i }));

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(/indisponible/i));
  });

  it("offers a download control that goes through the authenticated fetch", async () => {
    render(<AudioMessage src={src} duration={12} />);

    await userEvent.click(screen.getByRole("button", { name: /télécharger le vocal/i }));

    await waitFor(() => expect(apiFetchBlob).toHaveBeenCalledWith(src));
  });

  it("exposes an accessible progress slider", () => {
    render(<AudioMessage src={src} duration={30} />);

    expect(screen.getByRole("slider", { name: /progression du vocal/i })).toBeInTheDocument();
  });
});
