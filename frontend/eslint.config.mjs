import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    // Sortie de `npm run deploy:pack` : du code déjà compilé, recopié tel
    // quel. Le lire noyait les vrais avertissements sous 145 erreurs.
    "deploy/**",
  ]),
]);

export default eslintConfig;
