# Locas - Location Context Assistant

## Overview

Locas is a location-based context assistant that provides information and insights about geographic locations. The application maintains session context to ensure continuity in the conversation flow, allowing users to refer to previously mentioned locations.

## Features

- Process natural language queries involving locations
- Extract location information from text, coordinates, or Google Maps URLs
- Analyze locations for land purchase suitability or business viability
- Maintain conversation context and location memory across user queries
- Redis-backed session management for reliability

## Session Management

The application uses a robust session management system:

1. Frontend generates a unique session ID using timestamp + random string
2. Session ID is stored in localStorage for persistence
3. Session ID is included with every API request
4. Backend stores session data in Redis with 24-hour expiration
5. Location data is maintained within the session for context-aware queries

## Development Setup

### Prerequisites

- Docker and Docker Compose
- Node.js 16+
- Python 3.8+

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/locas.git
cd locas
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys
```

3. Start the application with Docker Compose:
```bash
docker-compose up
```

4. Access the application:
- Frontend: http://localhost:3000
- Backend API: http://localhost:5000

## Debug Mode

To enable more verbose session debugging, add to your .env:
```
DEBUG_SESSION=true
```

## API Endpoints

- `POST /api/process-query`: Process a location query
  - Required parameters: `query` (string), `session_id` (string)
  - Returns: Query result with location information

- `GET /api/get-history`: Retrieve chat history for a session
  - Required parameters: `session_id` (string)
  - Returns: Array of chat messages for the given session

## Architecture

```
├── frontend (Next.js)
│   ├── components
│   ├── lib
│   │   ├── api.ts - API client with session handling
│   │   └── auth.ts 
│   └── pages
│       └── index.tsx - Main chat interface with session management
│
├── backend (Flask)
│   ├── app.py - Main Flask application
│   ├── services
│   │   └── redis_service.py - Redis session service
│   └── assistant
│       ├── location_assistant.py - Core location processing
│       └── location_parser.py - Location extraction
│
└── docker-compose.yml - Service definitions including Redis
```

## License

[MIT License](LICENSE)