export const ENTITY_TYPE_COLORS = {
  person: '#FF6B6B',
  organization: '#4ECDC4',
  location: '#45B7D1',
  geo: '#45B7D1',
  event: '#96CEB4',
  category: '#FFEAA7',
  equipment: '#DDA0DD',
  athlete: '#FF7675',
  record: '#FD79A8',
  year: '#FDCB6E',
  unknown: '#B2BEC3'
};

export function normalizeEntityType(entityType) {
  const raw = (entityType ?? '').toString().trim();
  if (!raw) return 'unknown';
  const lowered = raw.toLowerCase();
  if (lowered === 'unknown') return 'unknown';
  return lowered;
}

export function getEntityTypeColor(entityType) {
  const normalized = normalizeEntityType(entityType);
  return ENTITY_TYPE_COLORS[normalized] || ENTITY_TYPE_COLORS.unknown;
}

