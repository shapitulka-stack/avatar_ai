import { ChangeEvent, useEffect, useState } from "react";

import { assetUrl, createFaceProfile, fetchFaceProfiles } from "./api";
import type { FaceProfile } from "./types";

type FaceProfilePanelProps = {
  guestSessionId?: string;
  telegramInitData?: string;
  selectedFaceProfileId: string;
  onSelectFaceProfileId: (profileId: string) => void;
};

function FaceProfilePanel(props: FaceProfilePanelProps) {
  const { guestSessionId, telegramInitData, selectedFaceProfileId, onSelectFaceProfileId } = props;
  const [profiles, setProfiles] = useState<FaceProfile[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    if (!guestSessionId && !telegramInitData) {
      return;
    }

    let active = true;
    setLoading(true);
    setError("");

    fetchFaceProfiles({ guestSessionId, telegramInitData })
      .then((items) => {
        if (!active) {
          return;
        }

        setProfiles(items);
        if (!selectedFaceProfileId && items[0]) {
          onSelectFaceProfileId(items[0].id);
        }
      })
      .catch((reason: unknown) => {
        if (active) {
          setError(reason instanceof Error ? reason.message : "Не удалось загрузить профили лица.");
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
  }, [guestSessionId, onSelectFaceProfileId, selectedFaceProfileId, telegramInitData]);

  async function handleProfileUpload(event: ChangeEvent<HTMLInputElement>): Promise<void> {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) {
      return;
    }

    setSaving(true);
    setError("");

    try {
      const profile = await createFaceProfile({
        file,
        label: file.name.replace(/\.[^.]+$/, "") || "My face",
        guestSessionId,
        telegramInitData,
      });
      setProfiles((current) => [profile, ...current]);
      onSelectFaceProfileId(profile.id);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не удалось сохранить лицо в профиль.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="face-panel">
      <div className="section-head compact">
        <div>
          <span className="eyebrow">Лицо профиля</span>
          <h3>{profiles.length > 0 ? "Сохраненные лица для генерации" : "Сначала сохраните одно лицо"}</h3>
        </div>
        <p>
          {profiles.length > 0
            ? "Дальше можно запускать шаблоны без новой загрузки фото. Для друга или другого человека просто добавьте еще один профиль."
            : "Первый раз человек загружает лицо в профиль, а дальше лента шаблонов уже работает без повторной загрузки."}
        </p>
      </div>

      <div className="face-panel__actions">
        <label className="ghost-button face-upload-button">
          {saving ? "Сохраняем лицо..." : profiles.length > 0 ? "Добавить еще лицо" : "Загрузить лицо в профиль"}
          <input type="file" accept="image/*" onChange={(event) => void handleProfileUpload(event)} disabled={saving} />
        </label>
        <span className="micro-pill">Free queue alpha</span>
      </div>

      {loading ? <div className="history-empty">Загружаем сохраненные лица...</div> : null}
      {!loading && profiles.length === 0 ? <div className="history-empty">Пока нет ни одного сохраненного лица.</div> : null}
      {error ? <div className="error-banner">{error}</div> : null}

      <div className="face-profile-grid">
        {profiles.map((profile) => {
          const preview = profile.preview_url || profile.image_url;
          return (
            <button
              type="button"
              key={profile.id}
              className={`face-profile-card ${selectedFaceProfileId === profile.id ? "is-selected" : ""}`}
              onClick={() => onSelectFaceProfileId(profile.id)}
            >
              <div className="face-profile-card__media">
                <img src={assetUrl(preview)} alt={profile.label} loading="lazy" decoding="async" sizes="96px" />
              </div>
              <div className="face-profile-card__body">
                <strong>{profile.label}</strong>
                <span>{selectedFaceProfileId === profile.id ? "Будет использовано по умолчанию" : "Можно переключить на этот профиль"}</span>
              </div>
            </button>
          );
        })}
      </div>
    </section>
  );
}

export default FaceProfilePanel;

