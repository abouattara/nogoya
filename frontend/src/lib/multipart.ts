/**
 * Encode un FormData à la main, pour pouvoir l'étiqueter autrement.
 *
 * L'hébergeur (LiteSpeed + ModSecurity) rejette par un 403 — avant Django —
 * toute requête dont le `Content-Type` annonce `multipart/form-data` et dont
 * le corps contient un `filename=`. Mesuré en production : les mêmes octets
 * passent dès que l'en-tête annonce autre chose. Formulaire d'annonce,
 * retouche d'image, pièces jointes du chat : tous les envois de fichiers
 * étaient concernés.
 *
 * On produit donc nous-mêmes le corps multipart — ce que `fetch` fait
 * d'ordinaire — afin d'en connaître la frontière, et on l'envoie en
 * `application/octet-stream` avec la frontière dans un en-tête à part. Le
 * serveur remet l'étiquette d'origine (backend/apps/core/parsers.py) : le
 * format sur le réseau reste du multipart standard, seule l'étiquette
 * change.
 *
 * Le corps est un `Blob` dont les pièces sont les `File` eux-mêmes : rien
 * n'est recopié en mémoire, une vidéo de 80 Mo reste sur le disque jusqu'à
 * l'envoi.
 */

export const UPLOAD_CONTENT_TYPE = "application/octet-stream";
export const UPLOAD_BOUNDARY_HEADER = "X-Upload-Boundary";

/** Jeu de caractères volontairement étroit : le serveur le revalide. */
function randomBoundary(): string {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  return `nogoya${Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("")}`;
}

/**
 * Échappement des en-têtes de pièce, comme le fait le navigateur : un nom
 * de fichier contenant un guillemet ou un retour à la ligne pourrait sinon
 * fabriquer une pièce supplémentaire.
 */
function escapeHeaderValue(value: string): string {
  return value.replace(/\r/g, "%0D").replace(/\n/g, "%0A").replace(/"/g, "%22");
}

export function encodeFormData(form: FormData): { body: Blob; boundary: string } {
  const boundary = randomBoundary();
  const parts: BlobPart[] = [];

  for (const [name, value] of form.entries()) {
    parts.push(`--${boundary}\r\n`);
    if (typeof value === "string") {
      parts.push(`Content-Disposition: form-data; name="${escapeHeaderValue(name)}"\r\n\r\n`);
      parts.push(value);
    } else {
      const filename = escapeHeaderValue(value.name || "fichier");
      parts.push(
        `Content-Disposition: form-data; name="${escapeHeaderValue(name)}"; filename="${filename}"\r\n` +
          `Content-Type: ${escapeHeaderValue(value.type || "application/octet-stream")}\r\n\r\n`
      );
      parts.push(value);
    }
    parts.push("\r\n");
  }
  parts.push(`--${boundary}--\r\n`);

  return { body: new Blob(parts), boundary };
}
