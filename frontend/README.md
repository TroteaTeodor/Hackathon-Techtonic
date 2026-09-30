# KBC Foresight: frontend

Next.js (App Router, TypeScript, Tailwind). Routes: `/login`, `/app` (customer), `/advisor`, `/advisor/customers/[id]`, `/advisor/scale`.

```bash
pnpm install          # pnpm only, never npm/npx
pnpm dev              # http://localhost:3000
pnpm lint && pnpm build
```

`.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_USE_MOCKS=false   # true = run on src/mocks/*.json without the backend
```

- The API contract lives in `src/lib/types.ts` (mirrored by `backend/app/schemas.py`).
- The mock fixtures in `src/mocks/` are validated by the backend contract test.
- See the root [README](../README.md) for the full project.
