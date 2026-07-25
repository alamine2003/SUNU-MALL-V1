import { useState } from "react";
import { Link } from "react-router-dom";
import { Baby, ChevronDown, Dumbbell, Home as HomeIcon, Package, Shirt, Smartphone, Sparkles, Utensils, type LucideIcon } from "lucide-react";
import { useAsync } from "@/hooks/useAsync";
import * as catalogApi from "@/api/catalog";

const ICON_BY_NAME: Record<string, LucideIcon> = {
  mode: Shirt,
  vêtements: Shirt,
  vetements: Shirt,
  électronique: Smartphone,
  electronique: Smartphone,
  maison: HomeIcon,
  beauté: Sparkles,
  beaute: Sparkles,
  alimentation: Utensils,
  enfants: Baby,
  bébé: Baby,
  bebe: Baby,
  sport: Dumbbell,
  sports: Dumbbell,
};

function iconFor(name: string) {
  return ICON_BY_NAME[name.toLowerCase().trim()] ?? Package;
}

export function CategoryMenu() {
  const [open, setOpen] = useState(false);
  const { data: categories } = useAsync(() => catalogApi.listCategories(), []);
  const topLevel = categories?.filter((c) => !c.parent) ?? [];

  return (
    <div className="relative hidden sm:block">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex h-full items-center gap-1 whitespace-nowrap rounded-l-lg border-r border-gray-200 px-3 text-sm text-gray-600 hover:bg-gray-50"
      >
        Toutes les catégories <ChevronDown className="ml-1 h-3.5 w-3.5 text-gray-400" />
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute left-0 top-full z-20 mt-1 w-64 overflow-hidden rounded-xl border border-gray-100 bg-white py-2 shadow-lg">
            {topLevel.length === 0 ? (
              <p className="px-4 py-3 text-sm text-gray-400">Aucune catégorie pour le moment.</p>
            ) : (
              topLevel.map((category) => {
                const Icon = iconFor(category.name);
                return (
                  <Link
                    key={category.id}
                    to={`/category/${category.id}`}
                    onClick={() => setOpen(false)}
                    className="flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 hover:text-orange"
                  >
                    <Icon className="h-4 w-4 text-orange" />
                    {category.name}
                  </Link>
                );
              })
            )}
            <Link
              to="/category"
              onClick={() => setOpen(false)}
              className="mt-1 block border-t border-gray-100 px-4 py-2.5 text-sm font-semibold text-orange hover:bg-gray-50"
            >
              Voir toutes les catégories
            </Link>
          </div>
        </>
      )}
    </div>
  );
}
