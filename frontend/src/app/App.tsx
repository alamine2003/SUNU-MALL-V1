import { Suspense, useEffect } from "react";
import { RouterProvider } from "react-router-dom";
import { router } from "@/app/router";

import { useAuthStore } from "@/store/authStore";
import { refreshAccessToken } from "@/lib/api";
import { Spinner } from "@/components/ui/Spinner";

export function App() {
  const hydrated = useAuthStore((state) => state.hasHydrated);
  useEffect(() => {
    void refreshAccessToken().catch(() => null).finally(() => useAuthStore.getState().setHasHydrated(true));
  }, []);
  if (!hydrated) return <Spinner label="Chargement…" />;
  return (
    <Suspense fallback={null}>
      <RouterProvider router={router} />
    </Suspense>
  );
}
