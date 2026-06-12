import { Tag } from "@/types/crm-completion";

export function TagBadge({ tag }: { tag: Tag }) {
  return <span className="rounded-full px-3 py-1 text-xs font-semibold text-white" style={{ backgroundColor: tag.color }}>{tag.name}</span>;
}
