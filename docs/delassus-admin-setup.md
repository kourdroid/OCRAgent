# Delassus Super-Admin Setup

The application now requires Supabase Auth for all dossier and administration APIs.

1. In Supabase Auth, create the controlled pilot administrator using email and password. Disable public sign-up for the pilot.
2. Obtain the new user's UUID from **Authentication > Users**.
3. Insert its platform role in the SQL editor:

```sql
INSERT INTO public.app_users (user_id, role)
VALUES ('<SUPABASE_AUTH_USER_UUID>', 'PLATFORM_SUPER_ADMIN');
```

4. Add `SUPABASE_PUBLISHABLE_KEY` to the root `.env` from the project API settings. Do not place `SUPABASE_SERVICE_ROLE_KEY` in frontend configuration.
5. Rebuild the frontend so Docker receives the public URL and publishable key:

```powershell
docker compose up --build
```

The first active ruleset must be confirmed in the Administration screen. Until then, the worker keeps each processed dossier in `REVIEW_REQUIRED`.

## Current deployment blocker

The configured database URL currently points to the Supabase transaction pooler on port 6543, but this machine receives `rejected SSL upgrade` from that endpoint. Replace `DATABASE_URL` with the current Supabase connection string from **Connect** and include the required TLS configuration before applying the migration or starting the worker.
