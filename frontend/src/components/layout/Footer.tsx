export function Footer() {
  return (
    <footer className="mt-16 border-t border-border py-8 text-sm text-foreground-muted">
      <div className="mx-auto flex max-w-7xl flex-col gap-2 px-4 sm:px-6">
        <p>© {new Date().getFullYear()} nogoya — la marketplace de location et de vente entre particuliers et professionnels.</p>
      </div>
    </footer>
  );
}
