import type { RentalPeriod } from "./types";

export function formatPrice(price: string | number, currency: string) {
  const value = typeof price === "string" ? Number(price) : price;
  return new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 }).format(value) + " " + currency;
}

const RENTAL_LABELS: Record<RentalPeriod, string> = {
  hour: "heure",
  day: "jour",
  week: "semaine",
  month: "mois",
  none: "",
};

export function rentalPeriodLabel(period: RentalPeriod) {
  return RENTAL_LABELS[period] ?? "";
}

export function formatDate(iso: string) {
  return new Intl.DateTimeFormat("fr-FR", { day: "numeric", month: "long", year: "numeric" }).format(new Date(iso));
}

export function formatShortDate(iso: string) {
  return new Intl.DateTimeFormat("fr-FR", { day: "2-digit", month: "2-digit" }).format(new Date(iso));
}

/** "il y a 5 min", "il y a 2 h"... for notification and chat timestamps. */
export function formatRelativeTime(iso: string, now: Date = new Date()) {
  const seconds = Math.round((now.getTime() - new Date(iso).getTime()) / 1000);
  if (seconds < 60) return "à l'instant";

  const units: Array<[Intl.RelativeTimeFormatUnit, number]> = [
    ["minute", 60],
    ["hour", 3600],
    ["day", 86400],
    ["month", 2592000],
    ["year", 31536000],
  ];
  const formatter = new Intl.RelativeTimeFormat("fr-FR", { numeric: "auto" });
  let chosen: [Intl.RelativeTimeFormatUnit, number] = units[0];
  for (const unit of units) {
    if (seconds >= unit[1]) chosen = unit;
  }
  return formatter.format(-Math.floor(seconds / chosen[1]), chosen[0]);
}

/** 78 -> "1:18" for voice message durations. */
export function formatDuration(totalSeconds: number) {
  const safe = Math.max(0, Math.floor(totalSeconds || 0));
  const minutes = Math.floor(safe / 60);
  const seconds = safe % 60;
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
}
