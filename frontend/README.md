# TaskForge frontend

The React + TypeScript frontend uses the implemented authentication, goal CRUD,
team, invitation, and scheduled-task APIs. It does not use an AI provider.

## Goal deadlines

- Optionally set a due date when creating or editing a draft goal.
- An unfinished goal with a due date is marked failed after the deadline when
  goal data is next requested. The dashboard refreshes goal data every minute
  while open; if the app is closed at the deadline, the status updates when it
  is opened again.
- Open a goal and use **Mark complete** to record completion before its
  deadline.

## Team task workflow

- A signed-in user creates a team and becomes that team's leader.
- Teams are private initially. Leaders may make a team discoverable; workers
  can search its name and request to join, subject to leader approval.
- The leader adds worker email addresses. An existing account joins right away;
  a new user joins when registering with the invited email.
- The leader assigns a task to a team worker and chooses a start time and
  deadline (shown in the browser's local timezone).
- Workers see only their own assigned tasks and can submit them for review.
- The leader can adjust times until completion, then approve completion or
  request changes. Requested changes return the task to the worker.

## Run on Windows

Start the backend in one Command Prompt window:

```bat
cd /d C:\task_devloper\backend
C:\task_devloper\.venv\Scripts\activate
uvicorn app.main:app --reload
```

In another Command Prompt window:

```bat
cd /d C:\task_devloper\frontend
npm.cmd install
npm.cmd run dev
```

Open the local URL printed by Vite, normally `http://localhost:5173`. When
Vite starts, it checks ports `8000`, `8001`, and `8002` for the TaskForge API
health endpoint and proxies `/api` requests to the first backend it finds. If
you start the backend after Vite, restart Vite so it can detect the backend.
To use a different API origin, copy `.env.example` to `.env.local`, set
`VITE_API_URL`, and restart Vite.

## Production build

```bat
npm.cmd run build
```

The output is written to `dist`.
