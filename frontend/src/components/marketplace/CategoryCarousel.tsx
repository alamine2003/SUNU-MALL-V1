import { useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import {
  Package,
  ChevronLeft,
  ChevronRight,
  Shirt,
  Smartphone,
  Home as HomeIcon,
  Sparkles,
  Utensils,
  Baby,
  Dumbbell,
  BookOpen,
  Car,
  type LucideIcon,
} from "lucide-react";
import type { Category } from "@/types";

const ICON_BY_NAME: Record<string, LucideIcon> = {
  mode: Shirt,
  vêtements: Shirt,
  vetements: Shirt,
  électronique: Smartphone,
  electronique: Smartphone,
  high_tech: Smartphone,
  "high-tech": Smartphone,
  maison: HomeIcon,
  ameublement: HomeIcon,
  beauté: Sparkles,
  beaute: Sparkles,
  cosmétiques: Sparkles,
  alimentation: Utensils,
  épicerie: Utensils,
  enfants: Baby,
  bébé: Baby,
  bebe: Baby,
  sport: Dumbbell,
  sports: Dumbbell,
  livres: BookOpen,
  culture: BookOpen,
  auto: Car,
  automobile: Car,
};

const GRADIENTS = [
  "from-orange to-orange-dark",
  "from-navy to-navy-2",
  "from-pink-500 to-rose-600",
  "from-blue-600 to-blue-800",
  "from-emerald-500 to-emerald-700",
  "from-purple-500 to-purple-700",
];

function iconFor(name: string) {
  return ICON_BY_NAME[name.toLowerCase().trim()] ?? Package;
}

export function CategoryCarousel({ categories }: { categories: Category[] }) {
  const trackRef = useRef<HTMLDivElement>(null);
  const pausedRef = useRef(false);
  const rafRef = useRef<number | null>(null);
  const topLevel = categories.filter((c) => !c.parent);

  useEffect(() => {
    const el = trackRef.current;
    if (!el || topLevel.length === 0) return;

    const SPEED = 0.5;
    const step = () => {
      if (!pausedRef.current) {
        el.scrollLeft += SPEED;
        const half = el.scrollWidth / 2;
        if (el.scrollLeft >= half) el.scrollLeft -= half;
      }
      rafRef.current = requestAnimationFrame(step);
    };
    rafRef.current = requestAnimationFrame(step);

    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [topLevel.length]);

  function nudge(dir: 1 | -1) {
    trackRef.current?.scrollBy({ left: dir * 260, behavior: "smooth" });
  }

  if (topLevel.length === 0) return null;

  const slides = [...topLevel, ...topLevel];

  return (
    <div className="group/carousel relative">
      <div
        ref={trackRef}
        onMouseEnter={() => (pausedRef.current = true)}
        onMouseLeave={() => (pausedRef.current = false)}
        className="flex gap-4 overflow-x-auto scroll-smooth py-1 scrollbar-hide"
      >
        {slides.map((c, i) => {
          const Icon = iconFor(c.name);
          const gradient = GRADIENTS[i % GRADIENTS.length];
          return (
            <Link
              key={`${c.id}-${i}`}
              to={`/category/${c.id}`}
              className={`group/card relative flex aspect-[4/3] w-52 shrink-0 items-end overflow-hidden rounded-2xl border border-gray-100 bg-gradient-to-br p-3 shadow-sm ${gradient}`}
            >
              <span className="absolute left-3 top-3 grid h-9 w-9 place-items-center rounded-full bg-white/95 text-orange shadow">
                <Icon className="h-4 w-4" />
              </span>
              <p className="relative font-display font-bold leading-tight text-white">{c.name}</p>
            </Link>
          );
        })}
      </div>

      <button
        aria-label="Précédent"
        onClick={() => nudge(-1)}
        className="absolute left-0 top-1/2 grid h-9 w-9 -translate-y-1/2 place-items-center rounded-full border border-gray-100 bg-white text-navy opacity-0 shadow-md transition-opacity hover:text-orange group-hover/carousel:opacity-100"
      >
        <ChevronLeft className="h-5 w-5" />
      </button>
      <button
        aria-label="Suivant"
        onClick={() => nudge(1)}
        className="absolute right-0 top-1/2 grid h-9 w-9 -translate-y-1/2 place-items-center rounded-full border border-gray-100 bg-white text-navy opacity-0 shadow-md transition-opacity hover:text-orange group-hover/carousel:opacity-100"
      >
        <ChevronRight className="h-5 w-5" />
      </button>
    </div>
  );
}
