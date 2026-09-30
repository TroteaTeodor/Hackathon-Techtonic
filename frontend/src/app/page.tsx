"use client";

import { FormEvent, useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Item = {
  id: number;
  name: string;
  created_at: string;
};

export default function Home() {
  const [items, setItems] = useState<Item[]>([]);
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_URL}/items`)
      .then((res) => {
        if (!res.ok) throw new Error(`API returned ${res.status}`);
        return res.json();
      })
      .then(setItems)
      .catch((err) => setError(`Could not reach the API: ${err.message}`));
  }, []);

  async function addItem(e: FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    const res = await fetch(`${API_URL}/items`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
    if (!res.ok) {
      setError(`Failed to add item (${res.status})`);
      return;
    }
    const item: Item = await res.json();
    setItems((prev) => [item, ...prev]);
    setName("");
    setError(null);
  }

  return (
    <main className="mx-auto flex w-full max-w-xl flex-1 flex-col gap-6 px-4 py-16">
      <h1 className="text-3xl font-semibold">Starter</h1>
      <p className="text-zinc-600 dark:text-zinc-400">
        Next.js → FastAPI → Postgres. Add an item to check the whole stack works.
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
          className="rounded-md bg-foreground px-4 py-2 font-medium text-background"
        >
          Add
        </button>
      </form>

      {error && <p className="text-red-600">{error}</p>}

      <ul className="flex flex-col divide-y divide-zinc-200 dark:divide-zinc-800">
        {items.map((item) => (
          <li key={item.id} className="flex justify-between py-2">
            <span>{item.name}</span>
            <span className="text-sm text-zinc-500">
              {new Date(item.created_at).toLocaleString()}
            </span>
          </li>
        ))}
      </ul>
    </main>
  );
}
