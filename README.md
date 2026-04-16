# Smart Venue Experience System

A production-grade, highly-scalable attendee experience and crowd management platform designed for huge sporting events (Olympics / FIFA scale).

## Architecture

*   **Frontend**: Next.js 14 utilizing App Router, structured with a component-first React paradigm. Employs raw CSS with Glassmorphism for a high-performance premium UI.
*   **Backend Decision Engine**: A Python FastAPI service implementing dynamic graph pathfinding. Evaluates absolute distances mixed with real-time congestion weights.
*   **Database (Planned)**: Production readiness targets Firestore, utilizing Node/Python admin SDKs for synchronization across nodes. (Currently running mock data for immediate demo viability).
*   **Deployment**: Backend containerized for Google Cloud Run (`backend/Dockerfile`).

## Setup Instructions

### 1. Backend (FastAPI Decision Engine)
The backend acts as the intelligent crowd routing manager.

```bash
cd backend
python -m venv venv
# On Windows: venv\\Scripts\\activate
# On Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
python main.py
```
*The backend will run on `http://localhost:8000`*

### 2. Frontend (Next.js Application)
Provides the Attendee and Admin UI.

```bash
cd frontend
npm install
npm run dev
```
*The frontend will run on `http://localhost:3000`*

## How to Demo
1. Open the frontend across two tabs (Admin and Attendee View).
2. On the **Admin View**, you will see the live heatmap pinging the backend every 3 seconds for dynamic node densities.
3. On the **Attendee View**, input a starting and destination location. The UI will request an optimal route from the FastAPI engine.
4. Try clicking "Simulate Bottleneck" in the Admin panel for a specific node, and re-run the attendee route to see the Decision Engine intelligently adapt and route around the congestion.
5. Check the `EMERGENCY MODE` toggle to see how the mathematical parameters forcefully shortcut around standard flow.
