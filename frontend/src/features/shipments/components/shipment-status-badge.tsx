"use client";

import { useI18n } from "@/i18n/provider";
import { statusBadgeClass, StatusTone } from "@/lib/status-styles";
import { ShipmentStatus } from "@/types/shipments";

const STATUS_TONES: Record<ShipmentStatus, StatusTone> = { DRAFT: "neutral", CREATED: "info", IN_TRANSIT: "violet", ARRIVED: "warning", DELIVERED: "success", RETURNED: "danger", CANCELLED: "neutral" };

export function ShipmentStatusBadge({ status }: { status: ShipmentStatus }) {
  const { formatStatus } = useI18n();
  return <span className={statusBadgeClass(STATUS_TONES[status])}>{formatStatus("shipment", status)}</span>;
}
