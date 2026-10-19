"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { ConfirmActionDialog } from "@/components/confirm-action-dialog";
import { Button } from "@/components/crm-workspace";
import { useI18n } from "@/i18n/provider";
import { hasUsableTtn } from "@/lib/ttn-draft";
import { fetchDirectCustomerAutomation } from "@/services/direct";
import { fetchOrder } from "@/services/orders";
import { fetchShipment } from "@/services/shipments";

// URLs carry only identity. Re-read all relationships under the current workspace;
// neither URL text nor customer identity alone authorizes a conversation handoff.
export function DirectTtnDraft({ workspaceId, conversationId, orderId, shipmentId, draftText, onInsert }: {
  workspaceId: string; conversationId: string; orderId: string; shipmentId: string;
  draftText: string; onInsert: (text: string) => void;
}) {
  const { t } = useI18n();
  const [confirm, setConfirm] = useState(false);
  const [inserted, setInserted] = useState(false);
  const query = useQuery({
    queryKey: ["direct-ttn-draft", workspaceId, conversationId, orderId, shipmentId],
    queryFn: async () => {
      const [order, shipment, automation] = await Promise.all([
        fetchOrder(workspaceId, orderId),
        fetchShipment(workspaceId, shipmentId),
        fetchDirectCustomerAutomation(conversationId, workspaceId),
      ]);
      if (order.id !== orderId || order.workspace_id !== workspaceId
        || shipment.id !== shipmentId || shipment.workspace_id !== workspaceId
        || shipment.order_id !== order.id || !hasUsableTtn(shipment)
        || automation.conversation_id !== conversationId || automation.linked_order_id !== order.id
        || !order.customer_id || automation.customer?.id !== order.customer_id
        || (shipment.customer_id && shipment.customer_id !== order.customer_id)) {
        throw new Error("TTN_RELATION_NOT_VERIFIED");
      }
      return { orderNumber: order.order_number, trackingNumber: shipment.nova_poshta_document_number || shipment.tracking_number };
    },
    retry: false,
  });
  if (inserted) return null;
  const text = query.data ? t("fulfillment.ttnDraftPreview", { order: query.data.orderNumber, ttn: query.data.trackingNumber }) : "";
  const insert = () => {
    if (!query.data || query.isFetching || query.isError) return;
    onInsert(text);
    setConfirm(false);
    setInserted(true);
  };
  return <section className="mb-2 grid shrink-0 gap-2 rounded-xl border border-border-subtle bg-surface-1 p-3 text-sm" data-direct-ttn-draft>
    {query.isPending || query.isFetching ? <p role="status">{t("fulfillment.ttnDraftLoading")}</p> : query.isError ? <p role="alert">{t("fulfillment.ttnDraftError")}</p> : <>
      <p className="break-words font-semibold">{text}</p>
      <p className="text-xs text-text-secondary">{t("fulfillment.ttnDraftNotice")}</p>
      <Button onClick={() => draftText.trim() ? setConfirm(true) : insert()}>{t("fulfillment.insertTtnDraft")}</Button>
    </>}
    {confirm ? <ConfirmActionDialog title={t("fulfillment.replaceDraftTitle")} description={t("fulfillment.replaceDraftDescription")} actionLabel={t("fulfillment.replaceDraft")} isSubmitting={query.isFetching || query.isError} onCancel={() => setConfirm(false)} onConfirm={insert} /> : null}
  </section>;
}
