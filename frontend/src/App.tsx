import { ChangeEvent, useEffect, useMemo, useState } from "react";

import { assetUrl, createJob, fetchFaceProfiles, fetchJob, fetchStyles } from "./api";
import FaceProfilePanel from "./FaceProfilePanel";
import type { JobDetail, ResultAsset, StyleCard } from "./types";

const GUEST_SESSION_KEY = "avatar_ai_guest_session";
const PENDING_STATUSES = new Set<JobDetail["status"]>(["queued", "running"]);

const STYLE_COPY: Record<string, Pick<StyleCard, "name" | "description" | "tags">> = {
  "anime-neon": {
    name: "Anime Neon",
    description: "Яркий аниме-образ с неоном.",
    tags: ["anime", "neon", "pop"],
  },
  "cinematic-pro": {
    name: "Cinematic Pro",
    description: "Киношный портрет с дорогим светом.",
    tags: ["cinema", "portrait", "clean"],
  },
  "cyber-commander": {
    name: "Cyber Commander",
    description: "Футуристичный sci-fi образ.",
    tags: ["cyber", "future", "bold"],
  },
  "fantasy-warden": {
    name: "Fantasy Warden",
    description: "Эпический fantasy-кадр.",
    tags: ["fantasy", "hero", "epic"],
  },
  "founder-brand": {
    name: "Founder Brand",
    description: "Чистый брендовый портрет.",
    tags: ["brand", "editorial", "clean"],
  },
  "velvet-royal": {
    name: "Velvet Royal",
    description: "Эффектный luxury-образ.",
    tags: ["royal", "luxury", "art"],
  },
};

function localizeStyle(style: StyleCard): StyleCard {
  const translation = STYLE_COPY[style.id];
  if (!translation) {
    return style;
  }

  return {
    ...style,
    name: translation.name,
    description: translation.description,
    tags: translation.tags,
  };
}

function currentJobIdFromUrl(): string {
  const url = new URL(window.location.href);
  return url.searchParams.get("job") || "";
}

function updateJobInUrl(jobId: string | null): void {
  const url = new URL(window.location.href);
  if (jobId) {
    url.searchParams.set("job", jobId);
  } else {
    url.searchParams.delete("job");
  }
  window.history.replaceState({}, "", url);
}

function humanStatus(status?: JobDetail["status"]): string {
  switch (status) {
    case "queued":
      return "В очереди";
    case "running":
      return "Генерируем";
    case "succeeded":
      return "Готово";
    case "failed":
      return "Ошибка";
    default:
      return "Подготовка";
  }
}

function formatWait(seconds?: number | null): string {
  if (!seconds || seconds <= 0) {
    return "Почти сразу";
  }

  const minutes = Math.max(1, Math.ceil(seconds / 60));
  return minutes === 1 ? "Около 1 мин" : `Около ${minutes} мин`;
}

