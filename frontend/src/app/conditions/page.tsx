import type { Metadata } from "next";
import Link from "next/link";
import { PREAMBLE, SECTIONS, TERMS_LABEL, type Block } from "@/content/conditions";

export const metadata: Metadata = {
  title: "Conditions et politique d'utilisation",
  description:
    "Comment BINOGOYA fonctionne, ce que deviennent vos données, ce qui est sanctionné, et de quoi chacun répond.",
};

/**
 * Les conditions, à plat et en entier.
 *
 * Pas d'accordéon, pas d'onglets : un texte que l'on doit accepter se
 * lit en entier ou ne se lit pas, et un pliage donne surtout le moyen de
 * ne pas voir la section qui dérange. Le sommaire sert à y revenir, pas
 * à en sauter des bouts.
 *
 * La page est statique et publique. Elle doit rester lisible sans
 * compte, depuis le lien du formulaire d'inscription comme depuis le
 * pied de page, et elle ne dépend d'aucun appel au serveur.
 */
export default function ConditionsPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-10 sm:px-6">
      <header className="border-b border-border pb-6">
        <h1 className="text-3xl font-bold tracking-tight">
          Conditions et politique d&apos;utilisation
        </h1>
        <p className="mt-2 text-sm text-foreground-muted">{TERMS_LABEL}</p>
      </header>

      <div className="mt-6 flex flex-col gap-4">
        {PREAMBLE.map((block, index) => (
          <BlockView key={index} block={block} />
        ))}
      </div>

      <nav aria-label="Sommaire" className="mt-8 rounded-xl border border-border bg-surface-muted p-4">
        <p className="mb-2 text-sm font-semibold">Sommaire</p>
        <ol className="flex flex-col gap-1 text-sm">
          {SECTIONS.map((section) => (
            <li key={section.id}>
              <a
                href={`#${section.id}`}
                className="text-brand-700 underline underline-offset-2 hover:text-brand-800"
              >
                {section.title}
              </a>
            </li>
          ))}
        </ol>
      </nav>

      {SECTIONS.map((section) => (
        <section key={section.id} id={section.id} className="mt-10 scroll-mt-24">
          <h2 className="border-b border-border pb-2 text-xl font-bold">{section.title}</h2>
          <div className="mt-4 flex flex-col gap-4">
            {section.blocks.map((block, index) => (
              <BlockView key={index} block={block} />
            ))}
          </div>
        </section>
      ))}

      <p className="mt-12 border-t border-border pt-6 text-sm text-foreground-muted">
        En créant un compte, vous acceptez ce texte dans la version affichée ci-dessus.{" "}
        <Link href="/register" className="font-medium text-brand-700 underline underline-offset-2">
          Créer un compte
        </Link>
      </p>
    </div>
  );
}

function BlockView({ block }: { block: Block }) {
  switch (block.kind) {
    case "h3":
      return <h3 className="mt-2 text-base font-semibold">{block.text}</h3>;
    case "ul":
      return (
        <ul className="flex list-disc flex-col gap-2 pl-5 text-[0.95rem] leading-relaxed text-foreground">
          {block.items.map((item, index) => (
            <li key={index}>{item}</li>
          ))}
        </ul>
      );
    case "ol":
      return (
        <ol className="flex list-decimal flex-col gap-2 pl-5 text-[0.95rem] leading-relaxed text-foreground">
          {block.items.map((item, index) => (
            <li key={index}>{item}</li>
          ))}
        </ol>
      );
    default:
      return <p className="text-[0.95rem] leading-relaxed text-foreground">{block.text}</p>;
  }
}
