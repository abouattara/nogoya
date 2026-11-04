/**
 * Les pictogrammes du chat, dessines ici plutot qu'importes.
 *
 * Les emoji qui servaient de boutons (+, 🎙️) changent de dessin selon le
 * systeme, ne prennent pas la couleur du theme et se lisent mal en petit.
 * Six traits de SVG coutent moins qu'une dependance et restent nets.
 *
 * Tous sont `aria-hidden` : l'intitule du bouton est porte par son
 * `aria-label`, sinon un lecteur d'ecran annoncerait la chose deux fois.
 */

type IconProps = { className?: string };

function base(className?: string) {
  return {
    viewBox: "0 0 24 24",
    fill: "none" as const,
    stroke: "currentColor",
    strokeWidth: 1.75,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
    className: className ?? "h-5 w-5",
  };
}

export function PaperclipIcon({ className }: IconProps) {
  return (
    <svg {...base(className)}>
      <path d="M21.44 11.05 12.25 20.24a6 6 0 0 1-8.49-8.49l9.2-9.19a4 4 0 0 1 5.65 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
    </svg>
  );
}

export function MicIcon({ className }: IconProps) {
  return (
    <svg {...base(className)}>
      <rect x="9" y="2" width="6" height="11" rx="3" />
      <path d="M5 10a7 7 0 0 0 14 0M12 17v5M8 22h8" />
    </svg>
  );
}

export function SendIcon({ className }: IconProps) {
  return (
    <svg {...base(className)}>
      <path d="m3 11 18-8-8 18-2.5-7.5L3 11Z" />
    </svg>
  );
}

export function BackIcon({ className }: IconProps) {
  return (
    <svg {...base(className)}>
      <path d="M19 12H5m0 0 6-6m-6 6 6 6" />
    </svg>
  );
}

export function CheckIcon({ className }: IconProps) {
  return (
    <svg {...base(className)}>
      <path d="m2 13 4 4L13 7" />
      <path d="m11 17 7-10" />
    </svg>
  );
}
