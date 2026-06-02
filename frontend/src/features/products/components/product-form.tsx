"use client";

import { FormEvent, useState } from "react";
import { ProductCreatePayload } from "@/services/products";

export function ProductForm({ onSubmit }: { onSubmit: (values: ProductCreatePayload) => void }) {
  const [values, setValues] = useState<ProductCreatePayload>({ name: "", images: [] });
  const [imageUrl, setImageUrl] = useState("");

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit({ ...values, images: imageUrl ? [{ image_url: imageUrl, is_primary: true }] : [] });
    setValues({ name: "", images: [] });
    setImageUrl("");
  }

  return (
    <form className="grid gap-4" onSubmit={submit}>
      <label className="grid gap-1 text-sm font-medium text-slate-700">Name<input className="rounded-md border border-slate-300 px-3 py-2" required value={values.name} onChange={(event) => setValues({ ...values, name: event.target.value })} /></label>
      <label className="grid gap-1 text-sm font-medium text-slate-700">SKU<input className="rounded-md border border-slate-300 px-3 py-2" value={values.sku ?? ""} onChange={(event) => setValues({ ...values, sku: event.target.value })} /></label>
      <label className="grid gap-1 text-sm font-medium text-slate-700">Primary image URL<input className="rounded-md border border-slate-300 px-3 py-2" value={imageUrl} onChange={(event) => setImageUrl(event.target.value)} /></label>
      <label className="grid gap-1 text-sm font-medium text-slate-700">Description<textarea className="rounded-md border border-slate-300 px-3 py-2" value={values.description ?? ""} onChange={(event) => setValues({ ...values, description: event.target.value })} /></label>
      <button className="rounded-md bg-blue-600 px-4 py-2 font-semibold text-white hover:bg-blue-700" type="submit">Create product</button>
    </form>
  );
}
