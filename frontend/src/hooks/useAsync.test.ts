// @vitest-environment jsdom
import { act, createElement } from "react";
import { createRoot } from "react-dom/client";
import { expect, it, vi } from "vitest";
import { useAsync } from "./useAsync";

it("ignore la réponse d'une recherche ancienne arrivée après la nouvelle", async () => {
  vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
  const container = document.createElement("div");
  const root = createRoot(container);
  let finishOld: (value: string) => void = () => undefined;
  const old = new Promise<string>((resolve) => { finishOld = resolve; });
  function Search({ query }: { query: string }) {
    const { data } = useAsync(() => query === "old" ? old : Promise.resolve("new-result"), [query]);
    return createElement("span", null, data);
  }
  try {
    await act(async () => { root.render(createElement(Search, { query: "old" })); });
    await act(async () => { root.render(createElement(Search, { query: "new" })); });
    expect(container.textContent).toBe("new-result");
    await act(async () => { finishOld("stale-result"); });
    expect(container.textContent).toBe("new-result");
  } finally {
    await act(async () => { root.unmount(); });
    vi.unstubAllGlobals();
  }
});
