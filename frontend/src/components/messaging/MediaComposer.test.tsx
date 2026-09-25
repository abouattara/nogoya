import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MediaComposer, UploadProgress, type PendingMedia } from "./MediaComposer";

const prepareImage = vi.hoisted(() => vi.fn());
const prepareVideo = vi.hoisted(() => vi.fn());
vi.mock("@/lib/media-prep", async () => {
  const actual = await vi.importActual<typeof import("@/lib/media-prep")>("@/lib/media-prep");
  return { ...actual, prepareImage, prepareVideo };
});

function imageFile(name = "photo.jpg", size = 1_000) {
  const file = new File(["x".repeat(size)], name, { type: "image/jpeg" });
  Object.defineProperty(file, "size", { value: size });
  return file;
}

function videoFile(name = "clip.mp4", size = 1_000) {
  const file = new File(["x".repeat(size)], name, { type: "video/mp4" });
  Object.defineProperty(file, "size", { value: size });
  return file;
}

function pending(overrides: Partial<PendingMedia> = {}): PendingMedia {
  return {
    id: "1",
    kind: "image",
    file: imageFile(),
    poster: null,
    duration: 0,
    previewUrl: "blob:preview",
    originalSize: 4_000_000,
    ...overrides,
  };
}

describe("MediaComposer", () => {
  beforeEach(() => {
    prepareImage.mockReset();
    prepareVideo.mockReset();
    prepareImage.mockImplementation(async (file: File) => ({
      file,
      width: 800,
      height: 600,
      previewUrl: "blob:preview",
      originalSize: file.size,
    }));
    prepareVideo.mockImplementation(async (file: File) => ({
      file,
      poster: imageFile("poster.jpg"),
      duration: 10,
      previewUrl: "blob:preview",
    }));
    global.URL.createObjectURL = vi.fn().mockReturnValue("blob:preview");
    global.URL.revokeObjectURL = vi.fn();
  });

  it("compresses a picture before it is queued for sending", async () => {
    const onChange = vi.fn();
    const { container } = render(
      <MediaComposer items={[]} onChange={onChange} limit={6} />
    );

    const input = container.querySelector('input[accept="image/*"]') as HTMLInputElement;
    await userEvent.upload(input, imageFile());

    await waitFor(() => expect(prepareImage).toHaveBeenCalled());
    expect(onChange).toHaveBeenCalledWith([expect.objectContaining({ kind: "image" })]);
  });

  it("refuses a video longer than a minute, before any upload", async () => {
    prepareVideo.mockResolvedValue({
      file: videoFile(),
      poster: null,
      duration: 120,
      previewUrl: "blob:preview",
    });
    const onChange = vi.fn();
    const { container } = render(<MediaComposer items={[]} onChange={onChange} limit={6} />);

    const input = container.querySelector('input[accept="video/*"]') as HTMLInputElement;
    await userEvent.upload(input, videoFile());

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(/60 secondes/));
    expect(onChange).not.toHaveBeenCalled();
  });

  it("refuses an oversized picture with a readable message", async () => {
    const onChange = vi.fn();
    const { container } = render(<MediaComposer items={[]} onChange={onChange} limit={6} />);

    const input = container.querySelector('input[accept="image/*"]') as HTMLInputElement;
    await userEvent.upload(input, imageFile("huge.jpg", 20 * 1024 * 1024));

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(/dépasse/));
    expect(onChange).not.toHaveBeenCalled();
  });

  it("stops at the attachment limit", async () => {
    const onChange = vi.fn();
    const { container } = render(
      <MediaComposer items={[pending(), pending({ id: "2" })]} onChange={onChange} limit={2} />
    );

    const input = container.querySelector('input[accept="image/*"]') as HTMLInputElement;
    await userEvent.upload(input, imageFile());

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(/2 fichiers au maximum/));
  });

  it("lets one queued file be removed individually", async () => {
    const onChange = vi.fn();
    render(
      <MediaComposer items={[pending(), pending({ id: "2" })]} onChange={onChange} limit={6} />
    );

    await userEvent.click(screen.getAllByRole("button", { name: /retirer ce fichier/i })[0]);

    expect(onChange).toHaveBeenCalledWith([expect.objectContaining({ id: "2" })]);
  });

  it("previews what is about to be sent", () => {
    render(<MediaComposer items={[pending()]} onChange={vi.fn()} limit={6} />);

    expect(screen.getByRole("img")).toHaveAttribute("src", "blob:preview");
  });
});

describe("UploadProgress", () => {
  it("reports how far the upload got and offers a way out", async () => {
    const onCancel = vi.fn();
    render(<UploadProgress percent={72} onCancel={onCancel} />);

    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "72");
    expect(screen.getByText("72%")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /annuler/i }));
    expect(onCancel).toHaveBeenCalled();
  });
});
