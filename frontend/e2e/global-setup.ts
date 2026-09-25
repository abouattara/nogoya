import { execFileSync } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";

/**
 * Puts the demo data back before the suite runs.
 *
 * The tests edit listings, and editing sends a listing back to moderation —
 * so after a few runs the supplier had nothing approved left and
 * "publier / dépublier" quietly turned into a skip. A test that skips every
 * time is not coverage, so the suite restores its own fixtures instead of
 * relying on someone remembering to reseed.
 *
 * Failures here are only warned about: the tests themselves report the real
 * problem (an unreachable API) far more clearly than a setup stack trace.
 */
export default function globalSetup() {
  if (process.env.E2E_SKIP_SEED === "1") return;

  const backend = path.resolve(__dirname, "..", "..", "backend");
  const venv = path.join(
    backend,
    ".venv",
    process.platform === "win32" ? "Scripts/python.exe" : "bin/python"
  );
  const python = existsSync(venv) ? venv : "python";

  run(python, backend, ["manage.py", "seed_demo"]);
  // Each run publishes a "Berline E2E …" listing; drop the previous ones.
  run(python, backend, [
    "manage.py",
    "shell",
    "-c",
    "from apps.catalog.models import Product;"
    + "Product.objects.filter(title__startswith='Berline E2E').delete()",
  ]);
}

function run(python: string, cwd: string, args: string[]) {
  try {
    execFileSync(python, args, { cwd, stdio: "pipe" });
  } catch (error) {
    console.warn(`[e2e] setup step failed (${args[1]}):`, (error as Error).message);
  }
}
