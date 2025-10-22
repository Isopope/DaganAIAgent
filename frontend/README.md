# Welcome to your Lovable project

## Project info

**URL**: https://lovable.dev/projects/3ee96998-0cdc-4ff4-a6ca-991f05ba0ee7

## How can I edit this code?

There are several ways of editing your application.

**Use Lovable**

Simply visit the [Lovable Project](https://lovable.dev/projects/3ee96998-0cdc-4ff4-a6ca-991f05ba0ee7) and start prompting.

Changes made via Lovable will be committed automatically to this repo.

**Use your preferred IDE**

If you want to work locally using your own IDE, you can clone this repo and push changes. Pushed changes will also be reflected in Lovable.

The only requirement is having Node.js & npm installed - [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating)

Follow these steps:

```sh
# Step 1: Clone the repository using the project's Git URL.
git clone <YOUR_GIT_URL>

# Step 2: Navigate to the project directory.
cd <YOUR_PROJECT_NAME>

# Step 3: Install the necessary dependencies.
npm i

# Step 4: Start the development server with auto-reloading and an instant preview.
npm run dev
```

**Edit a file directly in GitHub**

- Navigate to the desired file(s).
- Click the "Edit" button (pencil icon) at the top right of the file view.
- Make your changes and commit the changes.

**Use GitHub Codespaces**

- Navigate to the main page of your repository.
- Click on the "Code" button (green button) near the top right.
- Select the "Codespaces" tab.
- Click on "New codespace" to launch a new Codespace environment.
- Edit files directly within the Codespace and commit and push your changes once you're done.

## What technologies are used for this project?

This project is built with:

- Vite
- TypeScript
- React
- shadcn-ui
- Tailwind CSS

## Local configuration

Create a `.env` file at the project root and define:

- `VITE_SUPABASE_URL` = your Supabase project URL
- `VITE_SUPABASE_PUBLISHABLE_KEY` = your Supabase anon/publishable key

For the Supabase Edge Function `chat`, set secrets in your Supabase project:
  - `OPENAI_API_KEY` = your OpenAI API key (supports `sk-proj-...`)

The dev server runs on `http://localhost:8080/` (configured in `vite.config.ts`).

## Project structure note

This repository currently contains a duplicated subfolder `smart-civic-bot-main/` with an identical project inside. Use the repository root as the working app and ignore the nested duplicate.

## Package manager

This project includes both `package-lock.json` and `bun.lockb`. Prefer `npm` locally:

- Install: `npm i`
- Dev: `npm run dev`
- Build: `npm run build`

## Configure Supabase secrets (Edge Functions)

Use Supabase CLI or dashboard to set secrets for the `chat` function:

- CLI example:
  - `supabase secrets set OPENAI_API_KEY="<your-sk-proj-key>"`

Then deploy the function:

- `supabase functions deploy chat`

## How can I deploy this project?

Simply open [Lovable](https://lovable.dev/projects/3ee96998-0cdc-4ff4-a6ca-991f05ba0ee7) and click on Share -> Publish.

## Can I connect a custom domain to my Lovable project?

Yes, you can!

To connect a domain, navigate to Project > Settings > Domains and click Connect Domain.

Read more here: [Setting up a custom domain](https://docs.lovable.dev/features/custom-domain#custom-domain)
