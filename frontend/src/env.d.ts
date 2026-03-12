/// <reference types="vite/client" />

interface TelegramThemeParams {
  bg_color?: string;
  secondary_bg_color?: string;
  text_color?: string;
  hint_color?: string;
  link_color?: string;
  button_color?: string;
  button_text_color?: string;
  header_bg_color?: string;
  accent_text_color?: string;
  section_bg_color?: string;
  section_header_text_color?: string;
  subtitle_text_color?: string;
  destructive_text_color?: string;
}

interface TelegramWebAppUser {
  id: number;
  username?: string;
  first_name?: string;
  last_name?: string;
}

interface TelegramWebAppInitDataUnsafe {
  user?: TelegramWebAppUser;
  start_param?: string;
}

type TelegramWebAppEventHandler = (...args: unknown[]) => void;

interface TelegramWebApp {
  initData: string;
  initDataUnsafe?: TelegramWebAppInitDataUnsafe;
  colorScheme?: "light" | "dark";
  platform?: string;
  version?: string;
  themeParams?: TelegramThemeParams;
  isExpanded?: boolean;
  viewportHeight?: number;
  viewportStableHeight?: number;
  ready: () => void;
  expand?: () => void;
  close?: () => void;
  setHeaderColor?: (color: string) => void;
  setBackgroundColor?: (color: string) => void;
  onEvent?: (eventType: string, handler: TelegramWebAppEventHandler) => void;
  offEvent?: (eventType: string, handler: TelegramWebAppEventHandler) => void;
}

interface Window {
  Telegram?: {
    WebApp?: TelegramWebApp;
  };
}
