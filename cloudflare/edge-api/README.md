# edge-api

Cloudflare Workers API project for Lab 17.

## Quick start

```bash
cd cloudflare/edge-api
npm install
npx wrangler login
npx wrangler whoami
npx wrangler dev
```

## Required Cloudflare resources

1. Create two secrets:
   - `API_TOKEN`
   - `ADMIN_EMAIL`
2. Create one Workers KV namespace named `SETTINGS`
3. Add the returned namespace IDs to `wrangler.jsonc`
4. Deploy with `npx wrangler deploy`

## Main routes

- `/` - app overview and deployment metadata
- `/health` - health check
- `/edge` - Cloudflare edge metadata from `request.cf`
- `/config` - safe plaintext configuration values
- `/secrets` - safe secret presence summary
- `/counter` - KV-backed persisted counter
- `/kv/<key>` - GET / PUT / POST key-value operations
