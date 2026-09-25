import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AudioRecorder } from "./AudioRecorder";

/** Minimal MediaRecorder stand-in: jsdom ships none. */
class FakeMediaRecorder {
  static isTypeSupported = vi.fn().mockReturnValue(true);
  ondataavailable: ((event: { data: Blob }) => void) | null = null;
  onstop: (() => void) | null = null;
  state = "inactive";
  mimeType = "audio/webm";

  start() {
    this.state = "recording";
  }
  pause() {
    this.state = "paused";
  }
  resume() {
    this.state = "recording";
  }
  stop() {
    this.state = "inactive";
    this.ondataavailable?.({ data: new Blob(["audio-bytes"], { type: "audio/webm" }) });
    this.onstop?.();
  }
}

const stopTrack = vi.fn();

beforeEach(() => {
  vi.stubGlobal("MediaRecorder", FakeMediaRecorder);
  Object.defineProperty(navigator, "mediaDevices", {
    configurable: true,
    value: { getUserMedia: vi.fn().mockResolvedValue({ getTracks: () => [{ stop: stopTrack }] }) },
  });
  global.URL.createObjectURL = vi.fn().mockReturnValue("blob:preview");
  global.URL.revokeObjectURL = vi.fn();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("AudioRecorder", () => {
  it("records, previews and hands the clip to the parent", async () => {
    const onReady = vi.fn();
    render(<AudioRecorder onReady={onReady} />);

    await userEvent.click(screen.getByRole("button", { name: /enregistrer un message vocal/i }));
    await waitFor(() => screen.getByText(/enregistrement/i));

    await userEvent.click(screen.getByRole("button", { name: /arrêter/i }));
    await waitFor(() => screen.getByRole("button", { name: /^envoyer$/i }));

    await userEvent.click(screen.getByRole("button", { name: /^envoyer$/i }));

    expect(onReady).toHaveBeenCalledTimes(1);
    const clip = onReady.mock.calls[0][0];
    expect(clip.file).toBeInstanceOf(File);
    expect(clip.duration).toBeGreaterThan(0);
  });

  it("can be discarded before sending", async () => {
    const onReady = vi.fn();
    const onCancel = vi.fn();
    render(<AudioRecorder onReady={onReady} onCancel={onCancel} />);

    await userEvent.click(screen.getByRole("button", { name: /enregistrer un message vocal/i }));
    await userEvent.click(screen.getByRole("button", { name: /arrêter/i }));
    await waitFor(() => screen.getByRole("button", { name: /supprimer le vocal/i }));
    await userEvent.click(screen.getByRole("button", { name: /supprimer le vocal/i }));

    expect(onReady).not.toHaveBeenCalled();
    expect(onCancel).toHaveBeenCalled();
    expect(screen.getByRole("button", { name: /enregistrer un message vocal/i })).toBeInTheDocument();
  });

  it("pauses and resumes", async () => {
    render(<AudioRecorder onReady={vi.fn()} />);

    await userEvent.click(screen.getByRole("button", { name: /enregistrer un message vocal/i }));
    await userEvent.click(screen.getByRole("button", { name: /pause/i }));
    expect(screen.getByText(/en pause/i)).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /reprendre/i }));
    expect(screen.getByText(/enregistrement/i)).toBeInTheDocument();
  });

  it("explains a refused microphone instead of failing silently", async () => {
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: {
        getUserMedia: vi.fn().mockRejectedValue(
          Object.assign(new Error("denied"), { name: "NotAllowedError" })
        ),
      },
    });

    render(<AudioRecorder onReady={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", { name: /enregistrer un message vocal/i }));

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(/micro refusé/i));
  });

  it("releases the microphone once the clip is captured", async () => {
    render(<AudioRecorder onReady={vi.fn()} />);

    await userEvent.click(screen.getByRole("button", { name: /enregistrer un message vocal/i }));
    await userEvent.click(screen.getByRole("button", { name: /arrêter/i }));

    await waitFor(() => expect(stopTrack).toHaveBeenCalled());
  });
});
