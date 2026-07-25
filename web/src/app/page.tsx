"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { apiFetch, logout, UnauthorizedError } from "@/lib/api";
import { ConversationSummary, UserOut } from "@/lib/types";

function fmtTime(iso: string | null): string {
  return iso ? new Date(iso).toLocaleString() : "—";
}

function duration(a: string | null, b: string | null): string {
  if (!a || !b) return "—";
  const s = Math.round((new Date(b).getTime() - new Date(a).getTime()) / 1000);
  return `${Math.floor(s / 60)}m ${s % 60}s`;
}

const STATUS_STYLE: Record<string, string> = {
  completed: "bg-emerald-900/60 text-emerald-300",
  active: "bg-sky-900/60 text-sky-300",
  failed: "bg-red-900/60 text-red-300",
  abandoned: "bg-slate-800 text-slate-400",
};

export default function HomePage() {
  const router = useRouter();
  const [user, setUser] = useState<UserOut | null>(null);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        setUser(await apiFetch<UserOut>("/auth/me"));
        setConversations(await apiFetch<ConversationSummary[]>("/conversations"));
      } catch (err) {
        if (err instanceof UnauthorizedError) router.replace("/login");
        else setError("Could not load conversations — is the API running?");
      }
    })();
  }, [router]);

  if (!user) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-400">
        {error ?? "Loading…"}
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-950 p-6 text-slate-100">
      <div className="mx-auto max-w-4xl space-y-6">
        <header className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold">Voice AI Support</h1>
            <p className="text-sm text-slate-400">
              {user.full_name} · {user.role}
            </p>
          </div>
          <div className="flex gap-3">
            <Link
              href="/call"
              className="rounded-lg bg-sky-600 px-4 py-2 font-medium text-white hover:bg-sky-500"
            >
              Start voice call
            </Link>
            <button
              onClick={async () => {
                await logout();
                router.replace("/login");
              }}
              className="rounded-lg border border-slate-700 px-4 py-2 text-slate-300 hover:bg-slate-800"
            >
              Sign out
            </button>
          </div>
        </header>

        <section className="rounded-2xl border border-slate-800 bg-slate-900">
          <h2 className="border-b border-slate-800 px-5 py-3 text-sm font-medium text-slate-300">
            Conversations
          </h2>
          {conversations.length === 0 ? (
            <p className="px-5 py-8 text-center text-sm text-slate-500">
              No conversations yet — start your first voice call.
            </p>
          ) : (
            <ul className="divide-y divide-slate-800">
              {conversations.map((c) => (
                <li key={c.id}>
                  <Link
                    href={`/conversations/${c.id}`}
                    className="flex items-center justify-between px-5 py-3 hover:bg-slate-800/50"
                  >
                    <div>
                      <p className="font-mono text-sm">{c.room_name ?? c.id.slice(0, 8)}</p>
                      <p className="text-xs text-slate-500">
                        {fmtTime(c.started_at ?? c.created_at)} · {c.channel} ·{" "}
                        {duration(c.started_at, c.ended_at)}
                      </p>
                    </div>
                    <span
                      className={`rounded-full px-2.5 py-0.5 text-xs ${STATUS_STYLE[c.status] ?? "bg-slate-800"}`}
                    >
                      {c.status}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </main>
  );
}
