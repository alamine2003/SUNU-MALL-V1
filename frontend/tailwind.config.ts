import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: "#0A163A",
        "navy-2": "#142A5E",
        orange: "#FF7A00",
        "orange-light": "#FF9833",
        "orange-dark": "#E66A00",
        ink: "#111827",
        success: "#22C55E",
        warning: "#F59E0B",
        danger: "#EF4444",
        border: "#E5E7EB",
        muted: "#F9FAFB",
        "muted-foreground": "#6B7280",
        accent: "#FFF7ED",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        display: ["Poppins", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      borderRadius: {
        sm: "6px",
        md: "8px",
        lg: "12px",
        xl: "16px",
        "2xl": "20px",
        "3xl": "24px",
      },
      boxShadow: {
        card: "0 1px 3px rgba(0,0,0,0.05), 0 1px 2px rgba(0,0,0,0.03)",
        elevated: "0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -1px rgba(0,0,0,0.03)",
        orange: "0 4px 14px 0 rgba(255, 122, 0, 0.39)",
        "orange-lg": "0 6px 20px rgba(255, 122, 0, 0.23)",
        "navy-glow": "0 20px 60px -20px rgba(30, 58, 138, 0.3)",
      },
      backgroundImage: {
        "gradient-orange": "linear-gradient(135deg, #FF8C00 0%, #FFA31A 100%)",
        "gradient-navy": "linear-gradient(160deg, #0A163A 0%, #142A5E 100%)",
        "gradient-hero":
          "radial-gradient(circle at 20% 20%, rgba(255,140,0,0.25) 0%, transparent 40%), radial-gradient(circle at 80% 80%, rgba(255,163,26,0.2) 0%, transparent 50%), linear-gradient(160deg, #0A163A 0%, #142A5E 100%)",
        "gradient-sunset": "linear-gradient(135deg, #FF8C00 0%, #FF5C7A 50%, #7B2CBF 100%)",
      },
      keyframes: {
        fadeInUp: {
          from: { opacity: "0", transform: "translateY(12px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-400px 0" },
          "100%": { backgroundPosition: "400px 0" },
        },
        pulseDot: {
          "0%, 100%": { transform: "scale(1)", opacity: "1" },
          "50%": { transform: "scale(1.4)", opacity: "0.5" },
        },
        shine: {
          "0%": { transform: "translateX(-100%) skewX(-15deg)" },
          "100%": { transform: "translateX(300%) skewX(-15deg)" },
        },
      },
      animation: {
        "fade-in-up": "fadeInUp 0.5s cubic-bezier(0.2, 0.8, 0.2, 1) both",
        shimmer: "shimmer 1.4s infinite linear",
        "pulse-dot": "pulseDot 1.4s ease-in-out infinite",
        shine: "shine 0.8s ease",
      },
    },
  },
  plugins: [],
};

export default config;
