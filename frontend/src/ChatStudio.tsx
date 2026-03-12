import { FormEvent, useEffect, useMemo, useState } from "react";

import { fetchAvatar, fetchAvatars, fetchChatSession, sendChatMessage } from "./api";
import type { AvatarDetail, AvatarSummary, ChatSession } from "./types";

const CHAT_SESSION_MAP_KEY = "avatar_ai_chat_sessions";
const RU_DATE_FORMAT = new Intl.DateTimeFormat("ru-RU", {
  dateStyle: "medium",
  timeStyle: "short",
});

type ChatSessionMap = Record<string, string>;

function readChatSessionMap(): ChatSessionMap {
  try {
    const raw = localStorage.getItem(CHAT_SESSION_MAP_KEY);
    if (!raw) {
      return {};
    }

    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

function formatMoment(value?: string | null): string {
  return value ? RU_DATE_FORMAT.format(new Date(value)) : "Только что";
}

function formatSessionId(sessionId?: string | null): string {
  return sessionId ? sessionId.slice(0, 8).toUpperCase() : "Новая";
}

function ChatStudio() {
  const [avatars, setAvatars] = useState<AvatarSummary[]>([]);
  const [selectedAvatarId, setSelectedAvatarId] = useState<string>("");
  const [avatarDetail, setAvatarDetail] = useState<AvatarDetail | null>(null);
  const [chatSessionMap, setChatSessionMap] = useState<ChatSessionMap>(() => readChatSessionMap());
  const [chatSession, setChatSession] = useState<ChatSession | null>(null);
  const [chatDraft, setChatDraft] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(true);
  const [chatLoading, setChatLoading] = useState<boolean>(false);
  const [chatSending, setChatSending] = useState<boolean>(false);
  const [error, setError] = useState<string>("");

  const avatarById = useMemo(() => new Map(avatars.map((avatar): [string, AvatarSummary] => [avatar.id, avatar])), [avatars]);
  const selectedAvatar = avatarById.get(selectedAvatarId) || null;
  const currentSessionId = selectedAvatarId ? chatSessionMap[selectedAvatarId] : "";
  const chatMessages = (chatSession?.messages || []).filter((message) => message.role !== "system");
  const runtimeMemory = chatSession?.memory || null;

  useEffect(() => {
    localStorage.setItem(CHAT_SESSION_MAP_KEY, JSON.stringify(chatSessionMap));
  }, [chatSessionMap]);

  useEffect(() => {
    let active = true;
    setLoading(true);

    fetchAvatars()
      .then((items) => {
        if (!active) {
          return;
        }

        setAvatars(items);
        if (!selectedAvatarId && items[0]) {
          setSelectedAvatarId(items[0].id);
        }
      })
      .catch((reason: unknown) => {
        if (active) {
          setError(reason instanceof Error ? reason.message : "Не удалось загрузить список аватаров.");
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!selectedAvatarId) {
      setAvatarDetail(null);
      setChatSession(null);
      return;
    }

    let active = true;
    const persistedSessionId = chatSessionMap[selectedAvatarId];
    setChatLoading(true);
    setError("");

    fetchAvatar(selectedAvatarId)
      .then(async (detail) => {
        if (!active) {
          return;
        }

        setAvatarDetail(detail);

        if (!persistedSessionId) {
          setChatSession(null);
          return;
        }

        try {
          const session = await fetchChatSession(selectedAvatarId, persistedSessionId);
          if (active) {
            setChatSession(session);
          }
        } catch {
          if (!active) {
            return;
          }

          setChatSession(null);
          setChatSessionMap((current) => {
            const next = { ...current };
            delete next[selectedAvatarId];
            return next;
          });
        }
      })
      .catch((reason: unknown) => {
        if (active) {
          setAvatarDetail(null);
          setChatSession(null);
          setError(reason instanceof Error ? reason.message : "Не удалось загрузить persona profile.");
        }
      })
      .finally(() => {
        if (active) {
          setChatLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [selectedAvatarId, currentSessionId]);

  async function handleSendChat(): Promise<void> {
    if (!selectedAvatarId) {
      setError("Сначала выберите аватар.");
      return;
    }

    const message = chatDraft.trim();
    if (!message) {
      return;
    }

    setChatSending(true);
    setError("");

    try {
      const response = await sendChatMessage({
        avatarId: selectedAvatarId,
        message,
        sessionId: currentSessionId || undefined,
      });

      setChatDraft("");
      if (response.session) {
        setChatSession(response.session);
      }
      if (response.session_id) {
        setChatSessionMap((current) => ({
          ...current,
          [selectedAvatarId]: response.session_id as string,
        }));
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не удалось отправить сообщение.");
    } finally {
      setChatSending(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    void handleSendChat();
  }

  function startFreshChat(): void {
    if (!selectedAvatarId) {
      return;
    }

    setChatSession(null);
    setChatDraft("");
    setError("");
    setChatSessionMap((current) => {
      const next = { ...current };
      delete next[selectedAvatarId];
      return next;
    });
  }

  return (
    <section className="focus-panel chat-panel">
      <div className="section-head">
        <div>
          <span className="eyebrow">Persona chat</span>
          <h2>Профиль, starter prompts и память сессии теперь видны в студии</h2>
        </div>
        <p>Локальный chat loop больше не спрятан в API. Можно выбрать аватара, продолжить прошлую сессию и увидеть, что именно он помнит.</p>
      </div>

      <div className="chat-layout">
        <div className="chat-sidebar">
          <div className="avatar-selector">
            {avatars.map((avatar) => (
              <button
                type="button"
                key={avatar.id}
                className={`avatar-chip ${selectedAvatarId === avatar.id ? "is-active" : ""}`}
                onClick={() => setSelectedAvatarId(avatar.id)}
              >
                <strong>{avatar.name}</strong>
                <span>{avatar.role}</span>
              </button>
            ))}
          </div>

          <div className="avatar-card-panel">
            <div className="avatar-card-head">
              <div>
                <span className="eyebrow">Выбранный аватар</span>
                <h3>{selectedAvatar ? selectedAvatar.name : "Пока не выбран"}</h3>
              </div>
              {selectedAvatar ? <span className="status-pill is-armed">{selectedAvatar.tone}</span> : null}
            </div>
            <p>{avatarDetail?.summary || selectedAvatar?.summary || "Выберите аватар, чтобы увидеть persona profile."}</p>

            {selectedAvatar ? (
              <div className="avatar-meta-grid">
                <div className="session-box">
                  <span>Роль</span>
                  <strong>{selectedAvatar.role}</strong>
                </div>
                <div className="session-box">
                  <span>Сессия</span>
                  <strong>{formatSessionId(currentSessionId)}</strong>
                </div>
              </div>
            ) : null}

            {avatarDetail?.starter_messages.length ? (
              <div className="starter-list">
                {avatarDetail.starter_messages.map((message) => (
                  <button type="button" key={message} className="starter-chip" onClick={() => setChatDraft(message)}>
                    {message}
                  </button>
                ))}
              </div>
            ) : null}
          </div>

          <div className="memory-card">
            <div className="memory-card__head">
              <div>
                <span className="eyebrow">Memory block</span>
                <h3>Что видит аватар</h3>
              </div>
              {runtimeMemory?.last_updated ? <span className="micro-pill">updated {formatMoment(runtimeMemory.last_updated)}</span> : null}
            </div>

            <div className="memory-group">
              <strong>Base profile memory</strong>
              {avatarDetail?.memory.length ? (
                <ul className="memory-list">
                  {avatarDetail.memory.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              ) : (
                <p className="memory-empty">У профиля пока нет сохраненных базовых фактов.</p>
              )}
            </div>

            <div className="memory-group">
              <strong>Session summary</strong>
              <p className="memory-summary">{runtimeMemory?.summary || "После первого сообщения здесь появится краткое состояние текущего диалога."}</p>
            </div>

            <div className="memory-grid">
              <div className="memory-group">
                <strong>Known facts</strong>
                {runtimeMemory?.known_facts.length ? (
                  <ul className="memory-list compact">
                    {runtimeMemory.known_facts.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="memory-empty">Пока пусто.</p>
                )}
              </div>

              <div className="memory-group">
                <strong>Active topics</strong>
                {runtimeMemory?.active_topics.length ? (
                  <div className="tag-row">
                    {runtimeMemory.active_topics.map((topic) => (
                      <span key={topic}>{topic}</span>
                    ))}
                  </div>
                ) : (
                  <p className="memory-empty">Появятся после разговора.</p>
                )}
              </div>
            </div>

            <div className="memory-group">
              <strong>Relationship state</strong>
              <p className="memory-summary">{runtimeMemory?.relationship_state || "Аватар пока ждет первого сообщения."}</p>
            </div>
          </div>
        </div>

        <div className="chat-main">
          <div className="chat-thread">
            {loading ? <div className="history-empty">Загружаем список аватаров...</div> : null}
            {chatLoading ? <div className="history-empty">Загружаем persona state...</div> : null}
            {!loading && !chatLoading && !selectedAvatar ? <div className="history-empty">Сначала выберите аватар.</div> : null}
            {!loading && !chatLoading && selectedAvatar && chatMessages.length === 0 ? (
              <div className="chat-empty-state">
                <strong>{avatarDetail?.name || selectedAvatar.name} готов к диалогу.</strong>
                <p>Начните с одного из starter prompts или напишите свой вопрос. Сессия сохранится локально и продолжится после перезагрузки.</p>
              </div>
            ) : null}
            {!loading &&
              !chatLoading &&
              chatMessages.map((message, index) => (
                <article key={`${message.role}-${index}`} className={`message-bubble is-${message.role}`}>
                  <div className="message-bubble__meta">
                    <strong>{message.role === "assistant" ? avatarDetail?.name || "Avatar" : "Вы"}</strong>
                    <span>{index === chatMessages.length - 1 ? formatMoment(chatSession?.updated_at) : ""}</span>
                  </div>
                  <p>{message.content}</p>
                </article>
              ))}
          </div>

          <form className="composer-panel" onSubmit={handleSubmit}>
            <label className="composer-field">
              <span className="eyebrow">Сообщение</span>
              <textarea
                value={chatDraft}
                onChange={(event) => setChatDraft(event.target.value)}
                placeholder={selectedAvatar ? `Напишите ${selectedAvatar.name.toLowerCase()}, что хотите сделать дальше...` : "Выберите аватар, чтобы начать"}
                rows={4}
                disabled={!selectedAvatar || chatSending}
              />
            </label>

            {error ? <div className="error-banner">{error}</div> : null}

            <div className="composer-actions">
              <div className="composer-meta-row">
                <span>{selectedAvatar ? `${selectedAvatar.name} · ${selectedAvatar.role}` : "Avatar not selected"}</span>
                <span>{chatSession ? `Последнее обновление: ${formatMoment(chatSession.updated_at)}` : "Новая локальная сессия"}</span>
              </div>
              <div className="composer-buttons">
                <button type="button" className="secondary-button" onClick={startFreshChat} disabled={!selectedAvatar && !chatSession}>
                  Новая сессия
                </button>
                <button type="submit" className="primary-button" disabled={!selectedAvatar || !chatDraft.trim() || chatSending}>
                  {chatSending ? "Отправляем..." : "Отправить в persona chat"}
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>
    </section>
  );
}

export default ChatStudio;

