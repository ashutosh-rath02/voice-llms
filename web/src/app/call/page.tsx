"use client";

import {
  LiveKitRoom,
  RoomAudioRenderer,
  useConnectionState,
  useLocalParticipant,
  useRoomContext,
  useVoiceAssistant,
} from "@livekit/components-react";
import {
  ConnectionState,
  Participant,
  RoomEvent,
  TranscriptionSegment,
} from "livekit-client";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { apiFetch, UnauthorizedError } from "@/lib/api";
import { VoiceSession } from "@/lib/types";

interface TranscriptPart {
  id: string;
  text: string;
  final: boolean;
}

interface TranscriptBubble {
  key: string;
  isAgent: boolean;
  parts: TranscriptPart[];
  at: number;
}

/** Collects live transcription segments (both parties) published into the room.
 *
 * The STT provider emits a new "final" segment (with a new id) on every natural
 * pause — e.g. spelling out an email produces several finals, not one — while
 * the backend's own turn-detector correctly merges them into a single logical
 * turn before it ever reaches the LLM or the database. This hook mirrors that:
 * consecutive segments from the same speaker are grouped into one growing
 * bubble, and only a speaker change starts a new one. A segment matching the
 * id of the latest part updates that part in place (partial -> final refinement).
 */
function useTranscript(): TranscriptBubble[] {
  const room = useRoomContext();
  const [bubbles, setBubbles] = useState<TranscriptBubble[]>([]);

  useEffect(() => {
    const handler = (segments: TranscriptionSegment[], participant?: Participant) => {
      const isAgent = participant?.isAgent ?? false;
      setBubbles((prev) => {
        const next = [...prev];
        for (const s of segments) {
          const last = next[next.length - 1];
          const part: TranscriptPart = { id: s.id, text: s.text, final: s.final };
          const existingIndex = last?.parts.findIndex((p) => p.id === s.id) ?? -1;

          if (last && existingIndex !== -1) {
            const parts = [...last.parts];
            parts[existingIndex] = part;
            next[next.length - 1] = { ...last, parts };
          } else if (last && last.isAgent === isAgent) {
            next[next.length - 1] = { ...last, parts: [...last.parts, part] };
          } else {
            next.push({
              key: s.id,
              isAgent,
              parts: [part],
              at: s.firstReceivedTime ?? Date.now(),
            });
          }
        }
        return next;
      });
    };
    room.on(RoomEvent.TranscriptionReceived, handler);
    return () => {
      room.off(RoomEvent.TranscriptionReceived, handler);
    };
  }, [room]);

  return bubbles;
}

const AGENT_STATE_STYLE: Record<string, { label: string; cls: string }> = {
  listening: { label: "Listening", cls: "bg-emerald-900/60 text-emerald-300" },
  thinking: { label: "Thinking…", cls: "bg-amber-900/60 text-amber-300" },
  speaking: { label: "Speaking", cls: "bg-sky-900/60 text-sky-300 animate-pulse" },
  initializing: { label: "Starting…", cls: "bg-slate-800 text-slate-400" },
  connecting: { label: "Connecting…", cls: "bg-slate-800 text-slate-400" },
  disconnected: { label: "Offline", cls: "bg-slate-800 text-slate-500" },
};

function CallUI() {
  const room = useRoomContext();
  const connectionState = useConnectionState();
  const { state: agentState } = useVoiceAssistant();
  const { localParticipant, isMicrophoneEnabled } = useLocalParticipant();
  const transcript = useTranscript();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [transcript]);

  const stateStyle = AGENT_STATE_STYLE[agentState] ?? AGENT_STATE_STYLE.initializing;

  return (
    <div className="flex h-screen flex-col bg-slate-950 text-slate-100">
      {connectionState === ConnectionState.Reconnecting && (
        <div className="bg-amber-600 px-4 py-2 text-center text-sm font-medium text-black">
          Connection lost — reconnecting…
        </div>
      )}

      <header className="flex items-center justify-between border-b border-slate-800 px-6 py-4">
        <h1 className="font-semibold">Live voice session</h1>
        <span className={`rounded-full px-3 py-1 text-sm ${stateStyle.cls}`}>
          {stateStyle.label}
        </span>
      </header>

      <div className="flex-1 space-y-3 overflow-y-auto p-6">
        {transcript.length === 0 && (
          <p className="text-center text-sm text-slate-500">
            Say hello — the agent is {agentState === "listening" ? "listening" : "starting up"}.
          </p>
        )}
        {transcript.map((b) => {
          const text = b.parts.map((p) => p.text).join(" ");
          const isFinal = b.parts[b.parts.length - 1].final;
          return (
            <div key={b.key} className={`flex ${b.isAgent ? "justify-start" : "justify-end"}`}>
              <div
                className={`max-w-[75%] rounded-2xl px-4 py-2 text-sm ${
                  b.isAgent ? "bg-slate-800 text-slate-100" : "bg-sky-700 text-white"
                } ${isFinal ? "" : "opacity-60"}`}
              >
                <span className="mb-0.5 block text-[10px] uppercase tracking-wide opacity-60">
                  {b.isAgent ? "Agent" : "You"}
                  {!isFinal && " · …"}
                </span>
                {text}
              </div>
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>

      <footer className="flex items-center justify-center gap-4 border-t border-slate-800 p-4">
        <button
          onClick={() => localParticipant.setMicrophoneEnabled(!isMicrophoneEnabled)}
          className={`rounded-full px-5 py-2.5 font-medium ${
            isMicrophoneEnabled
              ? "bg-slate-800 text-slate-200 hover:bg-slate-700"
              : "bg-red-600 text-white hover:bg-red-500"
          }`}
        >
          {isMicrophoneEnabled ? "Mute" : "Unmute"}
        </button>
        <button
          onClick={() => room.disconnect()}
          className="rounded-full bg-red-600 px-5 py-2.5 font-medium text-white hover:bg-red-500"
        >
          End call
        </button>
      </footer>
    </div>
  );
}

export default function CallPage() {
  const router = useRouter();
  const [session, setSession] = useState<VoiceSession | null>(null);
  const [error, setError] = useState<string | null>(null);
  // POST /voice/token creates a conversation row — not idempotent. React
  // StrictMode double-mounts effects in dev, so guard against firing twice.
  const requested = useRef(false);

  useEffect(() => {
    if (requested.current) return;
    requested.current = true;
    (async () => {
      try {
        setSession(await apiFetch<VoiceSession>("/voice/token", { method: "POST" }));
      } catch (err) {
        if (err instanceof UnauthorizedError) router.replace("/login");
        else setError("Could not start a voice session. Is the backend running?");
      }
    })();
  }, [router]);

  if (error) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-950 text-red-400">
        {error}
      </main>
    );
  }
  if (!session) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-400">
        Preparing your session…
      </main>
    );
  }

  return (
    <LiveKitRoom
      serverUrl={session.url}
      token={session.token}
      connect
      audio
      video={false}
      onDisconnected={() => router.push(`/conversations/${session.conversation_id}`)}
      onMediaDeviceFailure={() =>
        setError("Microphone access failed — please allow the microphone and reload.")
      }
    >
      <CallUI />
      <RoomAudioRenderer />
    </LiveKitRoom>
  );
}
