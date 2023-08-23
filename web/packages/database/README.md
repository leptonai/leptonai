## Supabase Usage

## Environment Requirements

- [npm](https://www.npmjs.com/get-npm)
- [pnpm](https://pnpm.io/installation)
- Docker

## Setup

### supabase link

Connecting to a remote database, if you don't have a database please go to [projects](https://supabase.com/dashboard/projects) to create one.

`https://supabase.com/dashboard/project/<project-id>`

```shell
npx supabase link --project-ref <project-id>
```

### supabase start

Starts the Supabase local development stack.

```shell
npx supabase start
```

### supabase db push

Pushes all local migrations to a remote database.

```shell
npx supabase db push
```

### supabase db reset

Reset the local database using `supabase/migrations` and `supabase/seed.sql`

```shell
npx supabase db reset
```

### supabase status

Check the status of your local Supabase development stack.

```shell
npx supabase status
```

And can open the `Studio URL` to view your database in the browser.

### pnpm build:types

Generate types for the database to `src/database.ts`.

```shell
pnpm build:types
```
