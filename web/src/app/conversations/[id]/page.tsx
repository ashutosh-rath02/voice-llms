"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { apiFetch, UnauthorizedError } from "@/lib/api";
import { ConversationDetail, LatencyOut, RetrievalEventOut } from "@/lib/types";

function LatencyChips({ latency }: { latency: LatencyOut }) {
  const chips: [string, number | null][] = [
    ["STT", latency.stt_final_ms],
    ["LLM", latency.llm_first_token_ms],
    ["TTS", latency.tts_first_audio_ms],
    ["total", latency.total_response_ms],
  ];
  return (
    <div className="mt-1.5 flex gap-1.5">
      {chips.map(
        ([label, value]) =>
          value !== null && (
            <span
              key={label}
              className={`rounded px-1.5 py-0.5 font-mono text-[10px] ${
                label === "total"
                  ? value > 2000
                    ? "bg-amber-900/60 text-amber-300"
                    : "bg-emerald-900/60 text-emerald-300"
                  : "bg-slate-800 text-slate-400"
              }`}
            >
              {label} {value}ms
            </span>
          ),
      )}
    </div>
  );
}

function RetrievalEvidence({ events }: { events: RetrievalEventOut[] }) {
  if (events.length === 0) return null;
  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
      <h2 className="mb-2 text-sm font-medium text-slate-300">
        Knowledge lookups ({events.length})
      </h2>
      <div className="space-y-3">
        {events.map((e, i) => (
          <div key={i} className="rounded-lg bg-slate-800/50 p-3 text-sm">
            <div className="flex items-center justify-between">
              <p className="font-medium text-slate-200">&ldquo;{e.query}&rdquo;</p>
              <span className="font-mono text-[10px] text-slate-500">{e.latency_ms}ms</span>
            </div>
            {e.results.length === 0 ? (
              <p className="mt-1.5 text-xs text-amber-400">
                No relevant documentation found — agent should have said so, not guessed.
              </p>
            ) : (
              <ul className="mt-1.5 space-y-1">
                {e.results.map((r) => (
                  <li key={r.chunk_id} className="flex items-center gap-2 text-xs">
                    <span className="rounded bg-slate-700 px-1 py-0.5 font-mono text-[10px] text-slate-400">
                      {r.vector_rank && `v#${r.vector_rank}`}
                      {r.vector_rank && r.fts_rank && " "}
                      {r.fts_rank && `f#${r.fts_rank}`}
                    </span>
                    {r.document_url ? (
                      <a
                        href={r.document_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sky-400 hover:underline"
                      >
                        {r.document_title}
                      </a>
                    ) : (
                      <span className="text-slate-300">{r.document_title}</span>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

export default function ReplayPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [detail, setDetail] = useState<ConversationDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        setDetail(await apiFetch<ConversationDetail>(`/conversations/${id}`));
      } catch (err) {
        if (err instanceof UnauthorizedError) router.replace("/login");
        else setError("Conversation not found.");
      }
    })();
  }, [id, router]);

  if (error || !detail) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-400">
        {error ?? "Loading…"}
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-950 p-6 text-slate-100">
      <div className="mx-auto max-w-3xl space-y-6">
        <header className="space-y-1">
          <Link href="/" className="text-sm text-sky-400 hover:underline">
            ← Back to conversations
          </Link>
          <h1 className="font-mono text-lg">{detail.room_name ?? detail.id}</h1>
          <p className="text-sm text-slate-400">
            {detail.status} · {detail.channel} · agent {detail.agent_version_label} ·{" "}
            {detail.started_at ? new Date(detail.started_at).toLocaleString() : "not started"}
          </p>
        </header>

        <section className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
          <h2 className="mb-2 text-sm font-medium text-slate-300">State timeline</h2>
          <div className="flex flex-wrap items-center gap-1.5 text-xs">
            {detail.state_events.map((e, i) => (
              <span key={i} className="flex items-center gap-1.5">
                {i > 0 && <span className="text-slate-600">→</span>}
                <span
                  className="rounded-full bg-slate-800 px-2.5 py-1 text-slate-300"
                  title={e.reason ?? undefined}
                >
                  {e.to_state}
                </span>
              </span>
            ))}
          </div>
        </section>

        <RetrievalEvidence events={detail.retrieval_events} />

        <section className="space-y-3">
          {detail.turns.map((t) => (
            <div
              key={t.turn_index}
              className={`flex ${t.role === "assistant" ? "justify-start" : "justify-end"}`}
            >
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm ${
                  t.role === "assistant" ? "bg-slate-800" : "bg-sky-700 text-white"
                }`}
              >
                <span className="mb-0.5 block text-[10px] uppercase tracking-wide opacity-60">
                  #{t.turn_index} · {t.role === "assistant" ? "Agent" : "Customer"}
                  {t.language && ` · ${t.language}`}
                  {t.interrupted && (
                    <span className="ml-1.5 rounded bg-red-900/70 px-1 py-0.5 text-red-300">
                      interrupted
                    </span>
                  )}
                </span>
                {t.content}
                {t.latency && <LatencyChips latency={t.latency} />}
                {t.partials.length > 0 && (
                  <details className="mt-1.5 text-xs opacity-70">
                    <summary className="cursor-pointer">
                      {t.partials.length} partial transcript{t.partials.length > 1 && "s"}
                    </summary>
                    <ul className="mt-1 list-inside list-disc space-y-0.5">
                      {t.partials.map((p, i) => (
                        <li key={i} className="font-mono">
                          {p}
                        </li>
                      ))}
                    </ul>
                  </details>
                )}
              </div>
            </div>
          ))}
        </section>
      </div>
    </main>
  );
}
