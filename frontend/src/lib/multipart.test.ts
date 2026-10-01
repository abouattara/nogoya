import { describe, expect, it } from "vitest";

import { encodeFormData } from "@/lib/multipart";

async function read(body: Blob) {
  return new Uint8Array(await body.arrayBuffer()).reduce(
    (text, byte) => text + String.fromCharCode(byte),
    ""
  );
}

describe("encodeFormData", () => {
  it("produit un corps multipart que Django sait relire", async () => {
    const form = new FormData();
    form.append("title", "Tente de réception");
    form.append("images", new File([new Uint8Array([1, 2, 3])], "photo.jpg", { type: "image/jpeg" }));

    const { body, boundary } = encodeFormData(form);
    const text = await read(body);

    expect(boundary).toMatch(/^nogoya[0-9a-f]{32}$/);
    expect(text).toContain('Content-Disposition: form-data; name="title"');
    expect(text).toContain(
      'Content-Disposition: form-data; name="images"; filename="photo.jpg"'
    );
    expect(text).toContain("Content-Type: image/jpeg");
    expect(text.endsWith(`--${boundary}--\r\n`)).toBe(true);
  });

  it("encode les champs texte en UTF-8", async () => {
    const form = new FormData();
    form.append("city", "Ouagadougou — Tampouy");
    const text = await read(encodeFormData(form).body);
    // Le tiret cadratin occupe trois octets en UTF-8, pas un seul.
    expect(text).toContain("\xe2\x80\x94");
  });

  it("neutralise un nom de fichier qui fabriquerait une pièce supplémentaire", async () => {
    const hostile = 'evil";\r\nContent-Disposition: form-data; name="admin';
    const form = new FormData();
    form.append("images", new File([new Uint8Array([0])], hostile, { type: "image/jpeg" }));

    const { body, boundary } = encodeFormData(form);
    const text = await read(body);

    // Une seule pièce : la frontière n'apparaît que deux fois, à l'ouverture
    // et à la clôture. Guillemets et sauts de ligne ont été échappés.
    expect(text.split(`--${boundary}`)).toHaveLength(3);
    expect(text).toContain("%22");
    expect(text).toContain("%0D%0A");
    expect(text).not.toContain(hostile);
  });

  it("donne une frontière différente à chaque envoi", () => {
    const a = encodeFormData(new FormData()).boundary;
    const b = encodeFormData(new FormData()).boundary;
    expect(a).not.toBe(b);
  });
});