function App() {
  const telegramInitData = useMemo(() => window.Telegram?.WebApp?.initData || "", []);
  const isTelegram = telegramInitData.length > 0;

  const [styles, setStyles] = useState<StyleCard[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [filePreview, setFilePreview] = useState<string>("");
  const [savedFacePreview, setSavedFacePreview] = useState<string>("");
  const [selectedStyleId, setSelectedStyleId] = useState<string>("");
  const [selectedFaceProfileId, setSelectedFaceProfileId] = useState<string>("");
  const [guestSessionId, setGuestSessionId] = useState<string>(() => localStorage.getItem(GUEST_SESSION_KEY) || "");
  const [currentJobId, setCurrentJobId] = useState<string>(currentJobIdFromUrl());
  const [currentJob, setCurrentJob] = useState<JobDetail | null>(null);
  const [featuredResultIndex, setFeaturedResultIndex] = useState<number>(0);
  const [sheetStyleId, setSheetStyleId] = useState<string | null>(null);
  const [sheetOpen, setSheetOpen] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);
  const [submittingStyleId, setSubmittingStyleId] = useState<string>("");
  const [error, setError] = useState<string>("");

  const styleById = useMemo(() => new Map(styles.map((style): [string, StyleCard] => [style.id, style])), [styles]);
  const hasFaceSource = Boolean(file || selectedFaceProfileId);
  const isQueueView = Boolean(currentJob && PENDING_STATUSES.has(currentJob.status));
  const isResultView = Boolean(currentJob && !PENDING_STATUSES.has(currentJob.status));
  const currentStyle = styleById.get(currentJob?.style_id || selectedStyleId) || null;
  const activeSheetStyle = sheetStyleId ? styleById.get(sheetStyleId) || null : null;
  const featuredResult: ResultAsset | null = currentJob?.results[featuredResultIndex] || currentJob?.results[0] || null;
  const portraitPreview = filePreview || savedFacePreview || (currentJob?.input_preview_url ? assetUrl(currentJob.input_preview_url) : "");

  useEffect(() => {
    const webApp = window.Telegram?.WebApp;
    webApp?.ready();
    webApp?.expand?.();
  }, []);

  useEffect(() => {
    if (isTelegram || guestSessionId) {
      return;
    }

    const nextGuestSessionId = crypto.randomUUID();
    localStorage.setItem(GUEST_SESSION_KEY, nextGuestSessionId);
    setGuestSessionId(nextGuestSessionId);
  }, [guestSessionId, isTelegram]);

  useEffect(() => () => {
    if (filePreview) {
      URL.revokeObjectURL(filePreview);
    }
  }, [filePreview]);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");

    fetchStyles()
      .then((items) => {
        if (!active) {
          return;
        }

        const enabledStyles = items.filter((style) => style.enabled).map(localizeStyle);
        setStyles(enabledStyles);
        if (!selectedStyleId && enabledStyles[0]) {
          setSelectedStyleId(enabledStyles[0].id);
        }
        if (!enabledStyles.length) {
          setError("Не нашли шаблоны.");
        }
      })
      .catch((reason: unknown) => {
        if (active) {
          setError(reason instanceof Error ? reason.message : "Не удалось загрузить ленту.");
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
    if (!isTelegram && !guestSessionId) {
      return;
    }

    let active = true;

    fetchFaceProfiles({
      guestSessionId: isTelegram ? undefined : guestSessionId,
      telegramInitData: isTelegram ? telegramInitData : undefined,
    })
      .then((items) => {
        if (!active || !items.length || filePreview) {
          return;
        }

        if (!selectedFaceProfileId) {
          setSelectedFaceProfileId(items[0].id);
        }
        setSavedFacePreview(items[0].preview_url || items[0].image_url);
      })
      .catch(() => {
        if (active) {
          setSavedFacePreview("");
        }
      });

    return () => {
      active = false;
    };
  }, [filePreview, guestSessionId, isTelegram, selectedFaceProfileId, telegramInitData]);

  useEffect(() => {
    if (!currentJobId) {
      setCurrentJob(null);
      return;
    }

    let active = true;
    let timer: number | undefined;

    const loadJob = async () => {
      try {
        const job = await fetchJob(currentJobId);
        if (!active) {
          return;
        }

        setCurrentJob(job);
        if (PENDING_STATUSES.has(job.status)) {
          timer = window.setTimeout(() => {
            void loadJob();
          }, 3000);
        }
      } catch (reason) {
        if (active) {
          setError(reason instanceof Error ? reason.message : "Не удалось загрузить задачу.");
        }
      }
    };

    void loadJob();

    return () => {
      active = false;
      if (timer) {
        window.clearTimeout(timer);
      }
    };
  }, [currentJobId]);

  useEffect(() => {
    setFeaturedResultIndex(0);
  }, [currentJob?.job_id, currentJob?.results?.length]);

  function clearTemporaryUpload(): void {
    if (filePreview) {
      URL.revokeObjectURL(filePreview);
    }
    setFile(null);
    setFilePreview("");
  }

  function onFileChange(event: ChangeEvent<HTMLInputElement>): void {
    const nextFile = event.target.files?.[0] || null;
    event.target.value = "";
    setError("");
    clearTemporaryUpload();

    if (nextFile) {
      setFile(nextFile);
      setFilePreview(URL.createObjectURL(nextFile));
    }
  }

  function handleSelectFaceProfile(profileId: string): void {
    setSelectedFaceProfileId(profileId);
    if (file || filePreview) {
      clearTemporaryUpload();
    }
  }

  function handleSelectedFacePreviewChange(previewUrl: string | null): void {
    setSavedFacePreview(previewUrl || "");
  }

  function openStyleSheet(styleId: string): void {
    setSelectedStyleId(styleId);
    setSheetStyleId(styleId);
    setSheetOpen(true);
  }

  function openFaceSheet(): void {
    setSheetStyleId(null);
    setSheetOpen(true);
  }

  function closeSheet(): void {
    setSheetOpen(false);
  }

  async function submitStyle(styleId: string): Promise<void> {
    setSelectedStyleId(styleId);
    setError("");
    setSubmittingStyleId(styleId);

    try {
      const response = await createJob({
        file: file || undefined,
        faceProfileId: file ? undefined : selectedFaceProfileId,
        styleId,
        source: isTelegram ? "telegram_webapp" : "web",
        guestSessionId: isTelegram ? undefined : guestSessionId || undefined,
        telegramInitData: isTelegram ? telegramInitData : undefined,
      });

      if (response.guest_session_id) {
        localStorage.setItem(GUEST_SESSION_KEY, response.guest_session_id);
        setGuestSessionId(response.guest_session_id);
      }

      setSheetOpen(false);
      setCurrentJobId(response.job_id);
      updateJobInUrl(response.job_id);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не удалось поставить задачу в очередь.");
    } finally {
      setSubmittingStyleId("");
    }
  }

  function dismissCurrentJob(): void {
    setCurrentJobId("");
    setCurrentJob(null);
    setFeaturedResultIndex(0);
    setError("");
    updateJobInUrl(null);
  }

  return (
    <div className="simple-shell feed-only-shell">
      <div className="simple-shell__glow simple-shell__glow--warm" />
      <div className="simple-shell__glow simple-shell__glow--cool" />

      {isQueueView && currentJob ? (
        <section className="focus-screen">
          <span className="eyebrow">Очередь</span>
          <h1>{currentJob.status === "running" ? "Делаем кадр" : "Поставили в очередь"}</h1>
          <p className="focus-screen__text">
            {currentJob.status === "running"
              ? "Генерация уже идет."
              : `Позиция ${currentJob.queue_position ?? "скоро запуск"}, впереди ${currentJob.jobs_ahead}, ждать ${formatWait(currentJob.estimated_wait_seconds)}.`}
          </p>

          <div className="focus-stats">
            <div className="focus-stat">
              <span>Статус</span>
              <strong>{humanStatus(currentJob.status)}</strong>
            </div>
            <div className="focus-stat">
              <span>Шаблон</span>
              <strong>{currentStyle?.name || currentJob.style_id}</strong>
            </div>
            <div className="focus-stat">
              <span>Ожидание</span>
              <strong>{formatWait(currentJob.estimated_wait_seconds)}</strong>
            </div>
            <div className="focus-stat">
              <span>Лимит</span>
              <strong>{currentJob.user_pending_jobs}/{currentJob.max_pending_per_user}</strong>
            </div>
          </div>

          <div className="focus-actions">
            <button type="button" className="secondary-button" onClick={dismissCurrentJob}>
              Назад к ленте
            </button>
          </div>
        </section>
      ) : null}

      {isResultView && currentJob ? (
        <section className="focus-screen">
          <span className="eyebrow">{currentJob.status === "failed" ? "Ошибка" : "Готово"}</span>
          <h1>{currentJob.status === "failed" ? "Не получилось" : "Результат готов"}</h1>
          <p className="focus-screen__text">
            {currentJob.status === "failed"
              ? currentJob.error_message || "Попробуй еще раз."
              : "Можно открыть вариант в полном размере или вернуться к ленте."}
          </p>

          {currentJob.status === "failed" ? (
            <div className="focus-actions">
              <button type="button" className="secondary-button" onClick={dismissCurrentJob}>
                Назад к ленте
              </button>
            </div>
          ) : featuredResult ? (
            <>
              <div className="result-showcase">
                <a
                  className="result-showcase__main"
                  href={assetUrl(featuredResult.image_url)}
                  target="_blank"
                  rel="noreferrer"
                >
                  <img
                    src={assetUrl(featuredResult.image_url)}
                    alt={`Вариант ${featuredResult.index + 1}`}
                    loading="eager"
                    decoding="async"
                    fetchPriority="high"
                  />
                </a>

                <div className="result-showcase__rail">
                  {currentJob.results.map((result) => (
                    <button
                      type="button"
                      key={result.index}
                      className={`result-mini ${featuredResult.index === result.index ? "is-active" : ""}`}
                      onClick={() => setFeaturedResultIndex(result.index)}
                    >
                      <img
                        src={assetUrl(result.thumb_url)}
                        alt={`Вариант ${result.index + 1}`}
                        loading="lazy"
                        decoding="async"
                        sizes="(max-width: 760px) 45vw, 160px"
                      />
                      <span>Вариант {result.index + 1}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div className="focus-actions">
                <button type="button" className="secondary-button" onClick={dismissCurrentJob}>
                  Назад к ленте
                </button>
                {currentStyle ? (
                  <button
                    type="button"
                    className="primary-button"
                    disabled={!hasFaceSource || Boolean(submittingStyleId)}
                    onClick={() => void submitStyle(currentStyle.id)}
                  >
                    {submittingStyleId === currentStyle.id ? "Ставим..." : "Сделать еще"}
                  </button>
                ) : null}
              </div>
            </>
          ) : null}
        </section>
      ) : null}

      {!isQueueView && !isResultView ? (
        <>
            <div className="gallery-topbar">
              <button type="button" className="face-entry-button" onClick={openFaceSheet}>
                {filePreview ? <img src={filePreview} alt="Ваше лицо" /> : null}
                {!filePreview && savedFacePreview ? <img src={assetUrl(savedFacePreview)} alt="Ваше лицо" /> : null}
                {!filePreview && !savedFacePreview ? <span className="face-entry-button__dot" /> : null}
                <strong>Мое лицо</strong>
              </button>
            </div>

          {error ? <div className="error-banner gallery-error">{error}</div> : null}

          <section className="feed-gallery">
            {styles.map((style) => {
              const isSelected = selectedStyleId === style.id;
              return (
                <article key={style.id} className={`feed-card feed-card--gallery ${isSelected ? "is-selected" : ""}`}>
                  <button
                    type="button"
                    className="feed-card__tap"
                    onClick={() => setSelectedStyleId(style.id)}
                  >
                    <div className="feed-card__media">
                      <img
                        src={assetUrl(style.preview_image)}
                        alt={style.name}
                        loading="lazy"
                        decoding="async"
                        sizes="(max-width: 760px) 100vw, (max-width: 1180px) 50vw, 33vw"
                      />
                    </div>
                    <div className="feed-card__overlay">
                      <div className="feed-card__copy">
                        <h3>{style.name}</h3>
                      </div>
                    </div>
                  </button>

                  {isSelected ? (
                    <div className="feed-card__actionbar">
                      <button
                        type="button"
                        className="card-action-button"
                        disabled={Boolean(submittingStyleId)}
                        onClick={() => {
                          if (hasFaceSource) {
                            void submitStyle(style.id);
                            return;
                          }
                          openStyleSheet(style.id);
                        }}
                      >
                        {submittingStyleId === style.id ? "Ставим..." : "Вставить себя"}
                      </button>
                    </div>
                  ) : null}
                </article>
              );
            })}
          </section>

          {sheetOpen ? (
            <div className="sheet-backdrop" onClick={closeSheet}>
              <section className="bottom-sheet" onClick={(event) => event.stopPropagation()}>
                <div className="bottom-sheet__grabber" />

                {activeSheetStyle ? (
                  <div className="sheet-style-preview">
                    <img src={assetUrl(activeSheetStyle.preview_image)} alt={activeSheetStyle.name} decoding="async" />
                  </div>
                ) : null}

                <div className="bottom-sheet__head">
                  <div>
                    <span className="eyebrow">{activeSheetStyle ? "Шаблон" : "Мое лицо"}</span>
                    <h2>{activeSheetStyle ? activeSheetStyle.name : "Выбери лицо"}</h2>
                  </div>
                </div>

                <div className="sheet-face-status">
                  <div className="sheet-face-status__chip">
                    {filePreview ? <img src={filePreview} alt="Выбранное лицо" /> : <span className="sheet-face-status__placeholder" />}
                    <div>
                      <strong>{hasFaceSource ? "Лицо выбрано" : "Лицо не выбрано"}</strong>
                      <span>{filePreview ? "Временное фото на этот запуск" : "Можно сохранить свое лицо или загрузить другое"}</span>
                    </div>
                  </div>
                </div>

                <div className="bottom-sheet__body">
                  <FaceProfilePanel
                    guestSessionId={isTelegram ? undefined : guestSessionId}
                    telegramInitData={isTelegram ? telegramInitData : undefined}
                    selectedFaceProfileId={selectedFaceProfileId}
                    onSelectFaceProfileId={handleSelectFaceProfile}
                    onSelectedFacePreviewChange={handleSelectedFacePreviewChange}
                  />

                  <section className="mini-override-panel">
                    <div className="mini-override-panel__head">
                      <span className="eyebrow">Другое лицо</span>
                      <p>На один раз</p>
                    </div>

                    {filePreview ? (
                      <div className="mini-override-panel__preview">
                        <img src={filePreview} alt="Другое лицо" decoding="async" />
                        <div className="mini-override-panel__actions">
                          <label className="ghost-button">
                            Сменить
                            <input type="file" accept="image/*" onChange={onFileChange} />
                          </label>
                          <button type="button" className="ghost-button" onClick={clearTemporaryUpload}>
                            Убрать
                          </button>
                        </div>
                      </div>
                    ) : (
                      <label className="mini-upload-button">
                        <input type="file" accept="image/*" onChange={onFileChange} />
                        <span>Загрузить фото</span>
                      </label>
                    )}
                  </section>
                </div>

                <div className="bottom-sheet__footer">
                  {activeSheetStyle ? (
                    <button
                      type="button"
                      className="primary-button"
                      disabled={!hasFaceSource || Boolean(submittingStyleId)}
                      onClick={() => void submitStyle(activeSheetStyle.id)}
                    >
                      {submittingStyleId === activeSheetStyle.id ? "Ставим..." : "Вставить себя"}
                    </button>
                  ) : (
                    <button type="button" className="secondary-button" onClick={closeSheet}>
                      Готово
                    </button>
                  )}
                </div>
              </section>
            </div>
          ) : null}
        </>
      ) : null}
    </div>
  );
}

export default App;
