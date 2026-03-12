import { ChangeEvent, useEffect, useMemo, useRef, useState } from "react";

import { assetUrl, createJob, fetchJob, fetchMyJobs, fetchStyles } from "./api";
import FaceProfilePanel from "./FaceProfilePanel";
import type { JobDetail, ResultAsset, StyleCard } from "./types";

const GUEST_SESSION_KEY = "avatar_ai_guest_session";
const PENDING_STATUSES = new Set<JobDetail["status"]>(["queued", "running"]);
const RU_DATE_FORMAT = new Intl.DateTimeFormat("ru-RU", {
  dateStyle: "medium",
  timeStyle: "short",
});

const STYLE_COPY: Record<string, Pick<StyleCard, "name" | "description" | "tags">> = {
  "anime-neon": {
    name: "Anime Neon",
    description: "Яркий аниме-образ с неоном и эффектной подачей.",
    tags: ["anime", "neon", "pop"],
  },
  "cinematic-pro": {
    name: "Cinematic Pro",
    description: "Киношный портрет с дорогим светом и спокойным вайбом.",
    tags: ["cinema", "portrait", "clean"],
  },
  "cyber-commander": {
    name: "Cyber Commander",
    description: "Футуристичный sci-fi образ с мощной digital-энергией.",
    tags: ["cyber", "future", "bold"],
  },
  "fantasy-warden": {
    name: "Fantasy Warden",
    description: "Эпический fantasy-кадр с атмосферой героя.",
    tags: ["fantasy", "hero", "epic"],
  },
  "founder-brand": {
    name: "Founder Brand",
    description: "Чистый брендовый портрет для профиля и личного бренда.",
    tags: ["brand", "editorial", "clean"],
  },
  "velvet-royal": {
    name: "Velvet Royal",
    description: "Эффектный luxury-образ с глубоким светом и wow-подачей.",
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
      return "Генерируется";
    case "succeeded":
      return "Готово";
    case "failed":
      return "Ошибка";
    default:
      return "Подготовка";
  }
}

function formatMoment(value?: string | null): string {
  return value ? RU_DATE_FORMAT.format(new Date(value)) : "Пока нет";
}

function formatWait(seconds?: number | null): string {
  if (!seconds || seconds <= 0) {
    return "Почти сразу";
  }

  const minutes = Math.max(1, Math.ceil(seconds / 60));
  return minutes === 1 ? "Около 1 мин" : `Около ${minutes} мин`;
}

function pickHistoryImage(job: JobDetail): string | null {
  if (job.results[0]) {
    return assetUrl(job.results[0].thumb_url);
  }
  if (job.input_preview_url) {
    return assetUrl(job.input_preview_url);
  }
  return null;
}

