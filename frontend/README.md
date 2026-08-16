# Research Agent Frontend

Small React + TypeScript frontend for the AI Engineer research-agent tech test, bootstrapped with Vite.

The app lets a user:

- enter a research request
- upload source files
- view a streamed markdown response

## Setup

Install dependencies:

```sh
npm install
```

Run the frontend locally:

```sh
npm run dev
```

Vite will print the local URL, usually `http://localhost:5173/`.

## Backend API

By default, the frontend calls:

```txt
http://localhost:8787
```

Set a different backend URL with:

```sh
VITE_API_BASE_URL=http://localhost:8787 npm run dev
```

Expected endpoints:

- `POST /api/research` — accepts JSON `{ "request": "..." }` and returns a streamed markdown response.
- `POST /api/sources` — accepts multipart form uploads under the repeated field name `files`.
