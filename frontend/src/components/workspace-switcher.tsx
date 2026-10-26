"use client";

import { WorkspaceMenuContent } from "@/components/workspace-menu-content";
import { useI18n } from "@/i18n/provider";
import { WorkspaceMembership } from "@/types/auth";

export function WorkspaceSwitcher({ memberships, currentWorkspaceId, onSwitchWorkspace, onCreated, onClose }: { memberships: WorkspaceMembership[]; currentWorkspaceId: string | null; onSwitchWorkspace: (workspaceId: string) => void; onCreated: () => Promise<void>; onClose?: () => void }) {
  const { t } = useI18n();
  const labels = {
    workspace: t("accountMenu.workspace"),
    currentWorkspace: t("accountMenu.currentWorkspace"),
    switchWorkspace: t("accountMenu.switchWorkspace"),
    createWorkspace: t("accountMenu.createWorkspace"),
    storeName: t("accountMenu.storeName"),
    slug: t("accountMenu.slug"),
    creating: t("accountMenu.creating"),
    emptyWorkspace: t("accountMenu.emptyWorkspace"),
    createError: t("accountMenu.createWorkspaceError"),
    roleOwner: t("accountMenu.roleOwner"),
    roleManager: t("accountMenu.roleManager"),
    roleAnalyst: t("accountMenu.roleAnalyst"),
    cancel: t("actions.cancel"),
  };
  return <WorkspaceMenuContent memberships={memberships} currentWorkspaceId={currentWorkspaceId} labels={labels} onSwitchWorkspace={onSwitchWorkspace} onCreated={onCreated} onClose={onClose} />;
}
