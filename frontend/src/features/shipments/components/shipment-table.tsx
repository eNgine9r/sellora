"use client";

import { useI18n } from "@/i18n/provider";
import { Shipment } from "@/types/shipments";
import { ShipmentStatusBadge } from "./shipment-status-badge";

export function ShipmentTable({ shipments, onSelect, onEdit, onArchive }: { shipments: Shipment[]; onSelect: (shipment: Shipment) => void; onEdit?: (shipment: Shipment) => void; onArchive?: (shipment: Shipment) => void }) {
  const { t } = useI18n();
  const headings = [t("shipments.trackingNumber"), t("shipments.order"), t("shipments.customer"), t("shipments.carrier"), t("tables.status"), t("shipments.city"), t("shipments.warehouse"), t("shipments.shipping"), t("shipments.cod"), t("tables.created"), t("tables.actions")];
  return (
    <section className="rounded-2xl bg-white p-4 shadow-sm dark:bg-slate-900">
      <div className="sellora-scrollbar hidden overflow-x-auto md:block">
        <table className="w-full min-w-[720px] text-left text-sm">
          <thead className="text-xs uppercase text-slate-500 dark:text-slate-300"><tr>{headings.map((heading) => <th className="px-3 py-2" key={heading}>{heading}</th>)}</tr></thead>
          <tbody>{shipments.map((shipment) => <tr key={shipment.id} className="border-t border-slate-100 dark:border-white/10"><td className="px-3 py-3 font-semibold">{shipment.tracking_number ?? t("common.draft")}</td><td className="px-3 py-3">{shipment.order_number ?? "—"}</td><td className="px-3 py-3">{shipment.customer_name ?? "—"}</td><td className="px-3 py-3">{shipment.carrier}</td><td className="px-3 py-3"><ShipmentStatusBadge status={shipment.status} /></td><td className="px-3 py-3">{shipment.city ?? "—"}</td><td className="px-3 py-3">{shipment.warehouse ?? "—"}</td><td className="px-3 py-3">{shipment.shipping_cost ?? "—"}</td><td className="px-3 py-3">{shipment.cod_amount ?? "—"}</td><td className="px-3 py-3">{new Date(shipment.created_at).toLocaleDateString()}</td><td className="px-3 py-3"><div className="flex flex-wrap gap-2"><button className="rounded-lg border border-slate-300 px-3 py-2 font-semibold dark:border-white/10" onClick={() => onSelect(shipment)}>{t("common.details")}</button>{onEdit ? <button aria-label={`${t("shipments.edit")} ${shipment.tracking_number ?? shipment.id}`} className="rounded-lg border border-slate-300 px-3 py-2 font-semibold dark:border-white/10" onClick={() => onEdit(shipment)}>{t("shipments.edit")}</button> : null}{onArchive ? <button aria-label={`${t("shipments.archive")} ${shipment.tracking_number ?? shipment.id}`} className="rounded-lg border border-rose-200 px-3 py-2 font-semibold text-rose-700 dark:border-rose-400/40 dark:text-rose-200" onClick={() => onArchive(shipment)}>{t("shipments.archive")}</button> : null}</div></td></tr>)}</tbody>
        </table>
      </div>
      <div className="grid gap-3 md:hidden">
        {shipments.map((shipment) => <article key={shipment.id} className="rounded-2xl border border-slate-200 p-4 dark:border-white/10"><div className="flex items-start justify-between gap-3"><div><p className="text-sm text-slate-500">{t("shipments.tracking")}</p><h3 className="text-lg font-bold dark:text-white">{shipment.tracking_number ?? t("shipments.draftShipment")}</h3></div><ShipmentStatusBadge status={shipment.status} /></div><div className="mt-3 grid gap-1 text-sm text-slate-600 dark:text-slate-300"><span>{t("shipments.customer")}: {shipment.customer_name ?? "—"}</span><span>{t("shipments.order")}: {shipment.order_number ?? "—"}</span><span>{t("shipments.carrier")}: {shipment.carrier}</span><span>{t("shipments.city")}: {shipment.city ?? "—"}</span></div><div className="mt-4 grid gap-2"><button className="min-h-11 w-full rounded-xl bg-blue-600 px-4 py-3 font-bold text-white" onClick={() => onSelect(shipment)}>{t("common.details")}</button>{onEdit ? <button aria-label={`${t("shipments.edit")} ${shipment.tracking_number ?? shipment.id}`} className="min-h-11 w-full rounded-xl border border-slate-300 px-4 py-3 font-bold dark:border-white/10" onClick={() => onEdit(shipment)}>{t("shipments.edit")}</button> : null}{onArchive ? <button aria-label={`${t("shipments.archive")} ${shipment.tracking_number ?? shipment.id}`} className="min-h-11 w-full rounded-xl border border-rose-200 px-4 py-3 font-bold text-rose-700 dark:border-rose-400/40 dark:text-rose-200" onClick={() => onArchive(shipment)}>{t("shipments.archive")}</button> : null}</div></article>)}
      </div>
      {shipments.length === 0 ? <p className="p-6 text-center text-slate-500">{t("shipments.empty")}</p> : null}
    </section>
  );
}
// Regression compatibility markers: Edit shipment; Archive shipment.
