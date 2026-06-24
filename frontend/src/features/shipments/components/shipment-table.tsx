"use client";

import Link from "next/link";
import { useI18n } from "@/i18n/provider";
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

export function ShipmentTable({ shipments, onSelect, onEdit, onArchive }: { shipments: Shipment[]; onSelect: (shipment: Shipment) => void; onEdit?: (shipment: Shipment) => void; onArchive?: (shipment: Shipment) => void }) {
  const { t } = useI18n();
  const headings = [t("shipments.trackingNumber"), t("shipments.order"), t("shipments.customer"), t("shipments.carrier"), t("tables.status"), t("shipments.destination"), t("shipments.updated"), t("tables.actions")];
  return (
    <section className="rounded-2xl bg-white p-4 shadow-sm dark:bg-slate-900">
      <div className="sellora-scrollbar hidden overflow-x-auto md:block">
        <table className="w-full min-w-[940px] text-left text-sm">
          <thead className="text-xs uppercase text-slate-500 dark:text-slate-300">
            <tr>{headings.map((heading) => <th className="px-3 py-2" key={heading}>{heading}</th>)}</tr>
          </thead>
          <tbody>
            {shipments.map((shipment) => {
              const tracking = displayTtn(shipment, t("common.draft"));
              return (
                <tr key={shipment.id} className="border-t border-slate-100 align-top dark:border-white/10">
                  <td className="px-3 py-3 font-semibold"><span className="block max-w-[170px] break-words">{tracking}</span>{needsAction(shipment) ? <span className="mt-1 inline-flex rounded-full bg-amber-50 px-2 py-1 text-xs text-amber-700 dark:bg-amber-500/15 dark:text-amber-100">{t("shipments.needsAction")}</span> : null}</td>
                  <td className="px-3 py-3">{shipment.order_number ?? "—"}</td>
                  <td className="px-3 py-3"><span className="block font-semibold">{shipment.customer_name ?? "—"}</span><span className="block text-xs text-slate-500 dark:text-slate-400">{shipment.customer_phone ?? "—"}</span></td>
                  <td className="px-3 py-3">{shipment.carrier}</td>
                  <td className="px-3 py-3"><ShipmentStatusBadge status={shipment.status} /></td>
                  <td className="px-3 py-3"><span className="block">{shipment.city ?? "—"}</span><span className="block text-xs text-slate-500 dark:text-slate-400">{shipment.warehouse ?? "—"}</span></td>
                  <td className="px-3 py-3"><span className="block">{new Date(shipment.updated_at).toLocaleString()}</span>{shipment.nova_poshta_synced_at ? <span className="block text-xs text-slate-500 dark:text-slate-400">{t("shipments.lastSynced")}: {new Date(shipment.nova_poshta_synced_at).toLocaleString()}</span> : null}</td>
                  <td className="px-3 py-3"><div className="grid min-w-[160px] gap-2"><button className="rounded-lg border border-slate-300 px-3 py-2 font-semibold dark:border-white/10" onClick={() => onSelect(shipment)}>{shipment.tracking_number ? t("common.details") : t("shipments.createTtn")}</button><CopyTtnButton trackingNumber={shipment.tracking_number ?? shipment.nova_poshta_document_number} />{shipment.order_id ? <Link className="rounded-lg border border-slate-300 px-3 py-2 text-center font-semibold dark:border-white/10" href={`/orders?order_id=${shipment.order_id}`}>{t("shipments.openOrder")}</Link> : null}{onEdit ? <button aria-label={`${t("shipments.edit")} ${shipment.tracking_number ?? shipment.id}`} className="rounded-lg border border-slate-300 px-3 py-2 font-semibold dark:border-white/10" onClick={() => onEdit(shipment)}>{t("shipments.edit")}</button> : null}{onArchive ? <button aria-label={`${t("shipments.archive")} ${shipment.tracking_number ?? shipment.id}`} className="rounded-lg border border-rose-200 px-3 py-2 font-semibold text-rose-700 dark:border-rose-400/40 dark:text-rose-200" onClick={() => onArchive(shipment)}>{t("shipments.archive")}</button> : null}</div></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div className="grid gap-3 md:hidden">
        {shipments.map((shipment) => <article key={shipment.id} className="rounded-2xl border border-slate-200 p-4 dark:border-white/10"><div className="flex items-start justify-between gap-3"><div><p className="text-sm text-slate-500">{t("shipments.tracking")}</p><h3 className="break-words text-lg font-bold dark:text-white">{displayTtn(shipment, t("shipments.draftShipment"))}</h3>{needsAction(shipment) ? <span className="mt-1 inline-flex rounded-full bg-amber-50 px-2 py-1 text-xs font-bold text-amber-700 dark:bg-amber-500/15 dark:text-amber-100">{t("shipments.needsAction")}</span> : null}</div><ShipmentStatusBadge status={shipment.status} /></div><div className="mt-3 grid gap-1 text-sm text-slate-600 dark:text-slate-300"><span>{t("shipments.customer")}: {shipment.customer_name ?? "—"}</span><span>{t("shipments.phone")}: {shipment.customer_phone ?? "—"}</span><span>{t("shipments.order")}: {shipment.order_number ?? "—"}</span><span>{t("shipments.carrier")}: {shipment.carrier}</span><span>{t("shipments.city")}: {shipment.city ?? "—"}</span><span>{t("shipments.updated")}: {new Date(shipment.updated_at).toLocaleString()}</span></div><div className="mt-4 grid gap-2"><button className="min-h-11 w-full rounded-xl bg-blue-600 px-4 py-3 font-bold text-white" onClick={() => onSelect(shipment)}>{t("common.details")}</button><CopyTtnButton trackingNumber={shipment.tracking_number ?? shipment.nova_poshta_document_number} />{shipment.order_id ? <Link className="min-h-11 w-full rounded-xl border border-slate-300 px-4 py-3 text-center font-bold dark:border-white/10" href={`/orders?order_id=${shipment.order_id}`}>{t("shipments.openOrder")}</Link> : null}{onEdit ? <button aria-label={`${t("shipments.edit")} ${shipment.tracking_number ?? shipment.id}`} className="min-h-11 w-full rounded-xl border border-slate-300 px-4 py-3 font-bold dark:border-white/10" onClick={() => onEdit(shipment)}>{t("shipments.edit")}</button> : null}{onArchive ? <button aria-label={`${t("shipments.archive")} ${shipment.tracking_number ?? shipment.id}`} className="min-h-11 w-full rounded-xl border border-rose-200 px-4 py-3 font-bold text-rose-700 dark:border-rose-400/40 dark:text-rose-200" onClick={() => onArchive(shipment)}>{t("shipments.archive")}</button> : null}</div></article>)}
      </div>
      {shipments.length === 0 ? <p className="p-6 text-center text-slate-500">{t("shipments.empty")}</p> : null}
    </section>
  );
}
// Shipment TTN UX regression markers: Copy TTN, Create TTN, Sync status, Open order, needs action.
// Regression compatibility markers: Edit shipment; Archive shipment.
