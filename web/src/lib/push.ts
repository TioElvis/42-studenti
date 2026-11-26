/** Browser notifications (Web Push) for this device. */

import { api } from "./api";
import type { Lang } from "./messages";

const SW_URL = "/sw.js";

/** Needs a secure context (HTTPS or localhost) and the Push API. */
export function isPushSupported(): boolean {
  return (
    typeof window !== "undefined" &&
    window.isSecureContext &&
    "serviceWorker" in navigator &&
    "PushManager" in window &&
    "Notification" in window
  );
}

async function currentSubscription(): Promise<PushSubscription | null> {
  if (!isPushSupported()) return null;
  const registration = await navigator.serviceWorker.getRegistration("/");
  return (await registration?.pushManager.getSubscription()) ?? null;
}

export async function isPushEnabled(): Promise<boolean> {
  if (!isPushSupported() || Notification.permission !== "granted") return false;
  return (await currentSubscription()) !== null;
}

function decodeKey(base64Url: string): Uint8Array<ArrayBuffer> {
  const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(base64.padEnd(Math.ceil(base64.length / 4) * 4, "="));
  return Uint8Array.from(raw, (c) => c.charCodeAt(0));
}

function sameKey(current: ArrayBuffer | null, expected: Uint8Array): boolean {
  if (!current) return false;
  const bytes = new Uint8Array(current);
  return bytes.length === expected.length && bytes.every((b, i) => b === expected[i]);
}

async function save(subscription: PushSubscription, lang: Lang): Promise<void> {
  const { endpoint, keys } = subscription.toJSON();
  if (!endpoint || !keys?.p256dh || !keys.auth) throw new Error("Incomplete push subscription");
  await api.pushSubscribe({ endpoint, keys: { p256dh: keys.p256dh, auth: keys.auth }, lang });
}

/** Ask for permission and register this browser. Call it from a click.
 * Resolves to `false` if the student didn't grant the permission. */
export async function enablePush(publicKey: string, lang: Lang): Promise<boolean> {
  // First thing, while the click still counts as a user gesture.
  if ((await Notification.requestPermission()) !== "granted") return false;

  await navigator.serviceWorker.register(SW_URL);
  const registration = await navigator.serviceWorker.ready;
  const key = decodeKey(publicKey);

  let subscription = await registration.pushManager.getSubscription();
  // A subscription made with an older server key can't be reused.
  if (subscription && !sameKey(subscription.options.applicationServerKey, key)) {
    await subscription.unsubscribe();
    subscription = null;
  }
  subscription ??= await registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: key,
  });

  try {
    await save(subscription, lang);
  } catch (err) {
    await subscription.unsubscribe();
    throw err;
  }
  return true;
}

/** Stop notifications on this browser. */
export async function disablePush(): Promise<void> {
  const subscription = await currentSubscription();
  if (!subscription) return;
  const { endpoint } = subscription;
  // Unsubscribe locally first: that alone stops delivery, and the server drops
  // the dead subscription on its next send if this call fails.
  await subscription.unsubscribe();
  await api.pushUnsubscribe(endpoint);
}

/** Re-send an existing subscription (current student and language). Never prompts. */
export async function syncPush(lang: Lang): Promise<void> {
  if (!(await isPushEnabled())) return;
  const subscription = await currentSubscription();
  if (subscription) await save(subscription, lang);
}
