# Railway Deployment

Deploy three services: Railway PostgreSQL, Railway backend, and Railway frontend. Keep Qdrant Cloud external.

## Backend

Create a Railway service from this GitHub repository. Keep its root directory at the repository root and set `RAILWAY_DOCKERFILE_PATH=backend/Dockerfile`. Generate a public domain and set health check path to `/health`.

Set these Railway Variables:

```text
POSTGRES_URL=${{Postgres.DATABASE_URL}}
LYZR_AGENT_API_KEY=<secret>
LYZR_EXTRACTION_AGENT_ID=<secret>
LYZR_RAG_AGENT_ID=<secret>
QDRANT_URL=<secret>
QDRANT_API_KEY=<secret>
JWT_SECRET=<long-random-secret>
GOOGLE_CLIENT_ID=<secret>
GOOGLE_CLIENT_SECRET=<secret>
GOOGLE_DRIVE_FOLDER_ID=<folder-id>
GOOGLE_SERVICE_ACCOUNT_JSON=<entire-service-account-json>
APP_ENV=production
APP_DEBUG=false
CORS_ORIGINS=["https://<your-frontend-domain>"]
```

## Frontend

Create a second service from the same repository. Set its root directory to `frontend`, Dockerfile path to `Dockerfile`, and build variable `VITE_API_BASE_URL=https://<your-backend-domain>/api/v1`. Generate a public domain.

After the frontend domain is available, set it in the backend `CORS_ORIGINS` variable and add this exact URL to the Google OAuth authorized JavaScript origins and redirect URI configuration.

Never commit `.env` or the service-account JSON. Railway Variables store them outside Git.
