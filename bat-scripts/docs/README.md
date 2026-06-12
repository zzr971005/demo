# Bat Startup Folder - Usage Guide

## Folder Structure

```
bat-scripts/
├── start-dev.bat          # Development mode startup (recommended)
├── start-frontend.bat     # Frontend only startup
├── start.bat              # Full service launcher
└── README.md              # This file
```

## Quick Start

### 1. Development Mode (Recommended for Coding)

Double-click or run in terminal:
```powershell
.\bat-scripts\start-dev.bat
```

**What it does:**
- Checks PostgreSQL and Redis local services
- Starts backend with hot-reload (port 8000)
- Starts frontend with HMR (port 5173)
- Opens separate windows for each service

**Requirements:**
- PostgreSQL 17 (local service)
- Redis (local service)
- Python 3.11+ with Poetry
- Node.js 18+

### 2. Frontend Only

```powershell
.\bat-scripts\start-frontend.bat
```

**Use case:** When backend is already running and you only need to work on UI.

### 3. Full Service Mode

```powershell
.\bat-scripts\start.bat
```

**What it does:**
- Interactive menu for starting all services
- Starts PostgreSQL, Redis, backend, and frontend

## Environment Setup

### Step 1: Install PostgreSQL and Redis

1. Install PostgreSQL 17: https://www.postgresql.org/download/windows/
2. Install Redis: https://github.com/tporadowski/redis/releases
3. Ensure both are registered as Windows services
4. Verify installation:
   ```powershell
   pg_isready -h localhost -p 5432
   redis-cli ping
   ```

### Step 2: Backend Environment

```powershell
cd backend
poetry install
poetry shell
```

### Step 3: Frontend Environment

```powershell
cd frontend
npm install
```

### Step 4: Environment Variables

Copy example file and configure:
```powershell
copy backend\.env.example .env
```

Edit `.env` with your settings:
- `TQSDK_ACCOUNT` - Your TQSDK account
- `TQSDK_PASSWORD` - Your TQSDK password
- Database credentials (optional, defaults work for local dev)

## Troubleshooting

### Database Not Running

**Error:** `PostgreSQL: Stopped` or `Redis: Not installed`

**Solution:**
1. Start PostgreSQL service: `net start postgresql-x64-17`
2. Start Redis service: `net start redis`
3. Or use the startup script option [3] to start infrastructure

### Port Already in Use

**Error:** `Port XXXX is in use`

**Solution:**
- Script automatically kills processes using required ports
- If still failing, manually check: `netstat -ano | findstr "8000"`
- Kill process: `taskkill /F /PID <PID>`

### Poetry Environment Not Found

**Error:** `Poetry virtual environment not found`

**Solution:**
```powershell
cd backend
poetry install
```

### Node Modules Not Found

**Error:** `node_modules not found`

**Solution:**
```powershell
cd frontend
npm install
```

## Development Workflow

### Daily Development

1. **Ensure infrastructure is running:**
   ```powershell
   # PostgreSQL and Redis should already be running as services
   pg_isready -h localhost -p 5432
   redis-cli ping
   ```

2. **Start backend (Terminal 1):**
   ```powershell
   cd backend
   poetry run uvicorn app.main:app --reload
   ```

3. **Start frontend (Terminal 2):**
   ```powershell
   cd frontend
   npm run dev
   ```

4. **Access services:**
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Using start-dev.bat (One Command)

Simply run:
```powershell
.\bat-scripts\start-dev.bat
```

This does all of the above automatically and opens separate windows for each service.

## Hot Reload / HMR

### Backend (FastAPI)
- Auto-reloads on Python file changes
- `--reload` flag enabled in start-dev.bat
- Changes effective immediately

### Frontend (Vite + React)
- Hot Module Replacement (HMR)
- Instant UI updates without page refresh
- State preserved during development

## Service Ports

| Service | Port | Description |
|---------|------|-------------|
| Backend API | 8000 | FastAPI application |
| Frontend | 5173 | Vite dev server |
| TimescaleDB | 5432 | PostgreSQL/TimescaleDB |
| Redis | 6379 | Cache/Message queue |

## Stopping Services

### Method 1: Via start-dev.bat
- Press any key in the main window
- Automatically stops backend and frontend

### Method 2: Manual Stop
```powershell
# Stop backend/frontend port processes
taskkill /F /FI "WINDOWTITLE eq Backend*"
taskkill /F /FI "WINDOWTITLE eq Frontend*"
```

### Method 3: Task Manager
- Find Python processes (backend)
- Find Node.js processes (frontend)
- End tasks manually

## Coding Standards

### Batch File Encoding
- **Must use ASCII characters only** (no Chinese characters)
- This prevents encoding issues on Windows
- All output is in English

### Path Handling
- Scripts use `%~dp0` to get their own directory
- Navigate to parent folder for project root: `%~dp0..\`
- Works regardless of where you run the script from

## Architecture Overview

```
┌─────────────────────────────────────────┐
│         Local Services                  │
│  ┌──────────────┐  ┌──────────────┐    │
│  │  PostgreSQL  │  │    Redis     │    │
│  │   :5432      │  │   :6379      │    │
│  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────┘
                    │
┌─────────────────────────────────────────┐
│         Application Layer               │
│  ┌──────────────┐  ┌──────────────┐    │
│  │   Backend    │  │   Frontend   │    │
│  │   :8000      │  │   :5173      │    │
│  │  --reload    │  │    HMR       │    │
│  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────┘
```

## Support

For issues or questions, refer to:
- Project documentation in `/doc` folder
- TQSDK documentation: https://doc.shinnytech.com/
- FastAPI docs: https://fastapi.tiangolo.com/
