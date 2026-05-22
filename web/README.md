# Redline web dashboard

React + Vite + Tailwind UI for the Redline backend.

## Develop

```bash
npm install
npm run dev
```

Vite serves on `http://localhost:5173` and proxies `/api/*` to the backend at
`http://localhost:8000`. Start the backend in another terminal:

```bash
# from the repo root
.venv/bin/python cli.py serve
```

## Build

```bash
npm run build        # tsc --noEmit, then vite build -> dist/
npm run preview      # serve the production bundle locally
```

`npm run build` runs `tsc --noEmit` first, so type errors fail the build.

## Layout

```
src/
  App.tsx              router
  main.tsx             entry
  pages/
    Landing.tsx        marketing page
    Dashboard.tsx      live scan, static scan, scan history
  components/
    ui/                shadcn-style primitives (button, card, tabs, …)
    Navbar.tsx
    theme-provider.tsx, theme-toggle.tsx
  lib/
    api.ts             thin fetch client over the backend
    utils.ts
```

## Backend endpoints consumed

| Path | Used by |
|---|---|
| `GET  /api/health` | health pill |
| `POST /api/scans` | live scan |
| `GET  /api/scans` | history list |
| `GET  /api/scans/{id}/stream` (SSE) | live scan progress |
| `POST /api/scans/{id}/cancel` | cancel button |
| `GET  /api/scans/{id}/report` | risk summary + history detail |
| `POST /api/scan-repo` | static scan tab |
