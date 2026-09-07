import { publicAsset } from "@/lib/assets";

export interface PaymentMethodOption {
  id: "wave" | "orange_money";
  label: string;
  /** Vrai logo de marque, quand disponible (public/) — prioritaire sur `icon`. */
  image?: string;
}

export const PAYMENT_METHODS: PaymentMethodOption[] = [
  { id: "wave", label: "Wave", image: publicAsset("wave.png") },
  { id: "orange_money", label: "Orange Money", image: publicAsset("orange-money.png") },
];
