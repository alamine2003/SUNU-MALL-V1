import { apiGet } from "./api";

describe("mobile API client", () => {
  it("returns decoded JSON for a successful response", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ results: ["ok"] }),
    }) as jest.Mock;

    await expect(
      apiGet<{ results: string[] }>("/catalog/products/"),
    ).resolves.toEqual({
      results: ["ok"],
    });
    expect(global.fetch).toHaveBeenCalled();
    expect((global.fetch as jest.Mock).mock.calls[0][0]).toContain(
      "/api/catalog/products/",
    );
  });

  it("raises a useful error for an unsuccessful response", async () => {
    global.fetch = jest
      .fn()
      .mockResolvedValue({ ok: false, status: 503 }) as jest.Mock;

    await expect(apiGet("/health/")).rejects.toThrow(
      "Erreur API (503) sur /health/",
    );
  });
});
