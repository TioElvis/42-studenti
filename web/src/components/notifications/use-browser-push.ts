"use client";

import * as React from "react";

import { api } from "@/lib/api";
import { disablePush, enablePush, isPushEnabled, isPushSupported } from "@/lib/push";
import { useI18n } from "@/providers/i18n-provider";

/** This device's browser notifications: current state and on/off. */
export function useBrowserPush() {
  const { lang } = useI18n();
  const [publicKey, setPublicKey] = React.useState<string | null>(null);
  const [supported, setSupported] = React.useState(true);
  const [blocked, setBlocked] = React.useState(false);
  const [enabled, setEnabled] = React.useState(false);
  const [busy, setBusy] = React.useState(false);
  const [failed, setFailed] = React.useState(false);

  React.useEffect(() => {
    let active = true;
    async function load() {
      const { public_key } = await api.pushKey();
      const ok = isPushSupported();
      const on = await isPushEnabled();
      if (!active) return;
      setPublicKey(public_key);
      setSupported(ok);
      setBlocked(ok && Notification.permission === "denied");
      setEnabled(on);
    }
    // If this fails the controls stay hidden; the rest of the panel still works.
    load().catch(() => {});
    return () => {
      active = false;
    };
  }, []);

  async function toggle(next: boolean) {
    if (!publicKey || busy) return;
    setBusy(true);
    setFailed(false);
    try {
      if (next) {
        setEnabled(await enablePush(publicKey, lang));
        setBlocked(Notification.permission === "denied");
      } else {
        await disablePush();
        setEnabled(false);
      }
    } catch {
      setEnabled(await isPushEnabled().catch(() => false));
      setFailed(true);
    } finally {
      setBusy(false);
    }
  }

  return {
    /** False until loaded, and for good if the server has push off. */
    available: publicKey !== null,
    supported,
    blocked,
    enabled,
    busy,
    failed,
    toggle,
  };
}
