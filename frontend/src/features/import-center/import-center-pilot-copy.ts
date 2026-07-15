import { ValidationIssue } from "@/types/import-center";

export type ImportCenterLocale = "uk" | "en";

const copy = {
  uk: {
    ordersHistoryHelp:
      "Імпорт створює історичні замовлення, позиції та клієнтів за потреби. Він не створює відправлення автоматично й за замовчуванням не впливає на поточний склад.",
    validationTitle: "Проблеми валідації",
    row: "Рядок",
    severity: "Рівень",
    field: "Колонка",
    message: "Повідомлення",
    mapping: "Мапінг",
    error: "Помилка",
    warning: "Попередження",
    downloadErrorCsv: "Завантажити CSV з помилками",
    executeConfirmTitle: "Підтвердити імпорт",
    executeConfirmDescription:
      "Sellora створить або оновить сутності відповідно до підтвердженого dry-run. Перевірте робочий простір, мапінг і підсумок перед виконанням.",
    executeConfirmAction: "Виконати імпорт",
    executeError: "Не вдалося виконати імпорт. Перевірте dry-run і повторіть спробу.",
    fallbackError: "Некоректне значення. Перевірте вказаний рядок і колонку.",
    fallbackWarning: "Перевірте значення у вказаному рядку.",
  },
  en: {
    ordersHistoryHelp:
      "The import creates historical orders, items, and customers when needed. It never creates shipments automatically and does not affect current inventory by default.",
    validationTitle: "Validation issues",
    row: "Row",
    severity: "Severity",
    field: "Column",
    message: "Message",
    mapping: "Mapping",
    error: "Error",
    warning: "Warning",
    downloadErrorCsv: "Download error CSV",
    executeConfirmTitle: "Confirm import",
    executeConfirmDescription:
      "Sellora will create or update entities according to the approved dry-run. Review the workspace, mapping, and summary before execution.",
    executeConfirmAction: "Execute import",
    executeError: "The import could not be executed. Review the dry-run and try again.",
    fallbackError: "Invalid value. Check the indicated row and column.",
    fallbackWarning: "Review the value in the indicated row.",
  },
} as const;

export function getImportCenterPilotCopy(locale: string) {
  return locale === "en" ? copy.en : copy.uk;
}

export function localizeImportIssue(issue: ValidationIssue, locale: string): string {
  const value = issue.message.trim();
  if (locale === "en") return value;

  const rules: Array<[RegExp, (match: RegExpMatchArray) => string]> = [
    [/^Required mapping missing: one of (.+)$/i, (match) => `Відсутнє обов’язкове зіставлення: одне з полів ${match[1]}.`],
    [/^(.+) must be numeric$/i, (match) => `Поле «${match[1]}» має містити числове значення.`],
    [/^(.+) cannot be negative$/i, (match) => `Поле «${match[1]}» не може мати від’ємне значення.`],
    [/^(.+) must be a valid date$/i, (match) => `Поле «${match[1]}» має містити коректну дату.`],
    [/^Unsupported order_status: (.+)$/i, (match) => `Непідтримуваний статус замовлення: ${match[1]}.`],
    [/^Unsupported payment_status: (.+)$/i, (match) => `Непідтримуваний статус оплати: ${match[1]}.`],
    [/^Unsupported entity_type$/i, () => "Цей тип імпорту не підтримується."],
    [/^Product variant SKU is required\.?$/i, () => "Потрібно вказати SKU варіанта товару."],
    [/^Product variant not found\. Import product catalog first\.?$/i, () => "Варіант товару не знайдено. Спочатку імпортуйте каталог товарів."],
    [/^Quantity must be greater than 0\.?$/i, () => "Кількість має бути більшою за 0."],
    [/^Unit price is required\.?$/i, () => "Потрібно вказати ціну одиниці."],
    [/^Campaign name is required\.?$/i, () => "Потрібно вказати назву рекламної кампанії."],
    [/^Metric date is required\.?$/i, () => "Потрібно вказати дату рекламної метрики."],
    [/^Spend cannot be negative\.?$/i, () => "Витрати на рекламу не можуть бути від’ємними."],
    [/^Duplicate (.+) skipped$/i, (match) => `Дублікат пропущено: ${match[1]}.`],
  ];

  for (const [pattern, translate] of rules) {
    const match = value.match(pattern);
    if (match) return translate(match);
  }

  const labels = getImportCenterPilotCopy(locale);
  return issue.severity === "WARNING" ? labels.fallbackWarning : labels.fallbackError;
}

export function escapeImportCsvCell(value: unknown): string {
  let text = value == null ? "" : String(value);
  if (/^[=+\-@]/.test(text)) text = `'${text}`;
  return `"${text.replaceAll('"', '""')}"`;
}
