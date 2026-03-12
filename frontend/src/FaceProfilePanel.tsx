import { ChangeEvent, useEffect, useState } from "react";

import { assetUrl, createFaceProfile, fetchFaceProfiles } from "./api";
import type { FaceProfile } from "./types";

type FaceProfilePanelProps = {
  guestSessionId?: string;
  telegramInitData?: string;
  selectedFaceProfileId: string;
  onSelectFaceProfileId: (profileId: string) => void;
  onSelectedFacePreviewChange?: (previewUrl: string | null) => void;
};

function FaceProfilePanel(props: FaceProfilePanelProps) {
  const { guestSessionId, telegramInitData, selectedFaceProfileId, onSelectFaceProfileId, onSelectedFacePreviewChange } = props;
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
          onSelectedFacePreviewChange?.(items[0].preview_url || items[0].image_url);
          return;
        }

        const selectedProfile = items.find((item) => item.id === selectedFaceProfileId);
        if (selectedProfile) {
          onSelectedFacePreviewChange?.(selectedProfile.preview_url || selectedProfile.image_url);
        } else if (!items.length) {
          onSelectedFacePreviewChange?.(null);
        }
      })
      .catch((reason: unknown) => {
        if (active) {
          setError(reason instanceof Error ? reason.message : "Не удалось загрузить лица.");
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
  }, [guestSessionId, onSelectFaceProfileId, onSelectedFacePreviewChange, selectedFaceProfileId, telegramInitData]);

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
      onSelectedFacePreviewChange?.(profile.preview_url || profile.image_url);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не удалось сохранить лицо.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="face-panel compact-face-panel">
      <div className="compact-face-panel__head">
        <span className="eyebrow">Мое лицо</span>
        <label className="ghost-button face-upload-button">
          {saving ? "Сохраняем..." : profiles.length > 0 ? "Добавить" : "Загрузить"}
          <input type="file" accept="image/*" onChange={(event) => void handleProfileUpload(event)} disabled={saving} />
        </label>
      </div>

      {loading ? <div className="history-empty">Загружаем...</div> : null}
      {!loading && profiles.length === 0 ? <div className="history-empty">Пока нет лиц.</div> : null}
      {error ? <div className="error-banner">{error}</div> : null}

      {profiles.length > 0 ? (
        <div className="face-profile-strip">
          {profiles.map((profile) => {
            const preview = profile.preview_url || profile.image_url;
            return (
              <button
                type="button"
                key={profile.id}
                className={`face-profile-pill ${selectedFaceProfileId === profile.id ? "is-selected" : ""}`}
                onClick={() => {
                  onSelectFaceProfileId(profile.id);
                  onSelectedFacePreviewChange?.(preview);
                }}
              >
                <img src={assetUrl(preview)} alt={profile.label} loading="lazy" decoding="async" sizes="56px" />
                <span>{profile.label}</span>
              </button>
            );
          })}
        </div>
      ) : null}
    </section>
  );
}

export default FaceProfilePanel;
