import { ChangeEvent, useEffect, useMemo, useState } from "react";

import { assetUrl, createJob, fetchJob, fetchMyJobs, fetchStyles } from "./api";
import FaceProfilePanel from "./FaceProfilePanel";
import type { JobDetail, ResultAsset, StyleCard } from "./types";

const GUEST_SESSION_KEY = "avatar_ai_guest_session";
const PENDING_STATUSES = new Set<JobDetail["status"]>(["queued", "running"]);
const STAGE_FLOW = ["face", "template", "queue", "result"] as const;
const RU_DATE_FORMAT = new Intl.DateTimeFormat("ru-RU", {
  dateStyle: "medium",
  timeStyle: "short",
});

type Stage = (typeof STAGE_FLOW)[number];

type StyleMeta = {
  mood: string;
  useCase: string;
  accent: string;
};

const STAGE_CONTENT: Record<Stage, { label: string; title: string; note: string }> = {
  face: {
    label: "Лицо",
    title: "Сохраните лицо один раз",
    note: "После первой загрузки пользователь просто выбирает шаблон и ставит задачу в очередь.",
  },
  template: {
    label: "Лента",
    title: "Выберите шаблон из ленты",
    note: "Никаких prompt-полей для пользователя: только карточки сценариев и быстрый запуск.",
  },
  queue: {
    label: "Очередь",
    title: "Free-очередь уже считает позицию",
    note: "Показываем статус, сколько задач впереди и примерное ожидание до результата.",
  },
  result: {
    label: "Результат",
    title: "Готовые варианты собраны в одном экране",
    note: "Главный кадр крупно, остальные результаты рядом, чтобы быстро выбрать лучший.",
  },
};

const STYLE_COPY: Record<string, Pick<StyleCard, "name" | "description" | "tags"> & StyleMeta> = {
  "anime-neon": {
    name: "Anime Neon",
    description: "Яркий шаблон для заметной аватарки с неоновым свечением и аниме-подачей.",
    tags: ["anime", "neon", "pop"],
    mood: "Заметный, смелый, молодежный вайб.",
    useCase: "Аватарки, gaming, reels cover, соцсети.",
    accent: "pink",
  },
  "cinematic-pro": {
    name: "Cinematic Pro",
    description: "Киношный портретный шаблон с дорогим светом и спокойной премиальной подачей.",
    tags: ["cinema", "portrait", "clean"],
    mood: "Статусный и дорогой визуал без лишнего шума.",
    useCase: "Личный бренд, экспертные профили, business-style контент.",
    accent: "gold",
  },
  "cyber-commander": {
    name: "Cyber Commander",
    description: "Futuristic face template с sci-fi светом, технологичным костюмом и резким вайбом.",
    tags: ["cyber", "future", "bold"],
    mood: "Tech, sci-fi, digital power.",
    useCase: "Комьюнити, gaming-персонажи, яркие карточки контента.",
    accent: "cyan",
  },
  "fantasy-warden": {
    name: "Fantasy Warden",
    description: "Эпический fantasy-шаблон для образов с легендарной атмосферой и драматичным светом.",
    tags: ["fantasy", "hero", "epic"],
    mood: "Сюжетный, атмосферный, героический.",
    useCase: "Фандомы, roleplay, story-driven контент.",
    accent: "emerald",
  },
  "founder-brand": {
    name: "Founder Brand",
    description: "Чистый editorial-шаблон для тех, кому нужна деловая, собранная и уверенная картинка.",
    tags: ["brand", "editorial", "clean"],
    mood: "Спокойный premium-бренд без перегруза.",
    useCase: "Founders, эксперты, продуктовые профили, лендинги.",
    accent: "amber",
  },
  "velvet-royal": {
    name: "Velvet Royal",
    description: "Художественный luxury-template с бархатной палитрой, глубоким светом и вау-подачей.",
    tags: ["royal", "luxury", "art"],
    mood: "Роскошный, эффектный, визуально богатый.",
    useCase: "Премиум-контент, постеры, красивый wow-shot.",
    accent: "plum",
  },
};

