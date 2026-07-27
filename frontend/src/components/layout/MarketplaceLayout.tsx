import { Outlet } from "react-router-dom";
import { MarketHeader } from "@/components/layout/MarketHeader";
import { Footer } from "@/components/layout/Footer";
import { GuestCheckoutModal } from "@/components/auth/GuestCheckoutModal";
import { SupportChatWidget } from "@/components/support/SupportChatWidget";

export function MarketplaceLayout() {
  return (
    <div className="flex min-h-screen flex-col bg-white">
      <MarketHeader />
      <main className="flex-1">
        <Outlet />
      </main>
      <Footer />
      <GuestCheckoutModal />
      <SupportChatWidget />
    </div>
  );
}