function App() {
  const composerRef = useRef<HTMLElement | null>(null);
  const telegramInitData = useMemo(() => window.Telegram?.WebApp?.initData || "", []);
  const isTelegram = telegramInitData.length > 0;
  const [styles, setStyles] = useState<StyleCard[]>([]);
  const [history, setHistory] = useState<JobDetail[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [filePreview, setFilePreview] = useState<string>("");
  const [selectedStyleId, setSelectedStyleId] = useState<string>("");
  const [selectedFaceProfileId, setSelectedFaceProfileId] = useState<string>("");
  const [guestSessionId, setGuestSessionId] = useState<string>(() => localStorage.getItem(GUEST_SESSION_KEY) || "");
  const [currentJobId, setCurrentJobId] = useState<string>(currentJobIdFromUrl());
  const [currentJob, setCurrentJob] = useState<JobDetail | null>(null);
  const [featuredResultIndex, setFeaturedResultIndex] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string>("");

  const styleById = useMemo(() => new Map(styles.map((style): [string, StyleCard] => [style.id, style])), [styles]);
  const hasFaceSource = Boolean(file || selectedFaceProfileId);
  const currentStyle = styleById.get(currentJob?.style_id || selectedStyleId) || null;
  const featuredResult: ResultAsset | null = currentJob?.results[featuredResultIndex] || currentJob?.results[0] || null;
  const portraitPreview = filePreview || (currentJob?.input_preview_url ? assetUrl(currentJob.input_preview_url) : "");
  const isQueueView = Boolean(currentJob && PENDING_STATUSES.has(currentJob.status));
  const isResultView = Boolean(currentJob && !PENDING_STATUSES.has(currentJob.status));
  const actionHint = hasFaceSource
    ? "Лицо выбрано. Теперь можно просто нажимать на понравившийся шаблон."
    : "Сначала выбери лицо или загрузи фото, потом нажми «Вставить себя» на карточке.";

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
          setError("Не найдено ни одного доступного шаблона.");
        }
      })
      .catch((reason: unknown) => {
        if (active) {
          setError(reason instanceof Error ? reason.message : "Не удалось загрузить шаблоны.");
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

    fetchMyJobs({
      guestSessionId: isTelegram ? undefined : guestSessionId,
      telegramInitData: isTelegram ? telegramInitData : undefined,
    })
      .then((response) => {
        if (active) {
          setHistory(response.items);
        }
      })
      .catch(() => {
        if (active) {
          setHistory([]);
        }
      });

    return () => {
      active = false;
    };
  }, [currentJobId, currentJob?.status, guestSessionId, isTelegram, telegramInitData]);

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
          setError(reason instanceof Error ? reason.message : "Не удалось загрузить текущую задачу.");
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

  function focusSetup(): void {
    composerRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  }

  function clearTemporaryUpload(): void {
    if (filePreview) {
      URL.revokeObjectURL(filePreview);
    }
    setFile(null);
    setFilePreview("");
  }

  function onFileChange(event: ChangeEvent<HTMLInputElement>): void {
    const nextFile = event.target.files?.[0] || null;
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

  async function runStyle(styleId: string): Promise<void> {
    setSelectedStyleId(styleId);
    setError("");

    if (!file && !selectedFaceProfileId) {
      setError("Сначала добавь лицо, потом нажми «Вставить себя» еще раз.");
      focusSetup();
      return;
    }

    setSubmitting(true);

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

      setCurrentJobId(response.job_id);
      updateJobInUrl(response.job_id);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не удалось поставить задачу в очередь.");
    } finally {
      setSubmitting(false);
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
    <div className="simple-shell">
      <div className="simple-shell__glow simple-shell__glow--warm" />
      <div className="simple-shell__glow simple-shell__glow--cool" />

      {isQueueView && currentJob ? (
        <section className="focus-screen">
          <span className="eyebrow">Очередь</span>
          <h1>{currentJob.status === "running" ? "Делаем ваш кадр" : "Поставили в очередь"}</h1>
          <p className="focus-screen__text">
            {currentJob.status === "running"
              ? "Сервис уже собирает результат. Экран обновится автоматически."
              : `Сейчас позиция ${currentJob.queue_position ?? "скоро запуск"}, впереди ${currentJob.jobs_ahead} задач, ожидание ${formatWait(currentJob.estimated_wait_seconds)}.`}
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

          <div className="focus-preview">
            {currentStyle ? (
              <div className="focus-preview__card">
                <img src={assetUrl(currentStyle.preview_image)} alt={currentStyle.name} decoding="async" />
                <span>Шаблон</span>
              </div>
            ) : null}
            {portraitPreview ? (
              <div className="focus-preview__card">
                <img src={portraitPreview} alt="Лицо для генерации" decoding="async" />
                <span>Ваше лицо</span>
              </div>
            ) : null}
          </div>

          <div className="focus-actions">
            <button type="button" className="secondary-button" onClick={dismissCurrentJob}>
              Вернуться к ленте
            </button>
          </div>
        </section>
      ) : null}

      {isResultView && currentJob ? (
        <section className="focus-screen">
          <span className="eyebrow">{currentJob.status === "failed" ? "Ошибка" : "Готово"}</span>
          <h1>{currentJob.status === "failed" ? "Не удалось собрать кадр" : "Выбери лучший вариант"}</h1>
          <p className="focus-screen__text">
            {currentJob.status === "failed"
              ? currentJob.error_message || "Попробуй еще раз с другим фото или другим шаблоном."
              : "Результаты готовы. Можно открыть любой вариант и вернуться обратно в ленту."}
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
                        alt={`Превью ${result.index + 1}`}
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
                    disabled={!hasFaceSource || submitting}
                    onClick={() => void runStyle(currentStyle.id)}
                  >
                    {submitting ? "Ставим в очередь..." : "Сделать еще"}
                  </button>
                ) : null}
              </div>
            </>
          ) : null}
        </section>
      ) : null}

      {!isQueueView && !isResultView ? (
        <>
          <header className="simple-header">
            <div className="simple-header__badges">
              <span className="simple-badge">avatar_ai</span>
              <span className="simple-badge">{isTelegram ? "Telegram" : "Browser preview"}</span>
            </div>
            <h1>Выбери шаблон и вставь себя</h1>
            <p>
              Один раз добавляешь лицо. Потом просто нажимаешь на понравившийся пример из ленты.
            </p>
          </header>

          {error ? <div className="error-banner simple-error">{error}</div> : null}

          <section ref={composerRef} className="setup-grid">
            <FaceProfilePanel
              guestSessionId={isTelegram ? undefined : guestSessionId}
              telegramInitData={isTelegram ? telegramInitData : undefined}
              selectedFaceProfileId={selectedFaceProfileId}
              onSelectFaceProfileId={handleSelectFaceProfile}
            />

            <section className="quick-override-panel">
              <div className="quick-override-panel__head">
                <div>
                  <span className="eyebrow">Разовая подмена</span>
                  <h3>{portraitPreview ? "На этот запуск выбрано другое лицо" : "Нужно вставить не себя?"}</h3>
                </div>
                <p>
                  {portraitPreview
                    ? "Это фото будет использовано только для текущей задачи."
                    : "Можно временно загрузить фото друга или другого человека, не меняя сохраненное лицо."}
                </p>
              </div>

              {portraitPreview ? (
                <div className="override-preview">
                  <img src={portraitPreview} alt="Временное лицо" decoding="async" />
                  <div className="override-preview__actions">
                    <label className="ghost-button">
                      Заменить фото
                      <input type="file" accept="image/*" onChange={onFileChange} />
                    </label>
                    <button type="button" className="ghost-button" onClick={clearTemporaryUpload}>
                      Убрать
                    </button>
                  </div>
                </div>
              ) : (
                <label className="simple-upload">
                  <input type="file" accept="image/*" onChange={onFileChange} />
                  <span>Загрузить другое лицо</span>
                  <strong>Например фото друга</strong>
                  <small>Если ничего не загружать, будет использовано сохраненное лицо.</small>
                </label>
              )}
            </section>
          </section>

          <section className="feed-block">
            <div className="feed-block__head">
              <div>
                <span className="eyebrow">Лента</span>
                <h2>{loading ? "Загружаем примеры..." : "Готовые примеры"}</h2>
              </div>
              <p>{actionHint}</p>
            </div>

            <div className="feed-grid">
              {styles.map((style) => {
                const isSelected = selectedStyleId === style.id;

                return (
                  <article key={style.id} className={`feed-card ${isSelected ? "is-selected" : ""}`}>
                    <div className="feed-card__media">
                      <img
                        src={assetUrl(style.preview_image)}
                        alt={style.name}
                        loading="lazy"
                        decoding="async"
                        sizes="(max-width: 760px) 100vw, (max-width: 1180px) 50vw, 33vw"
                      />
                    </div>

                    <div className="feed-card__body">
                      <div className="feed-card__top">
                        <div>
                          <h3>{style.name}</h3>
                          <p>{style.description}</p>
                        </div>
                        {isSelected ? <span className="micro-pill">Выбран</span> : null}
                      </div>

                      <div className="tag-row">
                        {style.tags.map((tag) => (
                          <span key={tag}>{tag}</span>
                        ))}
                      </div>

                      <button
                        type="button"
                        className="primary-button"
                        disabled={submitting}
                        onClick={() => void runStyle(style.id)}
                      >
                        {submitting && isSelected ? "Ставим в очередь..." : "Вставить себя"}
                      </button>
                    </div>
                  </article>
                );
              })}
            </div>
          </section>

          <section className="mini-history">
            <div className="feed-block__head">
              <div>
                <span className="eyebrow">История</span>
                <h2>Последние рендеры</h2>
              </div>
              <p>{history.length > 0 ? "Можно открыть любой старый запуск." : "История появится после первого рендера."}</p>
            </div>

            <div className="mini-history__row">
              {history.length === 0 ? <div className="history-empty">Пока пусто.</div> : null}
              {history.map((job) => {
                const historyImage = pickHistoryImage(job);
                return (
                  <button
                    type="button"
                    key={job.job_id}
                    className={`mini-history-card ${job.job_id === currentJobId ? "is-current" : ""}`}
                    onClick={() => {
                      setCurrentJobId(job.job_id);
                      updateJobInUrl(job.job_id);
                    }}
                  >
                    <div className="mini-history-card__thumb">
                      {historyImage ? (
                        <img src={historyImage} alt={job.style_id} loading="lazy" decoding="async" sizes="88px" />
                      ) : (
                        <div className="history-card__placeholder" />
                      )}
                    </div>
                    <div className="mini-history-card__body">
                      <strong>{styleById.get(job.style_id)?.name || job.style_id}</strong>
                      <span>{humanStatus(job.status)}</span>
                      <small>{formatMoment(job.created_at)}</small>
                    </div>
                  </button>
                );
              })}
            </div>
          </section>
        </>
      ) : null}
    </div>
  );
}

export default App;