const FLOW_CARDS = [
  {
    title: "Telegram-first",
    text: "Основной путь пользователя живет внутри Telegram Mini App, а браузер нужен только для локальной проверки.",
  },
  {
    title: "Saved face profile",
    text: "Первый запуск просит лицо, дальше можно гонять шаблоны без повторной загрузки фотографии.",
  },
  {
    title: "Free queue alpha",
    text: "Пока продукт работает только с бесплатной очередью и mock-генерацией, но интерфейс уже готов к росту.",
  },
];

const PHOTO_TIPS = [
  "Лицо по центру и без сильного поворота головы.",
  "Лучше мягкий свет и без агрессивных теней.",
  "JPG, PNG и WEBP подходят без доп. подготовки.",
];

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

function styleMeta(styleId?: string | null): StyleMeta {
  const translation = styleId ? STYLE_COPY[styleId] : undefined;
  if (translation) {
    return {
      mood: translation.mood,
      useCase: translation.useCase,
      accent: translation.accent,
    };
  }

  return {
    mood: "Выберите карточку, которая ближе по вайбу и задаче.",
    useCase: "Профиль, соцсети, контент и тестовые рендеры.",
    accent: "neutral",
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
      return "Генерация идет";
    case "succeeded":
      return "Готово";
    case "failed":
      return "Ошибка";
    default:
      return "Подготовка";
  }
}

