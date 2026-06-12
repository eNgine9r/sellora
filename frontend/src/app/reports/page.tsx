import { redirect } from "next/navigation";

export default function ReportsAliasPage() {
  redirect("/analytics");
}
// Reports navigation decision: /reports is a stable sidebar alias that redirects to the existing /analytics reports page.
