"use client";

import { Archive, Pencil, Trash2 } from "lucide-react";
import { IconButton } from "@/components/ui/primitives";

type RowActionButtonsProps = {
  entityLabel: string;
  editLabel: string;
  archiveLabel: string;
  onEdit?: () => void;
  onArchive?: () => void;
  destructiveIcon?: "archive" | "delete";
};

// Standard desktop table actions: icon-only, one line, independent of entity type.
// Opening details is handled by selecting the row; destructive actions stay confirmed by the page.
export function RowActionButtons({ entityLabel, editLabel, archiveLabel, onEdit, onArchive, destructiveIcon = "archive" }: RowActionButtonsProps) {
  return (
    <div className="flex shrink-0 items-center justify-end gap-1 whitespace-nowrap" onClick={(event) => event.stopPropagation()}>
      {onEdit ? (
        <IconButton type="button" className="h-10 w-10 min-h-10 min-w-10 rounded-lg" variant="ghost" title={editLabel} aria-label={`${editLabel} ${entityLabel}`} onClick={onEdit}>
          <Pencil className="h-4 w-4" aria-hidden="true" />
        </IconButton>
      ) : null}
      {onArchive ? (
        <IconButton type="button" className="h-10 w-10 min-h-10 min-w-10 rounded-lg" variant="danger" title={archiveLabel} aria-label={`${archiveLabel} ${entityLabel}`} onClick={onArchive}>
          {destructiveIcon === "delete" ? <Trash2 className="h-4 w-4" aria-hidden="true" /> : <Archive className="h-4 w-4" aria-hidden="true" />}
        </IconButton>
      ) : null}
      {!onEdit && !onArchive ? <span className="px-2 text-xs text-text-muted">—</span> : null}
    </div>
  );
}
