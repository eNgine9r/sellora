import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
      },
      boxShadow: {
        "sellora-xs": "0 6px 18px rgba(15, 23, 42, 0.06)",
        "sellora-sm": "var(--shadow-sm)",
        "sellora-md": "var(--shadow-md)",
      },
      borderRadius: {
        sellora: "var(--radius-control)",
        "sellora-card": "var(--radius-card)",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
