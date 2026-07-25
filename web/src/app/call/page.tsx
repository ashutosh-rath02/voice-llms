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

interface TranscriptEntry {
  id: string;
  text: string;
  final: boolean;
  isAgent: boolean;
  at: number;
}

/** Collects live transcription segments (both parties) published into the room.
 *  Partials arrive with final=false and are replaced in place as they firm up —
 *  keyed by segment id, so an updated segment overwrites its earlier version. */
function useTranscript(): TranscriptEntry[] {
  const room = useRoomContext();
  const [entries, setEntries] = useState<Map<string, TranscriptEntry>>(new Map());

  useEffect(() => {
    const handler = (segments: TranscriptionSegment[], participant?: Participant) => {
      setEntries((prev) => {
        const next = new Map(prev);
        for (const s of segments) {
          next.set(s.id, {
            id: s.id,
            text: s.text,
            final: s.final,
            isAgent: participant?.isAgent ?? false,
            at: next.get(s.id)?.at ?? s.firstReceivedTime ?? Date.now(),
          });
        }
        return next;
      });
    };
    room.on(RoomEvent.TranscriptionReceived, handler);
    return () => {
      room.off(RoomEvent.TranscriptionReceived, handler);
    };
  }, [room]);

  return [...entries.values()].sort((a, b) => a.at - b.at);
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
        {transcript.map((e) => (
          <div key={e.id} className={`flex ${e.isAgent ? "justify-start" : "justify-end"}`}>
            <div
              className={`max-w-[75%] rounded-2xl px-4 py-2 text-sm ${
                e.isAgent ? "bg-slate-800 text-slate-100" : "bg-sky-700 text-white"
              } ${e.final ? "" : "opacity-60"}`}
            >
              <span className="mb-0.5 block text-[10px] uppercase tracking-wide opacity-60">
                {e.isAgent ? "Agent" : "You"}
                {!e.final && " · …"}
              </span>
              {e.text}
            </div>
          </div>
        ))}
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

  useEffect(() => {
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
