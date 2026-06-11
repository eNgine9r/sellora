const UUID_PATTERN = /^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$/;

export function normalizeWorkspaceId(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const workspaceId = value.trim();
  if (!workspaceId) return null;
  if (workspaceId.includes(",")) return null;
  if (workspaceId.toLowerCase() === "undefined" || workspaceId.toLowerCase() === "null") return null;
  return UUID_PATTERN.test(workspaceId) ? workspaceId : null;
}

export function isValidUuid(value: unknown): value is string {
  return normalizeWorkspaceId(value) !== null;
}
