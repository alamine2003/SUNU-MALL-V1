import { beforeEach, afterEach, expect, it, vi } from "vitest";
import { apiGet, refreshAccessToken } from "./api";
import { useAuthStore } from "@/store/authStore";

const user = { id: "client", email: "client@example.test", first_name: "Client", last_name: "", phone: "", roles: ["client" as const], is_verified: true, has_password: true };
const json = (data: unknown, status = 200) => new Response(JSON.stringify(data), { status, headers: { "Content-Type": "application/json" } });

beforeEach(() => { useAuthStore.setState({ user, accessToken: "expired", refreshToken: null, sessionVersion: 0 }); });
afterEach(() => { vi.unstubAllGlobals(); });

it("mutualise le renouvellement de deux requêtes expirées et réessaie avec le nouveau jeton", async () => {
  const fetcher = vi.fn(async (url: string, options?: RequestInit) => {
    if (url.endsWith("/csrf/")) return json({ csrfToken: "csrf" });
    if (url.endsWith("/refresh/")) return json({ user, access: "fresh", refresh: null });
    return (options?.headers as Record<string, string>).Authorization === "Bearer fresh" ? json({ ok: true }) : json({}, 401);
  });
  vi.stubGlobal("fetch", fetcher);
  expect(await Promise.all([apiGet("/orders/"), apiGet("/shopping/cart/")])).toEqual([{ ok: true }, { ok: true }]);
  expect(fetcher.mock.calls.filter(([url]) => url.endsWith("/refresh/"))).toHaveLength(1);
  const options = fetcher.mock.calls.find(([url]) => url.endsWith("/refresh/"))![1]!;
  expect(options.credentials).toBe("include");
  expect(options.body).toBeUndefined();
  expect(useAuthStore.getState().refreshToken).toBeNull();
});

it("n'écrase pas une nouvelle session avec une réponse de renouvellement ancienne", async () => {
  let finish: (value: Response) => void = () => undefined;
  vi.stubGlobal("fetch", vi.fn(async (url: string) => {
    if (url.endsWith("/csrf/")) return json({ csrfToken: "csrf" });
    return new Promise<Response>((resolve) => { finish = resolve; });
  }));
  const pending = refreshAccessToken();
  await vi.waitFor(() => expect(vi.mocked(fetch).mock.calls.length).toBe(2));
  useAuthStore.getState().loginSuccess({ user: { ...user, id: "new-client" }, access: "new-session", refresh: null });
  finish(json({ user, access: "stale", refresh: null }));
  expect(await pending).toBeNull();
  expect(useAuthStore.getState().accessToken).toBe("new-session");
});
