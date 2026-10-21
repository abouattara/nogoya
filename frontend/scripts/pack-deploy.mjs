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
 *    s'affiche. On retire les variantes étrangères à la cible et on
 *    télécharge celle de la cible (`npm pack`, qui ignore la plateforme de
 *    l'hôte, là où `npm install` ne retient que les siennes).
 * 3. La `package.json` recopiée liste *toutes* les dépendances, y compris
 *    Playwright et Vitest. On la remplace par une version **sans
 *    dépendances du tout** : le bundle est complet, il n'y a rien à
 *    installer sur le serveur.
 *
 * Cette dernière décision a été payée cher. La version précédente déclarait
 * `{"dependencies": {"sharp": "..."}}` et la procédure finissait par
 * `npm install`. npm considérait alors `next`, `react` et `react-dom` —
 * présents dans node_modules mais absents des dépendances déclarées —
 * comme superflus, et les **supprimait**. L'application ne démarrait plus
 * et tout le site répondait 503. Mesuré : 11 paquets avant, 7 après.
 *
 * Règle qui en découle : **jamais de `npm install` sur le serveur.** Si une
 * dépendance manque à l'exécution, c'est ici qu'il faut la faire entrer.
 *
 * Usage : npm run deploy:pack
 */
import { cp, mkdir, readFile, rm, writeFile, readdir } from "node:fs/promises";
import { existsSync } from "node:fs";
import { execFileSync } from "node:child_process";
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

  // 4. récupérer le binaire natif de la cible
  const fetched = await fetchPlatformBinaries(imgDir);

  // 5. une package.json qui ne décrit que l'exécution
  const source = JSON.parse(await readFile(path.join(ROOT, "package.json"), "utf8"));
  await writeFile(
    path.join(OUT, "package.json"),
    JSON.stringify(
      {
        name: "nogoya-frontend",
        version: source.version,
        private: true,
        scripts: { start: "node server.js" },
        // Volontairement SANS `dependencies`. Le bundle est complet : tout
        // node_modules est là, binaire natif compris. Déclarer `sharp` ici
        // était un piège — un `npm install` sur le serveur considérait
        // alors `next`, `react` et `react-dom` comme superflus et les
        // SUPPRIMAIT, laissant une application incapable de démarrer et un
        // 503 sur tout le site. Vérifié : 11 paquets avant, 7 après.
        //
        // Il n'y a donc rien à installer sur le serveur. Si un jour une
        // dépendance manque, c'est le bundle qu'il faut corriger, pas un
        // `npm install` qu'il faut ajouter.
      },
      null,
      2
    ) + "\n"
  );

  console.log(`Dossier prêt : ${path.relative(process.cwd(), OUT)}`);
  if (removed.length) {
    console.log(`Variantes natives retirées (cible ${KEEP_PLATFORM}) : ${removed.join(", ")}`);
  }
  console.log(`Binaires natifs ajoutés : ${fetched.join(", ") || "(aucun)"}`);
  console.log("Sur le serveur : extraire et redémarrer. Pas de `npm install`.");
}

/**
 * Télécharge les paquets natifs de la plateforme cible.
 *
 * `npm install` ne les récupère pas depuis une machine Windows : npm ne
 * retient que les dépendances optionnelles correspondant à l'hôte. Mais
 * `npm pack` télécharge l'archive d'un paquet quelle que soit la
 * plateforme — on l'extrait nous-mêmes au bon endroit.
 */
/** GNU tar sous Windows veut des barres obliques, pas des antislashs. */
function posix(p) {
  return p.split(path.sep).join("/");
}

async function fetchPlatformBinaries(imgDir) {
  const sharpManifest = path.join(STANDALONE, "node_modules", "sharp", "package.json");
  if (!existsSync(sharpManifest)) return [];

  const { optionalDependencies = {} } = JSON.parse(await readFile(sharpManifest, "utf8"));
  const wanted = Object.entries(optionalDependencies).filter(([name]) =>
    name.includes(KEEP_PLATFORM)
  );
  if (!wanted.length) return [];

  await mkdir(imgDir, { recursive: true });
  const staging = path.join(OUT, ".platform-staging");
  await mkdir(staging, { recursive: true });

  const added = [];
  for (const [name, version] of wanted) {
    const shortName = name.split("/").pop();
    const target = path.join(imgDir, shortName);
    if (existsSync(target)) continue;

    // On lit le nom sur la sortie de `npm pack` plutôt que de le deviner :
    // pour un paquet « scoped », npm aplatit le nom en remplaçant « @ » et
    // « / », si bien que @img/sharp-libvips-linux-x64 ressort en
    // « img-sharp-libvips-linux-x64-1.3.3.tgz ». Le deviner avait produit
    // une recherche qui ne trouvait rien.
    const output = execFileSync(
      "npm",
      ["pack", `${name}@${version}`, "--pack-destination", staging],
      { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"], shell: process.platform === "win32" }
    );
    const archive = output.trim().split(/\r?\n/).pop();
    if (!archive || !archive.endsWith(".tgz")) {
      throw new Error(`Archive introuvable pour ${name}@${version} (npm a répondu « ${output.trim()} »)`);
    }

    await mkdir(target, { recursive: true });
    // L'archive npm range tout sous « package/ » : on retire ce niveau.
    //
    // Chemins en barres obliques et `--force-local` : GNU tar lit
    // « C:\dossier » comme l'hôte distant « C », et répond « Child returned
    // status 128 » sans jamais nommer la vraie cause.
    execFileSync(
      "tar",
      [
        "--force-local",
        "-xzf",
        posix(path.join(staging, archive)),
        "-C",
        posix(target),
        "--strip-components=1",
      ],
      { stdio: "pipe", shell: process.platform === "win32" }
    );

    // Une extraction muette qui ne produit rien laisserait un dossier vide
    // dans le bundle, et l'erreur n'apparaîtrait qu'en production.
    if ((await readdir(target)).length === 0) {
      await rm(target, { recursive: true, force: true });
      throw new Error(`Extraction vide pour ${name}@${version}`);
    }
    added.push(`${name}@${version}`);
  }

  await rm(staging, { recursive: true, force: true });
  return added;
}

await main();
