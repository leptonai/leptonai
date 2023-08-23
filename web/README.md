# Lepton Web

This is a monorepo for the lepton web and its packages.

## Packages

| Package                                     | Description                                              |
| ------------------------------------------- | -------------------------------------------------------- |
| [dashboard](./packages/dashboard/README.md) | Lepton Dashboard, web-based UI for Lepton workspaces.    |
| [portal](./packages/portal/README.md)       | Includes APIs for authorization, billing, admin and oss. |
| [database](./packages/database/README.md)   | Database models and migrations.                          |

## Install Dependencies

This project uses [pnpm](https://pnpm.io/) as the package manager. To install dependencies, run:

```bash
pnpm install
```

### Running in dev mode

Add `packages/dashboard/.env.development.local` file like `packages/dashboard/.env.example`.

Add `packages/portal/.env.local` file like `packages/portal/.env.local.example`.

Run the following command to start the development server:

```bash
pnpm dev
```

> Note: When you want to cancel the development server, you might need to press `Ctrl + C` twice.
