// pubDate llega como medianoche UTC: formatear en UTC evita que en Lima (UTC-5) se muestre el día anterior.
export const formatDate = (d: Date) =>
  d.toLocaleDateString('es-PE', { year: 'numeric', month: 'long', day: 'numeric', timeZone: 'UTC' });

export const readingMinutes = (body: string | undefined) =>
  Math.max(1, Math.round((body ?? '').split(/\s+/).filter(Boolean).length / 200));
