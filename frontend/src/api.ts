import type {
  AvatarDetail,
  AvatarSummary,
  ChatResponse,
  ChatSession,
  FaceProfile,
  FaceProfileListResponse,
  JobCreateResponse,
  JobDetail,
  JobListResponse,
  StyleCard,
} from "./types";

const rawApiBase = import.meta.env.VITE_API_BASE_URL || (typeof window !== "undefined" ? window.location.origin : "http://127.0.0.1:8000");
const API_BASE = rawApiBase.includes("://") ? rawApiBase : `https://${rawApiBase}`;

function buildUrl(path: string): string {
  return `${API_BASE}${path}`;
}

async function parseError(response: Response, fallback: string): Promise<Error> {
  const error = await response.json().catch(() => ({ detail: fallback }));
  return new Error(error.detail || fallback);
}

export async function fetchStyles(): Promise<StyleCard[]> {
  const response = await fetch(buildUrl("/api/templates"));
  if (!response.ok) {
    throw await parseError(response, "Could not load templates.");
  }
  return response.json();
}

export async function fetchFaceProfiles(params: { guestSessionId?: string; telegramInitData?: string }): Promise<FaceProfile[]> {
  const search = new URLSearchParams();
  if (params.guestSessionId) {
    search.set("guest_session_id", params.guestSessionId);
  }
  if (params.telegramInitData) {
    search.set("telegram_init_data", params.telegramInitData);
  }

  const response = await fetch(buildUrl(`/api/me/face-profiles?${search.toString()}`));
  if (!response.ok) {
    throw await parseError(response, "Could not load face profiles.");
  }

  const body: FaceProfileListResponse = await response.json();
  return body.items;
}

export async function createFaceProfile(params: {
  file: File;
  label?: string;
  guestSessionId?: string;
  telegramInitData?: string;
}): Promise<FaceProfile> {
  const form = new FormData();
  form.append("photo", params.file);
  form.append("label", params.label || "My face");
  if (params.guestSessionId) {
    form.append("guest_session_id", params.guestSessionId);
  }
  if (params.telegramInitData) {
    form.append("telegram_init_data", params.telegramInitData);
  }

  const response = await fetch(buildUrl("/api/me/face-profiles"), {
    method: "POST",
    body: form,
  });

  if (!response.ok) {
    throw await parseError(response, "Could not save face profile.");
  }

  return response.json();
}

export async function fetchAvatars(): Promise<AvatarSummary[]> {
  const response = await fetch(buildUrl("/api/avatars"));
  if (!response.ok) {
    throw await parseError(response, "Could not load avatars.");
  }
  return response.json();
}

export async function fetchAvatar(avatarId: string): Promise<AvatarDetail> {
  const response = await fetch(buildUrl(`/api/avatars/${avatarId}`));
  if (!response.ok) {
    throw await parseError(response, "Could not load avatar details.");
  }
  return response.json();
}

export async function fetchChatSession(avatarId: string, sessionId: string): Promise<ChatSession> {
  const response = await fetch(buildUrl(`/api/chat/sessions/${avatarId}/${sessionId}`));
  if (!response.ok) {
    throw await parseError(response, "Could not load chat session.");
  }
  return response.json();
}

export async function sendChatMessage(params: {
  avatarId: string;
  message: string;
  sessionId?: string;
  temperature?: number;
}): Promise<ChatResponse> {
  const response = await fetch(buildUrl("/api/chat"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      avatar_id: params.avatarId,
      message: params.message,
      session_id: params.sessionId,
      temperature: params.temperature ?? 0.7,
    }),
  });

  if (!response.ok) {
    throw await parseError(response, "Could not send chat message.");
  }

  return response.json();
}

export async function createJob(params: {
  file?: File;
  faceProfileId?: string;
  styleId: string;
  source: "web" | "telegram_webapp";
  guestSessionId?: string;
  telegramInitData?: string;
}): Promise<JobCreateResponse> {
  const form = new FormData();
  if (params.file) {
    form.append("photo", params.file);
  }
  if (params.faceProfileId) {
    form.append("face_profile_id", params.faceProfileId);
  }
  form.append("style_id", params.styleId);
  form.append("source", params.source);
  if (params.guestSessionId) {
    form.append("guest_session_id", params.guestSessionId);
  }
  if (params.telegramInitData) {
    form.append("telegram_init_data", params.telegramInitData);
  }

  const response = await fetch(buildUrl("/api/jobs"), {
    method: "POST",
    body: form,
  });

  if (!response.ok) {
    throw await parseError(response, "Could not create job.");
  }

  return response.json();
}

export async function fetchJob(jobId: string): Promise<JobDetail> {
  const response = await fetch(buildUrl(`/api/jobs/${jobId}`));
  if (!response.ok) {
    throw await parseError(response, "Could not load job.");
  }
  return response.json();
}

export async function fetchMyJobs(params: { guestSessionId?: string; telegramInitData?: string }): Promise<JobListResponse> {
  const search = new URLSearchParams();
  if (params.guestSessionId) {
    search.set("guest_session_id", params.guestSessionId);
  }
  if (params.telegramInitData) {
    search.set("telegram_init_data", params.telegramInitData);
  }

  const response = await fetch(buildUrl(`/api/me/jobs?${search.toString()}`));
  if (!response.ok) {
    throw await parseError(response, "Could not load job history.");
  }
  return response.json();
}

export function assetUrl(path: string): string {
  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }
  return `${API_BASE}${path}`;
}
