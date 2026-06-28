/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        mint: {
          DEFAULT: "hsl(var(--mint))",
          foreground: "hsl(var(--mint-foreground))",
        },
        redline: {
          50: "hsl(var(--red-50))",
          200: "hsl(var(--red-200))",
          300: "hsl(var(--red-300))",
          400: "hsl(var(--red-400))",
          500: "hsl(var(--red-500))",
          600: "hsl(var(--red-600))",
          700: "hsl(var(--red-700))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      fontFamily: {
        sans: ["Satoshi", "ui-sans-serif", "system-ui", "sans-serif"],
        display: ["Cabinet Grotesk", "Satoshi", "ui-sans-serif", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      keyframes: {
        "fade-up": {
          from: { opacity: "0", transform: "translateY(8px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "redline-shimmer": {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        "redline-float": {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-4px)" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.5s ease-out forwards",
        "redline-shimmer": "redline-shimmer 6s linear infinite",
        "redline-float": "redline-float 4s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
