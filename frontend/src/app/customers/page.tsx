"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { CustomerForm, CustomerFormValues } from "@/features/customers/components/customer-form";
import { CustomerTable } from "@/features/customers/components/customer-table";
import { createCustomer, fetchCustomers } from "@/services/crm";

export default function CustomersPage() {
  const queryClient = useQueryClient();
  const [workspaceId, setWorkspaceId] = useState("");
  const [token, setToken] = useState("");
  const [search, setSearch] = useState("");
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const enabled = Boolean(workspaceId);

  const customersQuery = useQuery({ queryKey: ["customers", workspaceId, search], queryFn: () => fetchCustomers(workspaceId, search, token), enabled });
  const createMutation = useMutation({
    mutationFn: (values: CustomerFormValues) => createCustomer(workspaceId, values, token),
    onSuccess: () => {
      setIsCreateOpen(false);
      queryClient.invalidateQueries({ queryKey: ["customers", workspaceId] });
    },
  });

  return (
    <main className="min-h-screen bg-slate-100 p-6 text-slate-950">
      <div className="mx-auto grid max-w-7xl gap-6">
        <header className="flex flex-col gap-4 rounded-2xl bg-white p-6 shadow-sm md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-blue-600">Sellora CRM</p>
            <h1 className="mt-2 text-3xl font-bold">Customers</h1>
            <p className="mt-1 text-slate-600">Manage converted and manually created customers.</p>
          </div>
          <button className="rounded-lg bg-blue-600 px-4 py-2 font-semibold text-white hover:bg-blue-700" onClick={() => setIsCreateOpen(true)}>Create customer</button>
        </header>

        <section className="grid gap-3 rounded-2xl bg-white p-4 shadow-sm md:grid-cols-3">
          <input className="rounded-md border border-slate-300 px-3 py-2" placeholder="Workspace ID" value={workspaceId} onChange={(event) => setWorkspaceId(event.target.value)} />
          <input className="rounded-md border border-slate-300 px-3 py-2" placeholder="Access token" value={token} onChange={(event) => setToken(event.target.value)} />
          <input className="rounded-md border border-slate-300 px-3 py-2" placeholder="Search customers" value={search} onChange={(event) => setSearch(event.target.value)} />
        </section>

        {customersQuery.isError ? <p className="rounded-lg bg-rose-50 p-4 text-rose-700">Unable to load customers. Check workspace and authentication.</p> : null}
        <CustomerTable customers={customersQuery.data ?? []} />

        {isCreateOpen ? (
          <div className="fixed inset-0 grid place-items-center bg-slate-950/40 p-4">
            <div className="w-full max-w-xl rounded-2xl bg-white p-6 shadow-xl">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-xl font-bold">Create customer</h2>
                <button className="text-slate-500" onClick={() => setIsCreateOpen(false)}>Close</button>
              </div>
              <CustomerForm onSubmit={(values) => createMutation.mutate(values)} />
            </div>
          </div>
        ) : null}
      </div>
    </main>
  );
}
