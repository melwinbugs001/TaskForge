import { api } from "./client";

interface PushSubscriptionPayload {
  endpoint: string;
  keys: {
    p256dh: string;
    auth: string;
  };
}

export async function getVapidPublicKey(): Promise<string> {
  const response = await api.get<{ public_key: string }>(
    "/notifications/vapid-public-key",
  );
  return response.data.public_key;
}

export async function savePushSubscription(
  subscription: PushSubscriptionPayload,
): Promise<void> {
  await api.post("/notifications/subscriptions", subscription);
}

export async function removePushSubscription(endpoint: string): Promise<void> {
  await api.delete("/notifications/subscriptions", { data: { endpoint } });
}