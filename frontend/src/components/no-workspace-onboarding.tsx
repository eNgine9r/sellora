"use client";

import Link from "next/link";
import { usePublicAuthOptions } from "@/hooks/use-public-auth-options";
import { WorkspaceSwitcher } from "@/components/workspace-switcher";
import { DemoWorkspaceActions } from "@/components/pilot-readiness";
import { useI18n } from "@/i18n/provider";

export function NoWorkspaceOnboarding({ onWorkspaceCreated, onSwitchWorkspace }: { onWorkspaceCreated: () => Promise<void>; onSwitchWorkspace: (workspaceId: string) => void }) {
  const { t } = useI18n();
  const { data: authOptions } = usePublicAuthOptions();

  return (
    <main className="min-h-[calc(100vh-5rem)] bg-[#F8F7FC] p-4 text-slate-950 dark:bg-[#101120] dark:text-white sm:p-6">
      <section className="mx-auto grid max-w-2xl gap-5 rounded-[32px] bg-white p-6 text-center shadow-[0_18px_45px_rgba(15,23,42,0.06)] dark:bg-white/10 sm:p-8">
        <div>
          <p className="text-sm font-black uppercase tracking-[0.25em] text-violet-600 dark:text-violet-200">Sellora</p>
          <h1 className="mt-3 text-3xl font-black sm:text-4xl">{t("accountMenu.emptyWorkspaceTitle")}</h1>
          <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-slate-600 dark:text-slate-300">{t("accountMenu.emptyWorkspaceDescription")}</p>
          <div className="mt-4 flex flex-wrap justify-center gap-2"><DemoWorkspaceActions /></div>
        </div>
        <div className="text-left">
          <WorkspaceSwitcher memberships={[]} currentWorkspaceId={null} onSwitchWorkspace={onSwitchWorkspace} onCreated={onWorkspaceCreated} />
        </div>
        {authOptions?.providers.length ? (
          <Link href="/settings/sign-in" className="mx-auto inline-flex min-h-11 items-center rounded-xl px-3 text-sm font-bold text-violet-700 underline underline-offset-4 focus-visible:ring-2 focus-visible:ring-violet-600 dark:text-violet-200">
            {t("auth.access.methodsTitle")}
          </Link>
        ) : null}
      </section>
    </main>
  );
}
