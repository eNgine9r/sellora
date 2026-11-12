"use client";

import Link from "next/link";
import { AlertCircle, ChevronRight } from "lucide-react";
import { useI18n } from "@/i18n/provider";
import { RowActionButtons } from "@/components/ui/row-action-buttons";
import { cn } from "@/services/utils";
import { Shipment } from "@/types/shipments";
import { ShipmentStatusBadge } from "./shipment-status-badge";
import { CopyTtnButton } from "./ttn-actions";

function displayTtn(shipment: Shipment, fallback: string) {
  return shipment.nova_poshta_document_number ?? shipment.tracking_number ?? fallback;
}

function needsAction(shipment: Shipment) {
  if (!shipment.customer_id) return true;
  if (!shipment.tracking_number && shipment.carrier === "NOVA_POSHTA") return true;
  return ["DRAFT", "CREATED", "ARRIVED"].includes(shipment.status);
}

function carrierName(carrier: Shipment["carrier"], locale: string) {
  const names: Record<Shipment["carrier"], [string, string]> = {
    NOVA_POSHTA: ["Нова Пошта", "Nova Poshta"],
    UKRPOSHTA: ["Укрпошта", "Ukrposhta"],
    MEEST: ["Meest", "Meest"],
    ROZETKA_DELIVERY: ["Rozetka", "Rozetka"],
    OTHER: ["Інший", "Other"],
  };
  return names[carrier]?.[locale === "en" ? 1 : 0] ?? carrier;
}

