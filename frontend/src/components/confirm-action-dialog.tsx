"use client";

import { ConfirmationDialog } from "@/components/ui/overlay";

export function ConfirmActionDialog({ title, description, actionLabel, isSubmitting = false, error, onCancel, onConfirm }: { title: string; description: string; actionLabel: string; isSubmitting?: boolean; error?: string | null; onCancel: () => void; onConfirm: () => void }) {
  return <ConfirmationDialog open title={title} description={description} actionLabel={actionLabel} isSubmitting={isSubmitting} error={error} onCancel={onCancel} onConfirm={onConfirm} />;
}
