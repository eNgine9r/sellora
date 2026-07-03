import { LegalPageShell } from "../_components/legal-page-shell";

export default function TermsPage() {
  return (
    <LegalPageShell
      title="Умови користування / Terms of Service"
      subtitle="Чернетка умов для підготовки продукту. Effective date: <вкажіть дату>. Contact: <вкажіть email підтримки або юридичний контакт>."
      sections={[
        {
          title: "Призначення сервісу / Service purpose",
          body: [
            "Sellora — це CRM/ERP SaaS для Instagram-магазинів, який допомагає керувати операційними процесами: лідами, клієнтами, замовленнями, товарами, складом, доставкою, рекламою, фінансами й аналітикою.",
            "Користувач відповідає за законне отримання, внесення та використання даних клієнтів, замовлень і рекламних даних у своєму робочому просторі.",
          ],
        },
        {
          title: "Фінанси та реклама / Finance and advertising",
          body: [
            "Sellora Finance — це операційна аналітика прибутку, а не бухгалтерський, податковий або юридичний звіт.",
            "Рекламні дані можуть бути ручними або імпортованими через CSV і можуть бути неповними. Meta Ads API ще не активний.",
          ],
        },
        {
          title: "Обмеження / Limitations",
          body: [
            "Sellora не гарантує податкову, бухгалтерську або юридичну відповідність без окремої перевірки кваліфікованими фахівцями.",
            "Майбутні інтеграції, зокрема Meta API, потребуватимуть окремої активації, безпекової перевірки та документації перед використанням.",
          ],
        },
        {
          title: "Контакт і дата / Contact and effective date",
          body: [
            "Contact placeholder: <support@example.com>. Effective date placeholder: <YYYY-MM-DD>.",
            "This draft must be reviewed before production launch, payment activation, or Meta App Review submission.",
          ],
        },
      ]}
    />
  );
}
