---
name: web-theme-component
description: Use when building or styling frontend UI in 42-studenti/web (Next.js 15, Tailwind v4, Radix + CVA) - semantic CSS tokens shared by the 4 themes, Italian/Roman slang copy and typecheck/lint steps.
---

# Web UI component and themes (42-studenti/web)

## Themes
Four themes switch via `[data-theme]` in `web/src/app/globals.css`:
`classic`, `hacker`, `bento`, `bento-hacker`. They share the same layout and
**semantic token names**; only values change per theme. Design source of truth
is in `assets/` (`classic.html`, `hacker.html`, `bento.html`,
`bento-hacker.html`, `rome-pixel.png`).

- Style with the semantic tokens (e.g. `bg-surface`, `text-fg`), never raw hex
  colors, so every theme works.
- A new token needs a value in **all four** themes.
- Check the component in each theme, including contrast.

## Components
- Location: `web/src/components/{bacheca,eventi,club,profile,students,
  notifications,chrome,content,ui}`. Reuse `ui/` primitives (hand-built
  shadcn-style on Radix Dialog and CVA) before adding new ones.
- App Router: routes in `web/src/app` (`/` Bacheca, `/eventi`, `/club`).
  Default to server components; add `"use client"` only when needed.
- API access only through `src/lib/api.ts`; types in `src/lib/types.ts`.
  Auth is cookie-based (httpOnly on the API origin), so the UI gates on
  `GET /me`.
- Merge classes with `cn()` (`src/lib/utils.ts`); variants in CVA.

## Copy
- UI is **100% Italian with Roman slang (romanesco)**. Keep strings in
  `src/lib/messages.ts` when shared; no English UI text.
- Tone: friendly, informal, short. Do not invent new slang that reads as a
  mistake; mirror nearby copy.
- Dates via `src/lib/time.ts` (Italian locale, Rome time).

## Scope guard
- Do **not** implement "Step 2.1" (students proposing events). Keep the TODO
  marker in `eventi/events-grid.tsx`.
- Club (`/club`) stays a "Prossimamente" page.

## TypeScript
`strict` + `noUncheckedIndexedAccess`: handle `undefined` from index access.

## Verify
```bash
cd web
pnpm typecheck && pnpm lint && pnpm build
pnpm dev     # check each theme + mobile width
```
