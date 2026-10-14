# TaskForge backend

The backend targets Python 3.12 or newer. By default, it stores data in the
SQLite file `backend\agentforge.db`; PostgreSQL is not required for local
development. `DATABASE_URL` can optionally be set to use a different database.
The API currently provides registration, login, bearer-token authentication,
owner-scoped goal CRUD, teams, invitations, and scheduled team tasks backed by
SQLAlchemy. A team creator is its leader; invited users become workers. Leaders
assign tasks to one worker or to all workers with a shared task ID and can edit
schedules until completion. Each worker submits their own completion for leader
review; approval updates that worker's progress, and the shared task is complete
after every assigned worker is approved. Goal creation leaves the goal in
`draft`; it does not plan or run it.
Users can optionally set a goal deadline and mark a draft complete. Unfinished
goals with expired deadlines are marked failed when goal data is next requested;
the dashboard refreshes while open. Only draft goals can currently be edited
or deleted.

Teams are private by default. A leader can enable discoverability; signed-in
workers can search visible team names and request to join. A team leader must
approve each join request before the worker becomes a member. Email invitations
remain available as a separate way to add known workers.

## Set up on Windows

Run these commands in Command Prompt from the `backend` directory:

```bat
py -3.12 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
copy .env.example .env
alembic upgrade head
```

Replace `JWT_SECRET` in `.env` with a random secret of at least 32 characters.
You do not need to set `DATABASE_URL` unless you want to override the default
SQLite file. Never commit `.env`.
The application loads `backend\.env` relative to the source file, so the
working directory used to launch Uvicorn does not affect configuration.

## Run the foundation

```bat
uvicorn app.main:app --port 8001 --reload
```

Run the command from `C:\task_devloper\backend`. If launching from the project
root instead, use:

```bat
uvicorn app.main:app --app-dir backend --port 8001 --reload
```

Health checks are available at `http://127.0.0.1:8001/health` and
`http://127.0.0.1:8001/api/v1/health`. The interactive API documentation is at
`http://127.0.0.1:8001/docs`.

The implemented API group is under `/api/v1`:

- `POST /auth/register`, `POST /auth/login`, `GET /auth/me`
- `POST /goals`, `GET /goals`, `GET /goals/{goal_id}`,
  `PATCH /goals/{goal_id}`, `POST /goals/{goal_id}/complete`,
  `DELETE /goals/{goal_id}`
- `POST /teams`, `GET /teams`, `GET /teams/{team_id}`,
  `POST /teams/{team_id}/invites`
- `GET /teams/discover`, `POST /teams/{team_id}/join-requests`,
  `PATCH /teams/{team_id}/join-requests/{request_id}`,
  `PATCH /teams/{team_id}/discoverability`
- `GET /teams/{team_id}/tasks`, `POST /teams/{team_id}/tasks`,
  `POST /teams/{team_id}/tasks/bulk` (one shared task for selected workers),
  `GET /tasks/{task_id}`, `PATCH /tasks/{task_id}/schedule`,
  `POST /tasks/{task_id}/submit`, `POST /tasks/{task_id}/review`
- `GET /notifications/vapid-public-key`,
  `GET|POST|DELETE /notifications/subscriptions`

Run `alembic upgrade head` to create the current authentication and goals
schema in `backend\agentforge.db`. This also adds team, task, assignment, and
push-subscription tables.

## Browser push notifications

Browser push uses the free Web Push protocol and the `pywebpush` library. Create
the VAPID key pair outside the repository so the private key is not committed.
From PowerShell at the workspace root:

```powershell
$Vapid = "C:\task_devloper\.venv\Scripts\vapid.exe"
$KeyDirectory = Join-Path $env:USERPROFILE ".agentforge-vapid"
New-Item -ItemType Directory -Path $KeyDirectory -Force | Out-Null
if (Test-Path (Join-Path $KeyDirectory "private_key.pem")) {
    throw "VAPID keys already exist; keep using them instead of replacing them."
}
Push-Location $KeyDirectory
& $Vapid --gen
$VapidPublicKey = & $Vapid --applicationServerKey
Pop-Location
$VapidPublicKey
```

The app loads `backend\.env.push` after `backend\.env`; this local-only file is
ignored by Git. Put the printed public key and private-key **path** in
`backend\.env.push`, not `.env.example`. Keep `private_key.pem` outside the
repository:

```dotenv
VAPID_PUBLIC_KEY=<printed-public-key>
VAPID_PRIVATE_KEY=C:/Users/<your-user>/.agentforge-vapid/private_key.pem
VAPID_SUBJECT=mailto:<your-contact-email>
CORS_ORIGINS=["http://127.0.0.1:5173","http://localhost:5173"]
```

Install dependencies, migrate the existing SQLite database, and run the
backend from Command Prompt or PowerShell:

```powershell
Set-Location C:\task_devloper\backend
& ..\.venv\Scripts\python.exe -m pip install -r requirements.txt
& ..\.venv\Scripts\python.exe -m alembic upgrade head
& ..\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8001 --reload
```

In a second terminal, run the frontend:

```powershell
Set-Location C:\task_devloper\frontend
npm.cmd install
npm.cmd run dev
```

Sign in, click **Enable notifications** on the dashboard, and allow the browser
prompt. Enable notifications separately in each browser/device that should
receive them. Then submit a team task as a worker and approve or reject it as the
team leader. Leaders receive a notification when a worker submits work, and
workers receive one when the leader assigns a task or approves/rejects their
submission. The browser displays native notifications; clicking one opens the
team task view. Push is delivered by browser push services, not by an app-owned
paid notification provider. Localhost is treated as a secure context for local
development; production deployments must serve the site over HTTPS.

Run the backend tests with `..\.venv\Scripts\python.exe -m pytest` from the
`backend` directory. Tests mock the outbound push provider; an actual browser
push requires configured VAPID keys and a real browser subscription.

## Run tests

```bat
python -m pytest
```
