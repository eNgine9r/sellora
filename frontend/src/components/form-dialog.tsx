"use client";

import { ReactNode } from "react";
import { Modal } from "@/components/ui/overlay";

export function FormDialog({ title, description, children, onClose, size = "lg" }: { title: string; description?: string; children: ReactNode; onClose: () => void; size?: "sm" | "md" | "lg" | "xl" }) {
  return <Modal open title={title} description={description} onClose={onClose} size={size}>{children}</Modal>;
}
