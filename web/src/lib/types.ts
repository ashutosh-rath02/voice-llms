// Mirrors backend/app/schemas — the API contract from the client's side.

export interface UserOut {
  id: string;
  email: string;
  full_name: string;
  role: string;
}

export interface VoiceSession {
  token: string;
  url: string;
  room_name: string;
  conversation_id: string;
}

export interface LatencyOut {
  stt_final_ms: number | null;
  llm_first_token_ms: number | null;
  tts_first_audio_ms: number | null;
  total_response_ms: number | null;
}

export interface TurnOut {
  turn_index: number;
  role: "user" | "assistant";
  content: string;
  language: string | null;
  interrupted: boolean;
  created_at: string;
  latency: LatencyOut | null;
  partials: string[];
}

export interface StateEventOut {
  from_state: string | null;
  to_state: string;
  reason: string | null;
  created_at: string;
}

export interface RetrievalResultOut {
  chunk_id: string;
  document_title: string;
  document_url: string | null;
  score: number;
  vector_rank: number | null;
  fts_rank: number | null;
}

export interface RetrievalEventOut {
  query: string;
  strategy: string;
  latency_ms: number;
  created_at: string;
  results: RetrievalResultOut[];
}

export interface ConversationSummary {
  id: string;
  room_name: string | null;
  channel: string;
  status: string;
  outcome: string | null;
  customer_id: string | null;
  customer_name: string | null;
  started_at: string | null;
  ended_at: string | null;
  created_at: string;
}

export interface ConversationDetail extends ConversationSummary {
  agent_version_label: string;
  turns: TurnOut[];
  state_events: StateEventOut[];
  retrieval_events: RetrievalEventOut[];
}
