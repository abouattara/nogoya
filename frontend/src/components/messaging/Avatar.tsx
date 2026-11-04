import Image from "next/image";
import clsx from "clsx";

/**
 * La pastille d'identite d'une conversation.
 *
 * Une photo quand il y en a une, l'initiale sinon — jamais un carre vide.
 * La couleur de fond est tiree du nom, pas aleatoire : la meme personne
 * garde la meme teinte d'un ecran a l'autre, ce qui aide a retrouver un
 * fil dans une liste sans lire chaque ligne.
 */

const TONES = [
  "bg-brand-100 text-brand-800",
  "bg-accent-100 text-accent-700",
  "bg-emerald-100 text-emerald-800",
  "bg-amber-100 text-amber-800",
  "bg-sky-100 text-sky-800",
];

function toneFor(name: string) {
  let sum = 0;
  for (const char of name) sum = (sum + char.codePointAt(0)!) % 9973;
  return TONES[sum % TONES.length];
}

export function Avatar({
  name,
  src,
  size = 40,
  className,
}: {
  name: string;
  src?: string | null;
  size?: number;
  className?: string;
}) {
  const label = (name.trim()[0] ?? "?").toUpperCase();

  return (
    <span
      aria-hidden="true"
      style={{ width: size, height: size, fontSize: Math.round(size * 0.4) }}
      className={clsx(
        "relative flex shrink-0 select-none items-center justify-center overflow-hidden rounded-full font-semibold",
        src ? "bg-surface-muted" : toneFor(name),
        className
      )}
    >
      {src ? <Image src={src} alt="" fill sizes={`${size}px`} className="object-cover" /> : label}
    </span>
  );
}
