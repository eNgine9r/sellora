"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/crm-workspace";
import { useAuth } from "@/hooks/use-auth";
import { useI18n } from "@/i18n/provider";
import { fetchDirectIdentityCandidates, linkDirectIdentityCandidate } from "@/services/direct";

export function DirectIdentityReview({ conversationId, hasOrder }: { conversationId: string; hasOrder: boolean }) {
  const { t } = useI18n();
  const { currentWorkspace } = useAuth();
  const workspaceId = currentWorkspace?.workspace_id;
  const client = useQueryClient();
  const [chosen, setChosen] = useState<string | null>(null);
  const candidates = useQuery({
    queryKey: ["direct-identity-candidates", workspaceId, conversationId],
    queryFn: () => fetchDirectIdentityCandidates(conversationId, workspaceId!),
    enabled: Boolean(workspaceId),
  });
  const link = useMutation({
    mutationFn: (customerId: string) => linkDirectIdentityCandidate(conversationId, customerId, workspaceId!),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ["direct-conversations", workspaceId] });
      void client.invalidateQueries({ queryKey: ["direct-customer-automation", workspaceId, conversationId] });
      void client.invalidateQueries({ queryKey: ["customers", workspaceId] });
    },
    onError: () => { void candidates.refetch(); setChosen(null); },
  });
  return <div className="mt-3 grid gap-2 text-sm" data-direct-identity-review>
    <p>{hasOrder ? t("direct.identityOrderBlocked") : t("direct.identityReviewPrompt")}</p>
    {candidates.isLoading ? <p>{t("direct.identityLoading")}</p> : null}
    {candidates.isError ? <p role="alert">{t("direct.identityLoadError")}</p> : null}
    {candidates.data?.length === 0 ? <p>{t("direct.identityNoCandidates")}</p> : null}
    {candidates.data?.map(candidate => <div key={candidate.id} className="rounded-xl border border-border-subtle bg-surface-1 p-3">
      <p className="break-words font-bold">{candidate.name}{candidate.instagram_username ? ` · @${candidate.instagram_username.replace(/^@/, "")}` : ""}{candidate.phone_last_four ? ` · •••• ${candidate.phone_last_four}` : ""}</p>
      {chosen === candidate.id ? <div className="mt-2 flex flex-wrap items-center gap-2">
        <span>{t("direct.identityConfirmQuestion")}</span>
        <Button onClick={() => link.mutate(candidate.id)} disabled={link.isPending || hasOrder}>{t("direct.identityConfirm")}</Button>
        <Button variant="secondary" onClick={() => setChosen(null)} disabled={link.isPending}>{t("direct.identityCancel")}</Button>
      </div> : <Button variant="secondary" onClick={() => setChosen(candidate.id)} disabled={link.isPending || hasOrder}>{t("direct.identityChoose")}</Button>}
    </div>)}
    {candidates.data?.length === 20 ? <p>{t("direct.identityMore")}</p> : null}
    {link.isError ? <p role="alert">{t("direct.identityLinkError")}</p> : null}
  </div>;
}