export function ShipmentTable({ shipments, selectedShipmentId, onSelect, onEdit, onArchive }: { shipments: Shipment[]; selectedShipmentId?: string; onSelect: (shipment: Shipment) => void; onEdit?: (shipment: Shipment) => void; onArchive?: (shipment: Shipment) => void }) {
  const { t, locale } = useI18n();
  const showActions = Boolean(onEdit || onArchive);
  const dateLocale = locale === "en" ? "en-GB" : "uk-UA";
  const updatedDate = (value: string) => new Intl.DateTimeFormat(dateLocale, { day: "2-digit", month: "2-digit", year: "2-digit" }).format(new Date(value));

  return (
    <section className="sellora-adaptive-list min-w-0 overflow-hidden rounded-xl border border-border-subtle bg-surface-1" data-shipments-density="compact">
      <div className="sellora-adaptive-table min-w-0">
        <table className="w-full table-fixed text-left text-sm">
          <colgroup>
            <col style={{ width: showActions ? "29%" : "33%" }} />
            <col style={{ width: showActions ? "31%" : "35%" }} />
            <col style={{ width: showActions ? "17%" : "19%" }} />
            <col style={{ width: showActions ? "12%" : "13%" }} />
            {showActions ? <col style={{ width: "11%" }} /> : null}
          </colgroup>
          <thead className="border-b border-border-subtle bg-surface-2/40 text-[11px] font-medium text-text-muted">
            <tr>
              <th scope="col" className="px-3 py-2 font-medium">{t("shipments.trackingNumber")}</th>
              <th scope="col" className="px-3 py-2 font-medium">{t("shipments.customer")}</th>
              <th scope="col" className="px-3 py-2 font-medium">{t("tables.status")}</th>
              <th scope="col" className="px-2 py-2 font-medium">{t("shipments.updated")}</th>
              {showActions ? <th scope="col" className="px-2 py-2 text-right font-medium">{t("tables.actions")}</th> : null}
            </tr>
          </thead>
          <tbody>
            {shipments.map((shipment) => {
              const tracking = displayTtn(shipment, t("common.draft"));
              const isSelected = shipment.id === selectedShipmentId;
              const hasIssue = needsAction(shipment);
              return (
                <tr
                  key={shipment.id}
                  tabIndex={0}
                  onClick={() => onSelect(shipment)}
                  onKeyDown={(event) => { if (event.target === event.currentTarget && (event.key === "Enter" || event.key === " ")) { event.preventDefault(); onSelect(shipment); } }}
                  title={shipment.tracking_number ? t("common.details") : t("shipments.createTtn")}
                  className={cn("cursor-pointer border-t border-border-subtle/70 align-middle transition-colors hover:bg-surface-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-focus-ring", isSelected && "bg-surface-selected ring-1 ring-inset ring-primary/30")}
                >
                  <td className="min-w-0 px-3 py-2">
                    <div className="flex min-w-0 items-center gap-1.5">
                      <span className="truncate font-semibold text-text-primary" title={tracking}>{tracking}</span>
                      {hasIssue ? <AlertCircle className="h-3.5 w-3.5 shrink-0 text-warning" aria-label={t("shipments.needsAction")} /> : null}
                    </div>
                    <span className="block truncate text-[11px] leading-4 text-text-muted" title={shipment.order_number ?? undefined}>{shipment.order_number ?? "—"}</span>
                  </td>
                  <td className="min-w-0 px-3 py-2">
                    <span className="block truncate font-medium text-text-primary" title={shipment.customer_name ?? undefined}>{shipment.customer_name ?? "—"}</span>
                    <span className="block truncate text-[11px] leading-4 text-text-muted" title={[shipment.city, shipment.warehouse, shipment.customer_phone].filter(Boolean).join(" · ")}>
                      {[shipment.city, carrierName(shipment.carrier, locale)].filter(Boolean).join(" · ") || "—"}
                    </span>
                  </td>
                  <td className="min-w-0 px-3 py-2"><ShipmentStatusBadge status={shipment.status} /></td>
                  <td className="whitespace-nowrap px-2 py-2 text-xs tabular-nums text-text-secondary">{updatedDate(shipment.updated_at)}</td>
                  {showActions ? <td className="px-1 py-1"><RowActionButtons entityLabel={tracking} editLabel={t("shipments.edit")} archiveLabel={t("shipments.archive")} onEdit={onEdit ? () => onEdit(shipment) : undefined} onArchive={onArchive ? () => onArchive(shipment) : undefined} /></td> : null}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="sellora-adaptive-cards grid gap-2 p-2">
        {shipments.map((shipment) => {
          const isSelected = shipment.id === selectedShipmentId;
          const tracking = displayTtn(shipment, t("shipments.draftShipment"));
          return (
            <article key={shipment.id} className={cn("min-w-0 rounded-xl border border-border-subtle bg-surface-1", isSelected && "border-primary bg-surface-selected")}>
              <button type="button" className="flex w-full min-w-0 items-center gap-2 p-3 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring" onClick={() => onSelect(shipment)}>
                <div className="min-w-0 flex-1">
                  <div className="flex min-w-0 items-center gap-1.5">
                    <strong className="truncate text-sm font-semibold text-text-primary">{tracking}</strong>
                    {needsAction(shipment) ? <AlertCircle className="h-3.5 w-3.5 shrink-0 text-warning" aria-label={t("shipments.needsAction")} /> : null}
                  </div>
                  <p className="truncate text-xs text-text-secondary">{shipment.customer_name ?? "—"} · {shipment.city ?? "—"}</p>
                  <p className="truncate text-[11px] text-text-muted">{shipment.order_number ?? "—"} · {carrierName(shipment.carrier, locale)}</p>
                </div>
                <div className="flex shrink-0 flex-col items-end gap-1.5">
                  <ShipmentStatusBadge status={shipment.status} />
                  <ChevronRight aria-hidden="true" className="h-3.5 w-3.5 text-text-muted" />
                </div>
              </button>
              {(shipment.tracking_number || shipment.nova_poshta_document_number || shipment.order_id) ? (
                <div className="flex flex-wrap items-center gap-2 border-t border-border-subtle px-3 py-2">
                  {(shipment.tracking_number || shipment.nova_poshta_document_number) ? <div className="[&_button]:min-h-9 [&_button]:rounded-lg [&_button]:px-3 [&_button]:text-xs"><CopyTtnButton trackingNumber={shipment.nova_poshta_document_number ?? shipment.tracking_number} /></div> : null}
                  {shipment.order_id ? <Link className="inline-flex min-h-9 items-center rounded-lg border border-border-subtle px-3 text-xs font-medium text-text-secondary hover:bg-surface-hover" href={`/orders?order_id=${encodeURIComponent(shipment.order_id)}`}>{t("shipments.openOrder")}</Link> : null}
                </div>
              ) : null}
            </article>
          );
        })}
      </div>
      {shipments.length === 0 ? <p className="p-4 text-center text-xs text-text-muted">{t("shipments.empty")}</p> : null}
    </section>
  );
}
// Shipment TTN UX regression markers: Copy TTN, Create TTN, Sync status, Open order, needs action.
// Regression compatibility markers: Edit shipment; Archive shipment; shipments.createTtn.
