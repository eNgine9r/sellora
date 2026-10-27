"use client";

import { useEffect, useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { FormDialog } from "@/components/form-dialog";
import { OrderFulfillmentWizard } from "@/features/orders/components/order-fulfillment-wizard";
import type { Customer } from "@/types/crm";
import type { Inventory, Product, ProductVariant } from "@/types/products";

const ws = "qa-only-workspace";
const customer = { id: "qa-customer", workspace_id: ws, name: "Тестовий клієнт", phone: "+380671234567", instagram_username: "test_only" } as Customer;
const product = { id: "qa-product", workspace_id: ws, name: "Тестовий браслет", sku: "QA-BRACELET" } as Product;
const variant = { id: "qa-variant", workspace_id: ws, product_id: product.id, sku: "QA-01", color: "Срібло", size: "M", price: "450", is_active: true } as ProductVariant;
const stock = { product_variant_id: variant.id, stock_quantity: 5, reserved_quantity: 0 } as Inventory;

export default function SyntheticOrderFixture() {
  const [open, setOpen] = useState(true);
  const [queryClient] = useState(() => {
    const q = new QueryClient({ defaultOptions: { queries: { staleTime: Infinity, retry: false } } });
    q.setQueryData(["nova-poshta-readiness", ws], { provider_writes_enabled: false, write_blockers: [] });
    q.setQueryData(["customer-addresses", ws, customer.id, "fulfillment"], [{ id: "qa-address", is_default: true, recipient_name: customer.name, phone: customer.phone, city: "Київ", nova_poshta_city_ref: "qa-city", address_line1: "Тестове відділення", nova_poshta_warehouse_ref: "qa-warehouse", warehouse_number: "1" }]);
    q.setQueryData(["np-cities", ws, "Київ"], []);
    q.setQueryData(["np-warehouses", ws, "qa-city", ""], []);
    q.setQueryData(["np-warehouses", ws, "qa-city", "Тестове відділення"], []);
    return q;
  });
  useEffect(() => {
    const blockSubmission = (event: MouseEvent) => {
      const target = event.target as HTMLElement;
      const button = target.closest("button");
      if (button && /Створити без ТТН|Створити замовлення і ТТН|Create without|Create order and/i.test(button.textContent || "")) {
        event.preventDefault(); event.stopPropagation();
      }
    };
    document.addEventListener("click", blockSubmission, true);
    return () => document.removeEventListener("click", blockSubmission, true);
  }, []);
  return <QueryClientProvider client={queryClient}>
    <main><h1>QA: лише синтетичні дані</h1><button type="button" onClick={() => setOpen(true)}>Відкрити тестову форму</button></main>
    {open ? <FormDialog title="Створити замовлення" description="Тестова форма: жодні дані не зберігаються." size="xl" onClose={() => setOpen(false)}>
      <OrderFulfillmentWizard workspaceId={ws} customers={[customer]} variants={[variant]} products={[product]} inventory={[stock]} campaigns={[]} currencyCode="UAH" showProfit initialCustomerId={customer.id} onSuccess={() => {}} />
    </FormDialog> : null}
  </QueryClientProvider>;
}
