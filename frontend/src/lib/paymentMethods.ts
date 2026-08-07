import { CreditCard } from "lucide-react";
import type { ComponentType } from "react";

export interface PaymentMethodOption {
  id: "wave" | "orange_money" | "card";
  label: string;
  /** Vrai logo de marque, quand disponible (public/) — prioritaire sur `icon`. */
  image?: string;
  icon?: ComponentType<{ className?: string }>;
}

export const PAYMENT_METHODS: PaymentMethodOption[] = [
  { id: "wave", label: "Wave", image: "/wave.png" },
  { id: "orange_money", label: "Orange Money", image: "/orange-money.png" },
  { id: "card", label: "Carte bancaire", icon: CreditCard },
];
