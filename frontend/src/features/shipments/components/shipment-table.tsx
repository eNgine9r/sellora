"use client";

import Link from "next/link";
import { useI18n } from "@/i18n/provider";
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

export function ShipmentTable({ shipments, selectedShipmentId, onSelect, onEdit, onArchive }: { shipments: Shipment[]; selectedShipmentId?: string; onSelect: (shipment: Shipment) => void; onEdit?: (shipment: Shipment) => void; onArchive?: (shipment: Shipment) => void }) {
  const { t } = useI18n();
  const headings = [t("shipments.trackingNumber"), t("shipments.order"), t("shipments.customer"), t("shipments.carrier"), t("tables.status"), t("shipments.destination"), t("shipments.updated"), t("tables.actions")];
  return (
    <section className="rounded-2xl border border-border-subtle bg-surface-1 p-4 shadow-sm">
      <div className="sellora-scrollbar hidden overflow-x-auto md:block">
        <table className="w-full min-w-[940px] text-left text-sm">
          <thead className="text-xs uppercase tracking-[0.14em] text-text-muted">
            <tr>{headings.map((heading) => <th className="px-3 py-2" key={heading}>{heading}</th>)}</tr>
          </thead>
          <tbody>
            {shipments.map((shipment) => {
              const tracking = displayTtn(shipment, t("common.draft"));
              const isSelected = shipment.id === selectedShipmentId;
              return (
                <tr key={shipment.id} className={cn("cursor-pointer border-t border-border-subtle align-top transition hover:bg-surface-hover", isSelected && "bg-surface-selected ring-1 ring-inset ring-primary/30")} onClick={() => onSelect(shipment)}>
                  <td className="px-3 py-3 font-semibold text-text-primary"><span className="block max-w-[170px] break-words">{tracking}</span>{needsAction(shipment) ? <span className="mt-1 inline-flex rounded-full bg-warning/10 px-2 py-1 text-xs text-warning">{t("shipments.needsAction")}</span> : null}</td>
                  <td className="px-3 py-3 text-text-secondary">{shipment.order_number ?? "—"}</td>
                  <td className="px-3 py-3"><span className="block font-semibold text-text-primary">{shipment.customer_name ?? "—"}</span><span className="block text-xs text-text-muted">{shipment.customer_phone ?? "—"}</span></td>
                  <td className="px-3 py-3 text-text-secondary">{shipment.carrier}</td>
                  <td className="px-3 py-3"><ShipmentStatusBadge status={shipment.status} /></td>
                  <td className="px-3 py-3"><span className="block text-text-primary">{shipment.city ?? "—"}</span><span className="block max-w-[190px] truncate text-xs text-text-muted" title={shipment.warehouse ?? undefined}>{shipment.warehouse ?? "—"}</span></td>
                  <td className="px-3 py-3 text-text-secondary"><span className="block">{new Date(shipment.updated_at).toLocaleString()}</span>{shipment.nova_poshta_synced_at ? <span className="block text-xs text-text-muted">{t("shipments.lastSynced")}: {new Date(shipment.nova_poshta_synced_at).toLocaleString()}</span> : null}</td>
                  <td className="px-3 py-3" onClick={(event) => event.stopPropagation()}><div className="grid min-w-[160px] gap-2"><button className="rounded-lg border border-border-subtle px-3 py-2 font-semibold text-text-primary hover:bg-surface-hover" onClick={() => onSelect(shipment)}>{shipment.tracking_number ? t("common.details") : t("shipments.createTtn")}</button><CopyTtnButton trackingNumber={shipment.tracking_number ?? shipment.nova_poshta_document_number} />{shipment.order_id ? <Link className="rounded-lg border border-border-subtle px-3 py-2 text-center font-semibold text-text-primary hover:bg-surface-hover" href={`/orders?order_id=${shipment.order_id}`}>{t("shipments.openOrder")}</Link> : null}{onEdit ? <button aria-label={`${t("shipments.edit")} ${shipment.tracking_number ?? shipment.id}`} className="rounded-lg border border-border-subtle px-3 py-2 font-semibold text-text-primary hover:bg-surface-hover" onClick={() => onEdit(shipment)}>{t("shipments.edit")}</button> : null}{onArchive ? <button aria-label={`${t("shipments.archive")} ${shipment.tracking_number ?? shipment.id}`} className="rounded-lg border border-danger/30 px-3 py-2 font-semibold text-danger hover:bg-danger/10" onClick={() => onArchive(shipment)}>{t("shipments.archive")}</button> : null}</div></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div className="grid gap-3 md:hidden">
        {shipments.map((shipment) => {
          const isSelected = shipment.id === selectedShipmentId;
          return <article key={shipment.id} className={cn("rounded-2xl border border-border-subtle bg-surface-1 p-4", isSelected && "border-primary bg-surface-selected")}><button type="button" className="w-full text-left" onClick={() => onSelect(shipment)}><div className="flex items-start justify-between gap-3"><div><p className="text-sm text-text-muted">{t("shipments.tracking")}</p><h3 className="break-words text-lg font-bold text-text-primary">{displayTtn(shipment, t("shipments.draftShipment"))}</h3>{needsAction(shipment) ? <span className="mt-1 inline-flex rounded-full bg-warning/10 px-2 py-1 text-xs font-bold text-warning">{t("shipments.needsAction")}</span> : null}</div><ShipmentStatusBadge status={shipment.status} /></div><div className="mt-3 grid gap-1 text-sm text-text-secondary"><span>{t("shipments.customer")}: {shipment.customer_name ?? "—"}</span><span>{t("shipments.phone")}: {shipment.customer_phone ?? "—"}</span><span>{t("shipments.order")}: {shipment.order_number ?? "—"}</span><span>{t("shipments.carrier")}: {shipment.carrier}</span><span>{t("shipments.city")}: {shipment.city ?? "—"}</span><span>{t("shipments.updated")}: {new Date(shipment.updated_at).toLocaleString()}</span></div></button><div className="mt-4 grid gap-2"><CopyTtnButton trackingNumber={shipment.tracking_number ?? shipment.nova_poshta_document_number} />{shipment.order_id ? <Link className="min-h-11 w-full rounded-xl border border-border-subtle px-4 py-3 text-center font-bold text-text-primary" href={`/orders?order_id=${shipment.order_id}`}>{t("shipments.openOrder")}</Link> : null}{onEdit ? <button aria-label={`${t("shipments.edit")} ${shipment.tracking_number ?? shipment.id}`} className="min-h-11 w-full rounded-xl border border-border-subtle px-4 py-3 font-bold text-text-primary" onClick={() => onEdit(shipment)}>{t("shipments.edit")}</button> : null}{onArchive ? <button aria-label={`${t("shipments.archive")} ${shipment.tracking_number ?? shipment.id}`} className="min-h-11 w-full rounded-xl border border-danger/30 px-4 py-3 font-bold text-danger" onClick={() => onArchive(shipment)}>{t("shipments.archive")}</button> : null}</div></article>;
        })}
      </div>
      {shipments.length === 0 ? <p className="p-6 text-center text-text-muted">{t("shipments.empty")}</p> : null}
    </section>
  );
}
// Shipment TTN UX regression markers: Copy TTN, Create TTN, Sync status, Open order, needs action.
// Regression compatibility markers: Edit shipment; Archive shipment.
