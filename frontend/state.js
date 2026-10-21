// Export only an artifact that belongs to the currently displayed source/settings.
export function currentArtifact({ revision, rendered, busy, last }) {
  return !busy && Boolean(last?.ok) && revision === rendered;
}
export function validSettings({pages,font_size}) {
  return Number.isInteger(pages)&&pages>=1&&pages<=20&&Number.isFinite(font_size)&&font_size>=9&&font_size<=12&&Number.isInteger(font_size*2);
}
