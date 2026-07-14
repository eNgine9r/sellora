import { ValidationIssue } from "@/types/import-center";

export type ImportCenterLocale = "uk" | "en";

const copy = {
  uk: {
    ordersHistoryHelp: "Імпорт створює історичні замовлення, позиції та клієнтів за потреби. Він не створює відправлення автоматично й за замовчуванням не впливає на поточний склад.",
    validationTitle: "Проблеми валідації",
    validationReport: "Звіт валідації",
    valid: "Дані коректні",
    invalid: "Потрібні виправлення",
    rows: "рядків",
    columnMapping: "Зіставлення колонок",
    notMapped: "Не зіставлено",
    entityType: "Тип даних",
    total: "Усього",
    processed: "Оброблено",
    success: "Успішно",
    failed: "З помилкою",
    row: "Рядок",
    severity: "Рівень",
    field: "Колонка",
    message: "Повідомлення",
    mapping: "Мапінг",
    error: "Помилка",
    warning: "Попередження",
    skipped: "Пропущено",
    downloadErrorCsv: "Завантажити CSV з помилками",
    fallbackError: "Некоректне значення. Перевірте вказаний рядок і колонку.",
    fallbackWarning: "Перевірте значення у вказаному рядку.",
  },
  en: {
    ordersHistoryHelp: "The import creates historical orders, items, and customers when needed. It never creates shipments automatically and does not affect current inventory by default.",
    validationTitle: "Validation issues",
    validationReport: "Validation report",
    valid: "Data is valid",
    invalid: "Changes required",
    rows: "rows",
    columnMapping: "Column mapping",
    notMapped: "Not mapped",
    entityType: "Data type",
    total: "Total",
    processed: "Processed",
    success: "Success",
    failed: "Failed",
    row: "Row",
    severity: "Severity",
    field: "Column",
    message: "Message",
    mapping: "Mapping",
    error: "Error",
    warning: "Warning",
    skipped: "Skipped",
    downloadErrorCsv: "Download error CSV",
    fallbackError: "Invalid value. Check the indicated row and column.",
    fallbackWarning: "Review the value in the indicated row.",
  },
} as const;

const entityLabels = {
  uk: {
    customers: "Клієнти",
    products: "Товари",
    product_variants: "Варіанти товарів",
    inventory: "Складські залишки",
    orders: "Замовлення",
    ad_campaigns: "Рекламні кампанії",
    ad_metrics: "Рекламні метрики",
    product_catalog: "Каталог товарів",
    orders_history: "Історія замовлень",
    advertising_history: "Історія реклами",
  },
  en: {
    customers: "Customers",
    products: "Products",
    product_variants: "Product variants",
    inventory: "Inventory",
    orders: "Orders",
    ad_campaigns: "Advertising campaigns",
    ad_metrics: "Advertising metrics",
    product_catalog: "Product catalog",
    orders_history: "Order history",
    advertising_history: "Advertising history",
  },
} as const;

const fieldLabels = {
  uk: {
    name: "Назва / ім’я", phone: "Телефон", instagram_username: "Instagram", city: "Місто", region: "Область",
    sku: "Артикул товару", description: "Опис", product_name: "Назва товару", product_sku: "Артикул товару",
    variant_sku: "Артикул варіанта", color: "Колір", size: "Розмір", selling_price: "Ціна продажу",
    stock_quantity: "Залишок", reserved_quantity: "Зарезервовано", minimum_quantity: "Мінімальний залишок",
    customer_name: "Клієнт", customer_phone: "Телефон клієнта", revenue: "Виручка", order_total: "Сума замовлення",
    created_at: "Дата створення", order_date: "Дата замовлення", ad_cost: "Витрати на рекламу",
    shipping_cost: "Доставка", cod_fee: "Комісія післяплати", other_cost: "Інші витрати", net_profit: "Чистий прибуток",
  },
  en: {
    name: "Name", phone: "Phone", instagram_username: "Instagram", city: "City", region: "Region",
    sku: "Product SKU", description: "Description", product_name: "Product name", product_sku: "Product SKU",
    variant_sku: "Variant SKU", color: "Color", size: "Size", selling_price: "Selling price",
    stock_quantity: "Stock", reserved_quantity: "Reserved", minimum_quantity: "Minimum stock",
    customer_name: "Customer", customer_phone: "Customer phone", revenue: "Revenue", order_total: "Order total",
    created_at: "Created at", order_date: "Order date", ad_cost: "Advertising cost",
    shipping_cost: "Shipping", cod_fee: "COD fee", other_cost: "Other costs", net_profit: "Net profit",
  },
} as const;

export function getImportCenterPilotCopy(locale: string) {
  return locale === "en" ? copy.en : copy.uk;
}

export function importEntityLabel(value: string, locale: string): string {
  const labels = locale === "en" ? entityLabels.en : entityLabels.uk;
  return labels[value as keyof typeof labels] ?? value;
}

export function importFieldLabel(value: string, locale: string): string {
  const labels = locale === "en" ? fieldLabels.en : fieldLabels.uk;
  return labels[value as keyof typeof labels] ?? value;
}

export function localizeImportIssue(issue: ValidationIssue, locale: string): string {
  const value = issue.message.trim();
  if (locale === "en") return value;

  const rules: Array<[RegExp, (match: RegExpMatchArray) => string]> = [
    [/^Required mapping missing: one of (.+)$/i, (match) => `Відсутнє обов’язкове зіставлення: одне з полів ${match[1]}.`],
    [/^Row requires one of (.+)$/i, (match) => `У рядку потрібно заповнити одне з полів: ${match[1]}.`],
    [/^(.+) must be numeric$/i, (match) => `Поле «${match[1]}» має містити числове значення.`],
    [/^(.+) cannot be negative$/i, (match) => `Поле «${match[1]}» не може мати від’ємне значення.`],
    [/^(.+) must be a valid date$/i, (match) => `Поле «${match[1]}» має містити коректну дату.`],
    [/^Unsupported order_status: (.+)$/i, (match) => `Непідтримуваний статус замовлення: ${match[1]}.`],
    [/^Unsupported payment_status: (.+)$/i, (match) => `Непідтримуваний статус оплати: ${match[1]}.`],
    [/^Formula-prefixed CSV values are not allowed$/i, () => "Значення, що починаються як формула, заборонені. Збережіть його як звичайний текст."],
    [/^Existing inventory will be updated using absolute quantities$/i, () => "Наявний складський залишок буде встановлено до вказаного абсолютного значення, а не додано повторно."],
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
