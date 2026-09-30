"use client";

import { FormEvent, useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Item = {
  id: number;
  name: string;
  category: string | null;
  category_confidence: number | null;
  created_at: string;
};

export default function Home() {
  const [items, setItems] = useState<Item[]>([]);
  const [categories, setCategories] = useState<Record<string, string>>({});
  const [filter, setFilter] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([fetch(`${API_URL}/items`), fetch(`${API_URL}/categories`)])
      .then(async ([itemsRes, categoriesRes]) => {
        if (!itemsRes.ok) throw new Error(`API returned ${itemsRes.status}`);
        setItems(await itemsRes.json());
        setCategories(await categoriesRes.json());
      })
      .catch((err) => setError(`Could not reach the API: ${err.message}`));
  }, []);

  async function addItem(e: FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setAdding(true);
    const res = await fetch(`${API_URL}/items`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
    setAdding(false);
    if (!res.ok) {
      setError(`Failed to add item (${res.status})`);
      return;
    }
    const item: Item = await res.json();
    setItems((prev) => [item, ...prev]);
    setName("");
    setError(null);
  }

  async function recategorize(id: number) {
    const res = await fetch(`${API_URL}/items/${id}/categorize`, { method: "POST" });
    if (!res.ok) {
      setError(`Failed to categorize item (${res.status})`);
      return;
    }
    const updated: Item = await res.json();
    setItems((prev) => prev.map((item) => (item.id === id ? updated : item)));
  }

  const visible = filter ? items.filter((item) => item.category === filter) : items;

  return (
    <main className="mx-auto flex w-full max-w-xl flex-1 flex-col gap-6 px-4 py-16">
      <h1 className="text-3xl font-semibold">Starter</h1>
      <p className="text-zinc-600 dark:text-zinc-400">
        Next.js → FastAPI → Postgres. New items are sorted into a category by Jev.
      </p>

      <form onSubmit={addItem} className="flex gap-2">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="New item"
          className="flex-1 rounded-md border border-zinc-300 bg-transparent px-3 py-2 dark:border-zinc-700"
        />
        <button
          type="submit"
          disabled={adding}
          className="rounded-md bg-foreground px-4 py-2 font-medium text-background disabled:opacity-50"
        >
          {adding ? "Adding…" : "Add"}
        </button>
      </form>

      {error && <p className="text-red-600">{error}</p>}

      <div className="flex flex-wrap gap-2">
        {[null, ...Object.keys(categories)].map((key) => (
          <button
            key={key ?? "all"}
            onClick={() => setFilter(key)}
            title={key ? categories[key] : undefined}
            className={`rounded-full border px-3 py-1 text-sm ${
              filter === key
                ? "border-foreground bg-foreground text-background"
                : "border-zinc-300 dark:border-zinc-700"
            }`}
          >
            {key ?? "all"}
          </button>
        ))}
      </div>

      <ul className="flex flex-col divide-y divide-zinc-200 dark:divide-zinc-800">
        {visible.map((item) => (
          <li key={item.id} className="flex items-center justify-between gap-4 py-2">
            <span>{item.name}</span>
            {item.category ? (
              <button
                onClick={() => recategorize(item.id)}
                title="Re-run categorization"
                className="shrink-0 rounded-full bg-zinc-100 px-2 py-0.5 text-sm text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300"
              >
                {item.category} · {Math.round((item.category_confidence ?? 0) * 100)}%
              </button>
            ) : (
              <button
                onClick={() => recategorize(item.id)}
                className="shrink-0 text-sm text-zinc-500 underline"
              >
                categorize
              </button>
            )}
          </li>
        ))}
      </ul>
    </main>
  );
}
