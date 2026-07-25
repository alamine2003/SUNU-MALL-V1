import { Outlet, useLocation } from "react-router-dom";
import { Logo } from "@/components/brand/Logo";

const AUTH_IMAGES: Record<string, { src: string; alt: string }> = {
  "/register-client": { src: "/hero-shopper.jpg", alt: "Cliente Sunu Mall avec ses achats" },
  "/register-merchant": { src: "/merchant-store.jpg", alt: "Commerçant Sunu Mall conseillant une cliente en boutique" },
};
const DEFAULT_AUTH_IMAGE = { src: "/auth-client.jpg", alt: "Client Sunu Mall" };

export function AuthLayout() {
  const { pathname } = useLocation();
  const image = AUTH_IMAGES[pathname] ?? DEFAULT_AUTH_IMAGE;

  return (
    <div className="flex min-h-screen flex-col lg:flex-row">
      <div className="relative hidden flex-1 lg:block">
        <img src={image.src} alt={image.alt} className="h-full w-full object-cover" />
        <div className="absolute inset-0 bg-gradient-to-b from-navy/75 via-navy/10 to-navy/85" />
        <div className="absolute left-8 top-8">
          <Logo light />
        </div>
        <div className="absolute bottom-10 left-8 right-8 text-white">
          <p className="font-display text-2xl font-extrabold leading-tight">
            Tout le Sénégal
            <br /> dans une seule plateforme
          </p>
          <p className="mt-2 text-sm text-white/70">Achetez, vendez et livrez en toute confiance.</p>
        </div>
      </div>

      <div className="flex flex-1 flex-col bg-gradient-hero lg:bg-white">
        <div className="p-6 lg:hidden">
          <Logo to="/home" light />
        </div>
        <div className="flex flex-1 items-center justify-center p-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-8 shadow-navy-glow animate-fade-in-up lg:shadow-none lg:border lg:border-border">
            <Outlet />
          </div>
        </div>
      </div>
    </div>
  );
}
