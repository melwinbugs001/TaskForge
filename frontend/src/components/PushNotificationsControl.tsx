import { useEffect, useState } from "react";
import { Bell, BellOff } from "lucide-react";
import { getApiError } from "../api/client";
import {
  getVapidPublicKey,
  removePushSubscription,
  savePushSubscription,
} from "../api/push";

type PushState = "loading" | "unsupported" | "unconfigured" | "disabled" | "enabled" | "denied";

export function PushNotificationsControl() {
  const [pushState, setPushState] = useState<PushState>("loading");
  const [publicKey, setPublicKey] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (
      !window.isSecureContext
      || !("Notification" in window)
      || !("serviceWorker" in navigator)
      || !("PushManager" in window)
    ) {
      setPushState("unsupported");
      return;
    }

    getVapidPublicKey()
      .then(async (key) => {
        setPublicKey(key);
        const registration = await navigator.serviceWorker.getRegistration("/");
        const subscription = await registration?.pushManager.getSubscription();
        if (subscription) {
          setPushState("enabled");
        } else if (Notification.permission === "denied") {
          setPushState("denied");
        } else {
          setPushState("disabled");
        }
      })
      .catch(() => setPushState("unconfigured"));
  }, []);

  async function toggleNotifications() {
    setBusy(true);
    setMessage("");
    try {
      if (pushState !== "enabled") {
        const permission = Notification.permission === "granted"
          ? "granted"
          : await Notification.requestPermission();
        if (permission !== "granted") {
          setPushState(permission === "denied" ? "denied" : "disabled");
          setMessage("Allow notifications in your browser to enable task updates.");
          return;
        }
      }

      const registration = await navigator.serviceWorker.getRegistration("/");
      const subscription = await registration?.pushManager.getSubscription();
      if (pushState === "enabled" && subscription) {
        await removePushSubscription(subscription.endpoint);
        await subscription.unsubscribe();
        setPushState("disabled");
        return;
      }

      const worker = registration ?? await navigator.serviceWorker.register("/sw.js");
      await navigator.serviceWorker.ready;
      const activeSubscription = await worker.pushManager.getSubscription()
        ?? await worker.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: decodeApplicationServerKey(publicKey),
        });
      const serialized = activeSubscription.toJSON();
      if (!serialized.endpoint || !serialized.keys?.p256dh || !serialized.keys.auth) {
        throw new Error("The browser returned an incomplete push subscription.");
      }
      await savePushSubscription({
        endpoint: serialized.endpoint,
        keys: {
          p256dh: serialized.keys.p256dh,
          auth: serialized.keys.auth,
        },
      });
      setPushState("enabled");
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : getApiError(reason));
    } finally {
      setBusy(false);
    }
  }

  if (pushState === "loading") {
    return <button type="button" disabled className="btn-secondary flex items-center gap-2 opacity-60"><Bell size={15} /> Checking notifications</button>;
  }
  if (pushState === "unsupported") {
    return <p role="status" className="self-center text-xs text-slate-500">Browser push is unavailable here</p>;
  }
  if (pushState === "unconfigured") {
    return <p role="status" className="self-center text-xs text-amber-300">Push keys are not configured</p>;
  }

  const enabled = pushState === "enabled";
  const label = pushState === "denied"
    ? "Notifications blocked"
    : enabled
      ? "Disable notifications"
      : "Enable notifications";

  return <div className="flex flex-col items-start gap-1">
    <button
      type="button"
      onClick={() => void toggleNotifications()}
      disabled={busy || pushState === "denied"}
      aria-label={label}
      className="btn-secondary flex items-center gap-2 disabled:cursor-not-allowed disabled:opacity-60"
    >
      {enabled ? <BellOff size={15} /> : <Bell size={15} />}
      {busy ? "Updating…" : label}
    </button>
    {(message || pushState === "denied") && <p role="status" className="max-w-64 text-[11px] text-slate-500">{message || "Notifications are blocked in this browser's site settings."}</p>}
  </div>;
}

function decodeApplicationServerKey(key: string): ArrayBuffer {
  const padding = "=".repeat((4 - key.length % 4) % 4);
  const base64 = (key + padding).replace(/-/g, "+").replace(/_/g, "/");
  const binary = window.atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  return bytes.buffer;
}