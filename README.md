# CampusOS AI

CampusOS AI is a campus operations platform prototype with a FastAPI backend and a React frontend. It brings academic information, student services, policy-aware decisions, and AI-assisted campus requests into one interface.

## Project structure

```text
backend/     FastAPI API, SQLAlchemy models, seed data, and policy logic
frontend/    React and Vite web application
```

## Prerequisites

- Python 3.10 or newer
- Node.js 18 or newer
- npm

## Run the backend

Open a terminal in the project root:

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload
```

The API runs at `http://localhost:8000`. Interactive API documentation is available at `http://localhost:8000/docs`.

If the backend uses AI features, create `backend/.env` and add your local configuration:

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=your_model_name
```

## Run the frontend

Open a second terminal in the project root:

```powershell
cd frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:5173`.

If needed, configure the API URL in `frontend/.env`:

```env
VITE_API_BASE_URL=http://localhost:8000
```

## Frontend commands

```powershell
npm run dev      # Start the development server
npm run build    # Create a production build
npm run lint     # Check the source with ESLint
npm run preview  # Preview the production build
```

## Security

Do not commit `.env` files, API keys, virtual environments, databases, or generated build folders. These files are excluded by `.gitignore`.
