# AI Knowledge Copilot - Quick Start Guide

## Prerequisites
- Python 3.11+
- Node.js 18+
- OpenAI API key (or Anthropic)

## Quick Start (Windows)

### Option 1: Using the startup script
```bash
start.bat
```

### Option 2: Manual setup

1. **Setup Backend**
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

2. **Setup Frontend**
```bash
cd frontend
npm install
```

3. **Configure Environment**
Edit `.env` file and add your OpenAI API key:
```
OPENAI_API_KEY=sk-your-key-here
```

4. **Start Backend**
```bash
cd backend
venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

5. **Start Frontend** (in a new terminal)
```bash
cd frontend
npm run dev
```

## Access the Application

- **Frontend**: http://localhost:3000
- **API Documentation**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

## First Steps

1. **Upload Documents**: Go to Documents panel and upload PDF/DOCX/TXT files
2. **Or Import Mock Data**: Click "Import Slack Data" or "Import Notion Data" buttons
3. **Start Chatting**: Ask questions about your uploaded documents
4. **Try SQL Queries**: Use the SQL panel for natural language database queries
5. **View Analytics**: Check the Analytics dashboard for usage metrics

## Testing Without API Key

The system uses local sentence-transformers for embeddings by default, so you can:
- Upload and process documents
- Test the retrieval system
- View the UI and features

However, you'll need an OpenAI or Anthropic API key for:
- Chat responses
- Query rewriting
- Answer generation
- SQL generation

## Troubleshooting

### Backend won't start
- Check Python version: `python --version` (should be 3.11+)
- Activate venv: `venv\Scripts\activate`
- Install dependencies: `pip install -r requirements.txt`

### Frontend won't start
- Check Node version: `node --version` (should be 18+)
- Install dependencies: `npm install`
- Clear cache: `rm -rf .next` then `npm run dev`

### "Module not found" errors
- Backend: Make sure venv is activated
- Frontend: Delete node_modules and run `npm install` again

## Features to Try

1. **Document Upload**: Upload company policies, manuals, guides
2. **Mock Data**: Import pre-configured Slack/Notion data
3. **Role-Based Chat**: Switch between General/Engineer/HR/Manager roles
4. **Source Citations**: Hover over answers to see source documents
5. **Follow-up Questions**: Click suggested follow-ups
6. **SQL Queries**: Ask questions about the mock employee database
7. **Action Layer**: Try "Create a support ticket for X"
8. **Analytics**: View query metrics and confidence scores

## Development

### Backend
```bash
cd backend
venv\Scripts\activate
pytest tests/
```

### Frontend
```bash
cd frontend
npm run lint
npm run build
```

## Support

For issues or questions, check the main README.md for detailed documentation.
