import type { Config } from "tailwindcss";
import animate from "tailwindcss-animate";

const config: Config = {
  darkMode: ["class"],
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary) / <alpha-value>)",
          foreground: "hsl(var(--primary-foreground) / <alpha-value>)",
        },
        canvas: "var(--canvas)",
        sidebar: "var(--sidebar)",
        surface: {
          1: "var(--surface-1)",
          2: "var(--surface-2)",
          3: "var(--surface-3)",
          elevated: "var(--surface-elevated)",
          hover: "var(--surface-hover)",
          selected: "var(--surface-selected)",
        },
        text: {
          primary: "var(--text-primary)",
          secondary: "var(--text-secondary)",
          muted: "var(--text-muted)",
        },
        input: {
          background: "var(--input-background)",
          border: "var(--input-border)",
        },
        success: "rgb(34 197 94 / <alpha-value>)",
        warning: "rgb(245 158 11 / <alpha-value>)",
        danger: "rgb(239 68 68 / <alpha-value>)",
        info: "rgb(59 130 246 / <alpha-value>)",
        focus: {
          ring: "var(--focus-ring)",
        },
      },
    },
  },
  plugins: [animate],
};

export default config;
