# Ironclad Frontend

The Next.js frontend provides the import dossier intake and review
interface plus an explicitly labeled legacy invoice dashboard.

```powershell
npm ci
npm run dev
```

Open `http://localhost:3000`. The browser API base defaults to
`http://localhost:8000` and can be changed with `NEXT_PUBLIC_API_URL`.

Verification:

```powershell
npm run lint
npm run build
```

The production image is built with `npm ci` and Next.js standalone output.
