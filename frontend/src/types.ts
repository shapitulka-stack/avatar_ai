export interface StyleCard {
  id: string;
  name: string;
  description: string;
  preview_image: string;
  enabled: boolean;
  tags: string[];
}

export interface FaceProfile {
  id: string;
  label: string;
  image_url: string;
  preview_url: string | null;
  created_at: string;
  updated_at: string;
}

export interface FaceProfileListResponse {
  items: FaceProfile[];
}

export interface AvatarSummary {
  id: string;
  name: string;
  role: string;
  tone: string;
  summary: string;
}

export interface AvatarDetail extends AvatarSummary {
  system_prompt: string;
  memory: string[];
  starter_messages: string[];
}

export type ChatRole = "system" | "user" | "assistant";

export interface ChatMessage {
  role: ChatRole;
  content: string;
}

export interface ChatMemoryState {
  summary: string;
  known_facts: string[];
  relationship_state: string;
  active_topics: string[];
  last_updated: string | null;
}

export interface ChatSession {
  session_id: string;
  avatar_id: string;
  avatar_name: string;
  created_at: string;
  updated_at: string;
  messages: ChatMessage[];
  memory: ChatMemoryState;
}

export interface ChatResponse {
  avatar_id: string;
  avatar_name: string;
  reply: string;
  session_id: string | null;
  session: ChatSession | null;
}

export type JobStatus = "queued" | "running" | "succeeded" | "failed";

export interface ResultAsset {
  index: number;
  image_url: string;
  thumb_url: string;
  seed: number | null;
  width: number | null;
  height: number | null;
}

export interface JobDetail {
  job_id: string;
  status: JobStatus;
  source: "web" | "telegram_webapp";
  style_id: string;
  guest_session_id: string | null;
  telegram_user_id: number | null;
  input_image_url: string;
  input_preview_url: string | null;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  queue_tier: "free" | "premium";
  queue_position: number | null;
  jobs_ahead: number;
  estimated_wait_seconds: number;
  user_pending_jobs: number;
  max_pending_per_user: number;
  results: ResultAsset[];
}

export interface JobCreateResponse {
  job_id: string;
  status: JobStatus;
  poll_url: string;
  result_url: string;
  guest_session_id: string | null;
  queue_tier: "free" | "premium";
  queue_position: number | null;
  jobs_ahead: number;
  estimated_wait_seconds: number;
  user_pending_jobs: number;
  max_pending_per_user: number;
}

export interface JobListResponse {
  items: JobDetail[];
}
