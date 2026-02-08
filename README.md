# GAMIFIED SAVINGS APP - HACKATHON PROJECT

## Project Overview
A gamified personal finance application that transforms savings goals into an engaging, social experience through AI-powered level progression, social accountability, and game mechanics.

## Team
- **Anna**: Backend Development (Python/Flask, MongoDB, APIs)
- **Aadya**: Frontend Development (React, UI/UX, Components)
- **Suhani**: Integration & Features (API client, State management, Special features)

## Tech Stack
- **Frontend**: React.js (Vite), Tailwind CSS, shadcn/ui, Framer Motion, Recharts
- **Backend**: Python (Flask), PyMongo
- **Database**: MongoDB Atlas
- **AI**: Google AI Studio API (Gemini models)
- **Banking**: Capital One Nessie API (sandbox)

## Project Structure
```
Advisory/
├── backend/              # Python Flask backend
│   ├── models/          # Database models
│   ├── routes/          # API endpoints
│   ├── utils/           # Helper functions (Nessie, AI)
│   ├── config/          # Configuration files
│   ├── app.py           # Main Flask application
│   └── requirements.txt # Python dependencies
├── frontend/            # React frontend
│   ├── src/
│   │   ├── components/  # React components
│   │   ├── pages/       # Page components
│   │   ├── services/    # API client
│   │   ├── context/     # State management
│   │   └── utils/       # Helper functions
│   ├── package.json
│   └── vite.config.js
├── docs/                # Documentation
├── scripts/             # Utility scripts (seeding, etc.)
└── README.md
```

## Core Features (MVP)
- [x] User authentication with JWT
- [ ] Bank account connection (Nessie API)
- [ ] AI-calculated flexible level system
- [ ] Gamification: Points, currency, streaks
- [ ] Side quests system
- [ ] Social features: Friends, veto cards, leaderboard
- [ ] AI assistant chatbot
- [ ] Dashboard with progress tracking

## Setup Instructions

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # Configure your API keys
python app.py
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

## Environment Variables

### Backend (.env)
```
MONGODB_URI=your_mongodb_connection_string
JWT_SECRET=your_jwt_secret_key
NESSIE_API_KEY=your_nessie_api_key
GOOGLE_AI_API_KEY=your_google_ai_api_key
```

### Frontend (.env)
```
VITE_API_BASE_URL=http://localhost:5000/api
```

## Demo
Demo user credentials will be added before presentation.

## Timeline
15-hour hackathon implementation with checkpoints at:
- Hour 4-5: Core integration test
- Hour 8-9: Full feature test
- Hour 12-15: Deployment and demo prep
