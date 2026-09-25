import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AttachmentGallery } from "./AttachmentGallery";
import { makeAttachment } from "@/test-utils";

const apiFetchBlob = vi.hoisted(() => vi.fn());
vi.mock("@/lib/client-api", () => ({
  apiFetchBlob,
  apiFetch: vi.fn(),
  ApiError: class extends Error {},
}));

describe("AttachmentGallery", () => {
  beforeEach(() => {
    apiFetchBlob.mockReset();
    apiFetchBlob.mockResolvedValue(new Blob(["bytes"], { type: "image/jpeg" }));
    global.URL.createObjectURL = vi.fn().mockReturnValue("blob:fake");
    global.URL.revokeObjectURL = vi.fn();
  });

  it("fetches media with the access token rather than as a bare <img src>", async () => {
    // The endpoints are participant-only: a plain media request carries no
    // Authorization header and comes back 401.
    const attachment = makeAttachment();
    render(<AttachmentGallery attachments={[attachment]} mine={false} />);

    await waitFor(() => expect(apiFetchBlob).toHaveBeenCalledWith(attachment.poster_url));
  });

  it("shows the thumbnail in the bubble, not the full image", async () => {
    const attachment = makeAttachment({
      url: "/full/",
      poster_url: "/thumb/",
    });
    render(<AttachmentGallery attachments={[attachment]} mine={false} />);

    await waitFor(() => expect(apiFetchBlob).toHaveBeenCalledWith("/thumb/"));
    expect(apiFetchBlob).not.toHaveBeenCalledWith("/full/");
  });

  it("loads the full image only when one is opened", async () => {
    const attachment = makeAttachment({ url: "/full/", poster_url: "/thumb/" });
    render(<AttachmentGallery attachments={[attachment]} mine={false} />);

    await screen.findByRole("img");
    await userEvent.click(screen.getByRole("button"));

    await waitFor(() => expect(apiFetchBlob).toHaveBeenCalledWith("/full/"));
    expect(screen.getByRole("dialog", { name: /image en grand/i })).toBeInTheDocument();
  });

  it("shows a video as a poster with a play control, never the file itself", async () => {
    const attachment = makeAttachment({
      kind: "video",
      duration: 34,
      url: "/video/",
      poster_url: "/poster/",
    });
    const { container } = render(<AttachmentGallery attachments={[attachment]} mine={false} />);

    await waitFor(() => expect(apiFetchBlob).toHaveBeenCalledWith("/poster/"));
    // Nothing of the video is downloaded until someone presses play.
    expect(apiFetchBlob).not.toHaveBeenCalledWith("/video/");
    expect(container.querySelector("video")).toBeNull();
    expect(screen.getByRole("button", { name: /lire la vidéo/i })).toBeInTheDocument();
    expect(screen.getByText("0:34")).toBeInTheDocument();
  });

  it("fetches the video only on play", async () => {
    const attachment = makeAttachment({ kind: "video", url: "/video/", poster_url: "/poster/" });
    render(<AttachmentGallery attachments={[attachment]} mine={false} />);

    await userEvent.click(screen.getByRole("button", { name: /lire la vidéo/i }));

    await waitFor(() => expect(apiFetchBlob).toHaveBeenCalledWith("/video/"));
  });

  it("says so instead of showing a broken frame when media cannot be loaded", async () => {
    apiFetchBlob.mockRejectedValue(new Error("403"));
    render(<AttachmentGallery attachments={[makeAttachment()]} mine={false} />);

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(/indisponible/i));
  });

  it("lays several photos out as a grid", async () => {
    const attachments = [
      makeAttachment({ id: 1 }),
      makeAttachment({ id: 2 }),
      makeAttachment({ id: 3 }),
    ];
    render(<AttachmentGallery attachments={attachments} mine={false} />);

    await waitFor(() => expect(screen.getAllByRole("img")).toHaveLength(3));
  });

  it("renders nothing when a message has no media", () => {
    const { container } = render(<AttachmentGallery attachments={[]} mine={false} />);
    expect(container).toBeEmptyDOMElement();
  });
});
