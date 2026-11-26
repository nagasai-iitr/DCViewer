# Demo database seed

`seed.sql` is loaded automatically by Postgres on **first** volume create via `/docker-entrypoint-initdb.d/`.

It contains the processed demo meetings (Hermantown, Joliet, Clinton, Augusta) so evaluators can use the UI without waiting for LLM jobs.

Regenerate after new ingest (maintainer only):

```bash
docker compose exec -T postgres pg_dump -U gathergov -d gathergov --no-owner --no-acl \
  | grep -vE '^\\restrict|^\\unrestrict' > db/seed.sql
```
