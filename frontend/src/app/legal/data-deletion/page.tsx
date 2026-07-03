import { LegalPageShell } from "../_components/legal-page-shell";

export default function DataDeletionPage() {
  return (
    <LegalPageShell
      title="Видалення даних / Data Deletion"
      subtitle="Чернетка інструкції для майбутньої публічної URL-сторінки. Contact: <вкажіть email підтримки або юридичний контакт>."
      sections={[
        {
          title: "Як подати запит / How to request deletion",
          body: [
            "Власник робочого простору може подати запит на видалення даних через support/contact placeholder: <support@example.com>. У запиті потрібно вказати робочий простір і підтвердити право керувати ним.",
            "A workspace owner can request deletion through the support/contact placeholder: <support@example.com>. The request should identify the workspace and confirm authorization to manage it.",
          ],
        },
        {
          title: "Що може бути видалено / What may be deleted",
          body: [
            "Можуть бути видалені дані робочого простору, операційні записи магазину, користувацькі налаштування, імпортовані рекламні дані, клієнти, замовлення, товари та інші записи, якщо це дозволено законом і технічно можливо.",
            "Деякі записи можуть тимчасово зберігатися, якщо це потрібно для безпеки, резервного копіювання, запобігання шахрайству, виконання закону або захисту прав сторін.",
          ],
        },
        {
          title: "Meta-related data",
          body: [
            "Meta Ads API ще не активний, тому Sellora наразі не зберігає live Meta tokens або live Meta sync data.",
            "Future Meta-related deletion handling will be added before live Meta activation, token storage, or production sync is implemented.",
          ],
        },
        {
          title: "Юридичний статус / Legal status",
          body: [
            "Ця сторінка є MVP-чернеткою та має бути перевірена кваліфікованим юристом перед production launch або Meta App Review submission.",
          ],
        },
      ]}
    />
  );
}
