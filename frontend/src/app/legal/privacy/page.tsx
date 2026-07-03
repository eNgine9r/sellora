import { LegalPageShell } from "../_components/legal-page-shell";

export default function PrivacyPolicyPage() {
  return (
    <LegalPageShell
      title="Політика конфіденційності / Privacy Policy"
      subtitle="Чернетка публічної сторінки для майбутнього Meta App setup. Effective date: <вкажіть дату>. Contact: <вкажіть email підтримки або юридичний контакт>."
      sections={[
        {
          title: "Що таке Sellora / What Sellora is",
          body: [
            "Sellora — це CRM/ERP SaaS для Instagram-магазинів в Україні, який допомагає власникам керувати лідами, клієнтами, замовленнями, товарами, складом, доставкою, рекламою, фінансами та аналітикою.",
            "Sellora is a CRM/ERP SaaS for Instagram shops that helps store owners manage leads, customers, orders, products, inventory, shipments, advertising, finance, and analytics.",
          ],
        },
        {
          title: "Які дані можуть зберігатися / Data that may be stored",
          body: [
            "Sellora може зберігати дані робочого простору, облікові записи користувачів, ролі, налаштування, операційні записи магазину та технічні дані, потрібні для роботи сервісу.",
            "Власники магазинів можуть вносити або імпортувати дані клієнтів і замовлень, зокрема імена, контакти, позиції замовлень, статуси оплат, доставки, примітки та історію взаємодій, якщо це дозволено законом і політиками магазину.",
          ],
        },
        {
          title: "Реклама і Meta / Advertising and Meta",
          body: [
            "Рекламні дані в MVP можуть вноситися вручну або імпортуватися через CSV. Meta Ads API ще не активний.",
            "Sellora наразі не надсилає дані клієнтів до Meta. Майбутні інтеграції потребуватимуть окремого перегляду безпеки, правових вимог і явної активації перед запуском.",
          ],
        },
        {
          title: "Контакт і дата / Contact and effective date",
          body: [
            "Contact placeholder: <support@example.com>. Effective date placeholder: <YYYY-MM-DD>.",
            "Do not treat this draft as final legal advice; it must be reviewed before public production launch or Meta App Review submission.",
          ],
        },
      ]}
    />
  );
}