function shortJobId(jobId?: string | null): string {
  return jobId ? jobId.slice(0, 8).toUpperCase() : "Новая";
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

  const hasFaceSource = Boolean(file || selectedFaceProfileId);
  const stage: Stage = currentJob
    ? PENDING_STATUSES.has(currentJob.status)
      ? "queue"
      : "result"
    : hasFaceSource
      ? "template"
      : "face";
  const stageIndex = STAGE_FLOW.indexOf(stage);

  const styleById = useMemo(() => new Map(styles.map((style): [string, StyleCard] => [style.id, style])), [styles]);
  const currentStyle = styleById.get(currentJob?.style_id || selectedStyleId) || null;
  const currentStyleMeta = styleMeta(currentStyle?.id);
  const featuredResult: ResultAsset | null = currentJob?.results[featuredResultIndex] || currentJob?.results[0] || null;
  const sessionMode = isTelegram ? "Telegram Mini App" : "Browser debug preview";
  const sessionNote = isTelegram
    ? "Это основной пользовательский сценарий сервиса: сохранить лицо, выбрать шаблон, встать в очередь и получить результат."
    : "Браузерный режим оставлен только для локальной проверки и admin/debug-preview. Основной продуктовый путь идет через Telegram Mini App.";
  const sessionStatus = currentJob
    ? humanStatus(currentJob.status)
    : hasFaceSource && currentStyle
      ? "Готово к запуску"
      : "Сначала выберите лицо и шаблон";
  const portraitPreview = filePreview || (currentJob?.input_preview_url ? assetUrl(currentJob.input_preview_url) : "");
  const isReadyToGenerate = Boolean((file || selectedFaceProfileId) && selectedStyleId && !submitting);
  const queueTitle = currentJob?.status === "running" ? "Генерация уже идет" : "Вы в бесплатной очереди";
  const queueNote = currentJob?.status === "running"
    ? "Текущая задача уже обрабатывается, позиция в очереди обнулилась. Как только mock-рендер завершится, экран обновится автоматически."
    : currentJob?.queue_position
      ? `Сейчас позиция ${currentJob.queue_position}, задач впереди ${currentJob.jobs_ahead}, ожидание ${formatWait(currentJob.estimated_wait_seconds)}.`
      : STAGE_CONTENT.queue.note;

  useEffect(() => {
    const webApp = window.Telegram?.WebApp;
    webApp?.ready();
    webApp?.expand?.();
    webApp?.setHeaderColor?.("#0b1020");
    webApp?.setBackgroundColor?.("#0b1020");
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

  async function handleCreateJob(): Promise<void> {
    if (!file && !selectedFaceProfileId) {
      setError("Сначала сохраните лицо в профиль или загрузите временную подмену.");
      return;
    }

    if (!selectedStyleId) {
      setError("Сначала выберите шаблон из ленты.");
      return;
    }

    setSubmitting(true);
    setError("");

    try {
      const response = await createJob({
        file: file || undefined,
        faceProfileId: file ? undefined : selectedFaceProfileId,
        styleId: selectedStyleId,
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

  function startOver(): void {
    clearTemporaryUpload();
    setCurrentJobId("");
    setCurrentJob(null);
    setFeaturedResultIndex(0);
    setError("");
    updateJobInUrl(null);
  }

  return (
    <div className={`app-shell stage-${stage}`}>
      <div className="app-glow app-glow--one" />
      <div className="app-glow app-glow--two" />
      <div className="app-grid" />

      <header className="hero-panel">
        <div className="hero-copy">
          <div className="pill-row">
            <span className="top-pill">avatar_ai</span>
            <span className="top-pill">{sessionMode}</span>
            <span className="top-pill">image-only alpha</span>
          </div>

          <h1>Telegram-first сервис, где лицо сохраняется один раз, а дальше человек просто кликает шаблон из ленты.</h1>
          <p className="hero-text">{sessionNote}</p>

          <div className="hero-stats">
            <div className="stat-chip">
              <span>Текущий статус</span>
              <strong>{sessionStatus}</strong>
            </div>
            <div className="stat-chip">
              <span>Выбранный шаблон</span>
              <strong>{currentStyle ? currentStyle.name : "Еще не выбран"}</strong>
            </div>
            <div className="stat-chip">
              <span>История запусков</span>
              <strong>{history.length > 0 ? `${history.length} задач` : "Пока пусто"}</strong>
            </div>
          </div>
        </div>

        <section className={`hero-preview tone-${currentStyleMeta.accent}`}>
          {currentStyle ? (
            <>
              <div className="hero-preview__media">
                <img
                  src={assetUrl(currentStyle.preview_image)}
                  alt={currentStyle.name}
                  loading="eager"
                  decoding="async"
                  fetchPriority="high"
                  sizes="(max-width: 980px) 100vw, 32vw"
                />
              </div>
              <div className="hero-preview__body">
                <span className={`status-pill is-${currentJob?.status || (isReadyToGenerate ? "armed" : "idle")}`}>{sessionStatus}</span>
                <h2>{currentStyle.name}</h2>
                <p>{currentStyle.description}</p>
                <div className="tag-row">
                  {currentStyle.tags.map((tag) => (
                    <span key={tag}>{tag}</span>
                  ))}
                </div>
                <div className="mini-copy-grid">
                  <div>
                    <span>Настроение</span>
                    <strong>{currentStyleMeta.mood}</strong>
                  </div>
                  <div>
                    <span>Лучше всего для</span>
                    <strong>{currentStyleMeta.useCase}</strong>
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="hero-preview__empty">
              <span className="status-pill is-idle">Соберите запуск</span>
              <h2>Сначала выберите лицо и шаблон</h2>
              <p>После этого пользователь сможет поставить рендер в очередь и вернуться к истории прямо из Telegram Mini App.</p>
            </div>
          )}
        </section>
      </header>

      <section className="progress-strip">
        {STAGE_FLOW.map((item, index) => {
          const isActive = stage === item;
          const isComplete = stageIndex > index;

          return (
            <div key={item} className={`progress-card ${isActive ? "is-active" : ""} ${isComplete ? "is-complete" : ""}`.trim()}>
              <span>0{index + 1}</span>
              <strong>{STAGE_CONTENT[item].label}</strong>
              <p>{STAGE_CONTENT[item].note}</p>
            </div>
          );
        })}
      </section>

      <main className="content-grid">
        <section className="builder-panel">
          <div className="section-head">
            <div>
              <span className="eyebrow">Шаблонная лента</span>
              <h2>{loading ? "Загружаем шаблоны..." : STAGE_CONTENT.template.title}</h2>
            </div>
            <p>Сценарий максимально простой: сохраненное лицо или временная подмена, выбор карточки и постановка в free-очередь.</p>
          </div>

          <div className="style-feed">
            {styles.map((style) => (
              <button
                type="button"
                key={style.id}
                className={`style-tile ${selectedStyleId === style.id ? "is-selected" : ""} tone-${styleMeta(style.id).accent}`.trim()}
                onClick={() => setSelectedStyleId(style.id)}
              >
                <div className="style-tile__media">
                  <img
                    src={assetUrl(style.preview_image)}
                    alt={style.name}
                    loading="lazy"
                    decoding="async"
                    sizes="(max-width: 760px) 82vw, (max-width: 1180px) 36vw, 24vw"
                  />
                </div>
                <div className="style-tile__body">
                  <div className="style-tile__header">
                    <strong>{style.name}</strong>
                    {selectedStyleId === style.id ? <span className="picked-badge">Выбран</span> : null}
                  </div>
                  <p>{style.description}</p>
                  <div className="tag-row">
                    {style.tags.map((tag) => (
                      <span key={tag}>{tag}</span>
                    ))}
                  </div>
                </div>
              </button>
            ))}
          </div>

          <FaceProfilePanel
            guestSessionId={isTelegram ? undefined : guestSessionId}
            telegramInitData={isTelegram ? telegramInitData : undefined}
            selectedFaceProfileId={selectedFaceProfileId}
            onSelectFaceProfileId={handleSelectFaceProfile}
          />

          <div className="builder-columns">
            <section className="upload-card">
              <div className="section-head compact">
                <div>
                  <span className="eyebrow">Временная подмена лица</span>
                  <h3>{portraitPreview ? "Override уже загружен" : "Подменить лицо только для этой задачи"}</h3>
                </div>
                <p>
                  {portraitPreview
                    ? "Этот файл приоритетнее saved face profile и будет использован только в текущем запуске."
                    : "Если нужно быстро сделать рендер для друга или другого человека, можно не трогать профиль, а загрузить временную замену."}
                </p>
              </div>

              {portraitPreview ? (
                <div className="portrait-card">
                  <img src={portraitPreview} alt="Временная подмена лица" decoding="async" />
                  <div className="portrait-card__overlay">
                    <div>
                      <span>Face override</span>
                      <strong>{file?.name || "Временное лицо"}</strong>
                    </div>
                    <div className="overlay-actions">
                      <label className="ghost-button">
                        Заменить
                        <input type="file" accept="image/*" onChange={onFileChange} />
                      </label>
                      <button type="button" className="ghost-button" onClick={clearTemporaryUpload}>
                        Очистить
                      </button>
                    </div>
                  </div>
                </div>
              ) : (
                <label className="upload-dropzone">
                  <input type="file" accept="image/*" onChange={onFileChange} />
                  <span className="upload-dropzone__kicker">Temporary override</span>
                  <strong>Загрузите отдельное лицо, если текущий рендер не должен использовать сохраненный профиль.</strong>
                  <small>Если поле пустое, задача возьмет сохраненное лицо из выбранного profile card.</small>
                </label>
              )}

              <div className="tip-list">
                {PHOTO_TIPS.map((tip) => (
                  <div key={tip} className="tip-item">
                    <div className="tip-item__dot" />
                    <span>{tip}</span>
                  </div>
                ))}
              </div>
            </section>

            <section className={`launch-card tone-${currentStyleMeta.accent}`}>
              <div className="section-head compact">
                <div>
                  <span className="eyebrow">Запуск</span>
                  <h3>{currentStyle ? currentStyle.name : "Сначала выберите шаблон"}</h3>
                </div>
                <p>В этой стадии работаем только с image-only alpha и free-очередью без оплаты и premium-проходов.</p>
              </div>

              <div className="launch-body">
                <div className="launch-points">
                  <div className="launch-point">
                    <span>Лицо</span>
                    <strong>{file ? "Временная подмена" : selectedFaceProfileId ? "Saved face profile" : "Не выбрано"}</strong>
                  </div>
                  <div className="launch-point">
                    <span>Режим</span>
                    <strong>{isTelegram ? "User flow" : "Debug preview"}</strong>
                  </div>
                  <div className="launch-point">
                    <span>Очередь</span>
                    <strong>{currentJob && PENDING_STATUSES.has(currentJob.status) ? formatWait(currentJob.estimated_wait_seconds) : "Будет показана после старта"}</strong>
                  </div>
                </div>

                <button type="button" className="primary-button" disabled={!isReadyToGenerate} onClick={() => void handleCreateJob()}>
                  {submitting ? "Ставим в очередь..." : "Поставить задачу в free-очередь"}
                </button>

                <p className="launch-note">
                  Пока сервис работает на mock-генерации и бесплатной очереди. Это alpha-оболочка продукта, но пользовательский flow уже соответствует Telegram-first MVP.
                </p>

                {(file || currentJobId) && (
                  <button type="button" className="secondary-button" onClick={startOver}>
                    Очистить текущий запуск
                  </button>
                )}
              </div>
            </section>
          </div>

          {error ? <div className="error-banner">{error}</div> : null}
        </section>

        <aside className="side-rail">
          <section className="side-card debug-card">
            <span className="eyebrow">Режим доступа</span>
            <h3>{isTelegram ? "Основной пользовательский канал" : "Локальный browser preview"}</h3>
            <p>{sessionNote}</p>
          </section>

          <section className="side-card promise-card">
            <span className="eyebrow">MVP alpha</span>
            <h3>Что уже проверяем продуктово</h3>
            <div className="promise-list">
              {FLOW_CARDS.map((item) => (
                <div key={item.title} className="promise-item">
                  <strong>{item.title}</strong>
                  <p>{item.text}</p>
                </div>
              ))}
            </div>
          </section>

          <section className="side-card session-card">
            <span className="eyebrow">Текущая задача</span>
            <h3>Сводка запуска</h3>
            <div className="session-grid">
              <div className="session-box">
                <span>Этап</span>
                <strong>{STAGE_CONTENT[stage].label}</strong>
              </div>
              <div className="session-box">
                <span>Статус</span>
                <strong>{sessionStatus}</strong>
              </div>
              <div className="session-box">
                <span>Задача</span>
                <strong>{shortJobId(currentJob?.job_id || currentJobId)}</strong>
              </div>
              <div className="session-box">
                <span>Создано</span>
                <strong>{formatMoment(currentJob?.created_at)}</strong>
              </div>
            </div>
          </section>

          <section className="side-card history-card-panel">
            <span className="eyebrow">История</span>
            <h3>Последние рендеры</h3>
            <div className="history-list">
              {history.length === 0 ? <div className="history-empty">История пользователя появится после первого запуска.</div> : null}
              {history.map((job) => {
                const historyImage = pickHistoryImage(job);
                return (
                  <button
                    type="button"
                    key={job.job_id}
                    className={`history-card ${job.job_id === currentJobId ? "is-current" : ""}`}
                    onClick={() => {
                      setCurrentJobId(job.job_id);
                      updateJobInUrl(job.job_id);
                    }}
                  >
                    <div className="history-card__thumb">
                      {historyImage ? <img src={historyImage} alt={job.style_id} loading="lazy" decoding="async" sizes="68px" /> : <div className="history-card__placeholder" />}
                    </div>
                    <div className="history-card__body">
                      <strong>{styleById.get(job.style_id)?.name || job.style_id}</strong>
                      <span>{humanStatus(job.status)}</span>
                      <small>{formatMoment(job.created_at)}</small>
                    </div>
                  </button>
                );
              })}
            </div>
          </section>
        </aside>
      </main>

      {stage === "queue" && currentJob ? (
        <section className="focus-panel processing-panel">
          <div className="processing-copy">
            <span className="eyebrow">Free queue</span>
            <h2>{queueTitle}</h2>
            <p>{queueNote}</p>
            <div className="processing-meta">
              <div>
                <span>Позиция</span>
                <strong>{currentJob.queue_position ?? "Сейчас рендерится"}</strong>
              </div>
              <div>
                <span>Задач впереди</span>
                <strong>{currentJob.jobs_ahead}</strong>
              </div>
              <div>
                <span>Ожидание</span>
                <strong>{formatWait(currentJob.estimated_wait_seconds)}</strong>
              </div>
              <div>
                <span>Лимит пользователя</span>
                <strong>{currentJob.user_pending_jobs}/{currentJob.max_pending_per_user}</strong>
              </div>
            </div>
          </div>

          <div className="processing-visual">
            <div className="signal-orbit">
              <div className="signal-orbit__ring" />
              <div className="signal-orbit__core">
                <span>{sessionStatus}</span>
                <small>{shortJobId(currentJob.job_id)}</small>
              </div>
            </div>
            {portraitPreview ? (
              <div className="processing-portrait">
                <img src={portraitPreview} alt="Портрет в очереди" decoding="async" />
              </div>
            ) : null}
          </div>
        </section>
      ) : null}

      {stage === "result" && currentJob ? (
        <section className="focus-panel result-panel">
          <div className="section-head">
            <div>
              <span className="eyebrow">Результат</span>
              <h2>{currentJob.status === "failed" ? "Задача завершилась ошибкой" : STAGE_CONTENT.result.title}</h2>
            </div>
            <p>
              {currentJob.status === "failed"
                ? currentJob.error_message || "Попробуйте заново с другим фото или тем же шаблоном."
                : "Mock-генерация вернула несколько вариантов. Можно быстро открыть главный кадр или посмотреть остальные превью."}
            </p>
          </div>

          {currentJob.status === "failed" ? (
            <div className="failed-box">
              <button type="button" className="primary-button" onClick={startOver}>
                Начать заново
              </button>
            </div>
          ) : featuredResult ? (
            <div className="result-layout">
              <a className="result-hero" href={assetUrl(featuredResult.image_url)} target="_blank" rel="noreferrer">
                <div className="result-hero__media">
                  <img
                    src={assetUrl(featuredResult.image_url)}
                    alt={`Главный результат ${featuredResult.index + 1}`}
                    loading="eager"
                    decoding="async"
                    fetchPriority="high"
                  />
                </div>
                <div className="result-hero__body">
                  <span className="eyebrow">Главный кадр</span>
                  <h3>Вариант {featuredResult.index + 1}</h3>
                  <p>{currentStyle ? `${currentStyle.name} сейчас выбран как основной просмотр.` : "Откройте полный размер и оцените итоговый mock-рендер."}</p>
                  <div className="tag-row">
                    <span>{featuredResult.width || 1024} x {featuredResult.height || 1024}</span>
                    <span>{featuredResult.seed ? `seed ${featuredResult.seed}` : "mock seed"}</span>
                    <span>{currentStyle ? currentStyle.name : "Template"}</span>
                  </div>
                </div>
              </a>

              <div className="result-rail">
                <div className="result-grid">
                  {currentJob.results.map((result) => (
                    <button
                      type="button"
                      key={result.index}
                      className={`result-tile ${featuredResult.index === result.index ? "is-featured" : ""}`}
                      onClick={() => setFeaturedResultIndex(result.index)}
                    >
                      <img
                        src={assetUrl(result.thumb_url)}
                        alt={`Вариант ${result.index + 1}`}
                        loading="lazy"
                        decoding="async"
                        sizes="(max-width: 760px) 100vw, (max-width: 1180px) 42vw, 20vw"
                      />
                      <strong>Вариант {result.index + 1}</strong>
                      <span>{result.seed ? `seed ${result.seed}` : "preview"}</span>
                    </button>
                  ))}
                </div>

                <div className="result-actions">
                  <button type="button" className="secondary-button" onClick={startOver}>
                    Запустить новый рендер
                  </button>
                </div>
              </div>
            </div>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}

export default App;

