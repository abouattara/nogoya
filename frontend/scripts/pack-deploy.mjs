/**
 * Assemble le dossier à envoyer sur un hébergement Node (cPanel).
 *
 * `next build --output standalone` produit presque tout, mais trois choses
 * manquent ou gênent pour un déploiement depuis une machine de
 * développement :
 *
 * 1. `.next/static` et `public` ne sont pas copiés par Next — sans eux, le
 *    site s'affiche sans aucun style.
 * 2. Le binaire natif de `sharp` embarqué correspond à la machine qui a
 *    construit. Un build Windows copie `@img/sharp-win32-x64`, inutilisable
 *    sous Linux : `/_next/image` renvoie 500 et plus aucune photo ne
 *    s'affiche. On retire les variantes étrangères à la cible, et un
 *    `npm install` sur le serveur récupère la bonne.
 * 3. La `package.json` recopiée liste *toutes* les dépendances, y compris
 *    Playwright et Vitest. Un `npm install` sur le serveur téléchargerait
 *    des centaines de mégaoctets d'outils de test. On la remplace par le
 *    strict nécessaire à l'exécution.
 *
 * Usage : npm run deploy:pack
 */
import { cp, mkdir, readFile, rm, writeFile, readdir } from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";

const ROOT = path.resolve(import.meta.dirname, "..");
const STANDALONE = path.join(ROOT, ".next", "standalone");
const OUT = path.join(ROOT, "deploy");

/** Variantes conservées : celles de la cible de déploiement. */
const KEEP_PLATFORM = process.env.DEPLOY_PLATFORM ?? "linux-x64";

async function main() {
  if (!existsSync(STANDALONE)) {
    console.error("Pas de .next/standalone — lancez `npm run build` d'abord.");
    process.exitCode = 1;
    return;
  }

  await rm(OUT, { recursive: true, force: true });
  await mkdir(OUT, { recursive: true });

  // 1. le serveur et ses dépendances d'exécution
  await cp(STANDALONE, OUT, { recursive: true });

  // 2. les fichiers statiques, que Next ne copie pas
  await mkdir(path.join(OUT, ".next"), { recursive: true });
  await cp(path.join(ROOT, ".next", "static"), path.join(OUT, ".next", "static"), {
    recursive: true,
  });
  if (existsSync(path.join(ROOT, "public"))) {
    await cp(path.join(ROOT, "public"), path.join(OUT, "public"), { recursive: true });
  }

  // 3. retirer les binaires natifs d'une autre plateforme
  const imgDir = path.join(OUT, "node_modules", "@img");
  let removed = [];
  if (existsSync(imgDir)) {
    for (const entry of await readdir(imgDir)) {
      // Tout ce qui nomme une plateforme : `sharp-win32-x64`,
      // `sharp-libvips-linux-arm64`, mais aussi `sharp-wasm32` — 8,7 Mo de
      // repli WebAssembly qui ne sert à rien quand le binaire natif de la
      // cible est présent. Seul `colour`, commun à toutes, est conservé.
      const isPlatformPackage = /^sharp(-libvips)?-/.test(entry);
      if (isPlatformPackage && !entry.includes(KEEP_PLATFORM)) {
        await rm(path.join(imgDir, entry), { recursive: true, force: true });
        removed.push(entry);
      }
    }
  }

  // 4. une package.json qui ne décrit que l'exécution
  const source = JSON.parse(await readFile(path.join(ROOT, "package.json"), "utf8"));
  await writeFile(
    path.join(OUT, "package.json"),
    JSON.stringify(
      {
        name: "nogoya-frontend",
        version: source.version,
        private: true,
        scripts: { start: "node server.js" },
        // sharp est la seule dépendance à (ré)installer sur le serveur : son
        // binaire dépend de la plateforme. Tout le reste est déjà dans
        // node_modules, figé par le build.
        dependencies: { sharp: await sharpVersion() },
      },
      null,
      2
    ) + "\n"
  );

  console.log(`Dossier prêt : ${path.relative(process.cwd(), OUT)}`);
  if (removed.length) {
    console.log(`Variantes natives retirées (cible ${KEEP_PLATFORM}) : ${removed.join(", ")}`);
  }
  console.log("Sur le serveur : extraire, puis `npm install` et redémarrer.");
}

async function sharpVersion() {
  const file = path.join(STANDALONE, "node_modules", "sharp", "package.json");
  if (!existsSync(file)) return "^0.35.4";
  const { version } = JSON.parse(await readFile(file, "utf8"));
  return version;
}

await main();
