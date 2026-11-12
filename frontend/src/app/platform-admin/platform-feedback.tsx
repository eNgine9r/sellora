import { Button, ErrorState } from "@/components/ui/primitives";
import { useI18n } from "@/i18n/provider";
import { ApiError } from "@/services/api";

export function accessDenied(error: unknown) {
  return error instanceof ApiError && (error.status === 401 || error.status === 403);
}

export function PlatformProblem({ message, retry }: { message: "forbidden" | "unavailable" | "error" | "notFound"; retry?: () => void }) {
  const { t } = useI18n();
  return (
    <div className="grid gap-3" role="alert">
      <ErrorState title={t(`platformAdmin.feedback.${message}.title`)} description={t(`platformAdmin.feedback.${message}.description`)} />
      {retry ? <Button variant="secondary" className="justify-self-start" onClick={retry}>{t("actions.retry")}</Button> : null}
    </div>
  );
}
