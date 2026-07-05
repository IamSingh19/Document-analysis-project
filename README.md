# DocMind AI - Chat with Your Documents

A web app where you upload documents (PDFs, Word files, etc.) and ask an AI questions about them. The AI reads your documents and gives you answers with sources.

## What It Does

📄 **Upload Documents** - Add PDFs, Word docs, spreadsheets  
🔍 **Smart Search** - Find information in your documents  
💬 **AI Chat** - Ask questions and get answers from your documents  
👥 **Team Workspaces** - Share documents with teammates  
📊 **Analytics** - See what you've uploaded and searched

## How It Works

1. **Upload a document** → AI reads and indexes it
2. **Ask a question** → AI searches your documents
3. **Get answer** → AI tells you the answer + which document it came from

## Setup (Quick Start)

### What You Need
- Python 3.8+ installed
- Node.js 16+ installed
- A computer with 4GB+ RAM

### Step 1: Backend Setup
```bash
cd backend
pip install -r requirements.txt
python main.py
```
Backend will start on http://localhost:8000

### Step 2: Frontend Setup (new terminal)
```bash
cd frontend
npm install
npm run dev
```
Frontend will start on http://localhost:3000

### Step 3: Use It
Go to http://localhost:3000 in your browser

## How to Use

### Register/Login
1. Go to http://localhost:3000
2. Create account with email and password
3. Login

### Upload Documents
1. Go to "Documents" page
2. Click "Upload" button
3. Select a file (PDF, Word, TXT, etc.)
4. Wait for processing (shows "completed" status)

### Ask Questions
1. Go to "Chat" page
2. Select a document or upload new one
3. Type your question
4. AI answers with sources

### Search
1. Go to "Search" page
2. Type what you're looking for
3. See results from your documents

## What Technologies Are Used

**Frontend (what you see)**
- Next.js 15 - React framework
- Tailwind CSS - Styling
- Zustand - State management

**Backend (the engine)**
- FastAPI - Python web server
- PostgreSQL - Database
- FAISS - Search engine
- BGE-M3 - AI model for understanding text
- Groq - Fast AI responses

**How It All Works**
1. You upload file → Backend saves it
2. Backend extracts text from file
3. Breaks text into chunks
4. Creates "embeddings" (AI understanding of text)
5. Stores in search engine
6. When you ask question → AI searches and answers

## Tech Stack (Simple Breakdown)

| Part | Technology | What It Does |
|------|-----------|------------|
| Website | Next.js | What you see and click |
| Server | FastAPI | Handles uploads, processes documents |
| Database | PostgreSQL | Stores your documents and chats |
| Search | FAISS | Finds relevant documents |
| AI Brain | BGE-M3 | Understands document content |
| Fast Answers | Groq | Answers questions quickly |

## Files You Need to Know

```
DocMind AI/
├── backend/              # The brain
│   ├── main.py          # Starts the server
│   ├── routes/          # API endpoints
│   ├── services/        # Document processing
│   └── models.py        # Database structure
│
├── frontend/            # What you see
│   ├── app/            # Pages (Documents, Chat, Search)
│   ├── components/     # Buttons, forms, etc.
│   └── lib/            # Helper code
│
└── docker-compose.yml  # For deployment
```

## Troubleshooting

### "Upload stuck in processing"
- Check backend is running
- Backend console should show steps: [1/6], [2/6], etc.
- If error, restart backend

### "PDF with images failed"
- PDFs with lots of images may not work well
- System extracts only text parts
- Try text-based PDFs first

### "Can't connect to backend"
- Make sure backend is running: `python backend/main.py`
- Check http://localhost:8000/health in browser

### "Database error"
- On first run, database auto-creates
- If issues, delete `backend/docmind.db` and restart

## Environment Setup

Create `.env` file in backend:
```
DATABASE_URL=sqlite:///./docmind.db
SECRET_KEY=your-secret-key-minimum-32-characters
GROQ_API_KEY=your-groq-api-key
EMBEDDING_MODEL=BAAI/bge-m3
```

Get GROQ_API_KEY from: https://console.groq.com

## Limits

- Max file size: 50 MB
- Max documents: Unlimited
- Supported formats: PDF, DOCX, PPTX, TXT, CSV, MD

## Current Issues & Fixes

### Issue: PDFs with images fail
**Fix**: System now handles mixed text/image PDFs. Image pages are marked but don't crash processing.

### Issue: Large files timeout
**Fix**: Processing in batches now. Shows progress: "Batch 20/80 stored"

### Issue: "Filesystem error" on Windows
**Fix**: Cache directories configured for Windows compatibility

## Development

### Run Tests
```bash
python backend/test_upload.py
```

### Check Database
```bash
python backend/check_db_contents.py
```

### Monitor Processing
```bash
python backend/test_upload_live.py
```

## Next Features (Soon)

✓ Document OCR (read scanned PDFs)  
✓ Real-time collaboration  
✓ Document versioning  
✓ Advanced analytics  
✓ Integration with cloud storage  

## Production Deployment

### Frontend
Deploy to Vercel (free)
```bash
vercel deploy
```

### Backend
Deploy to Railway or Render
```bash
git push  # Deploys automatically
```

### Database
Use managed PostgreSQL (AWS RDS, Railway, etc.)

## Security

- Passwords hashed with bcrypt
- JWT tokens for login
- Rate limiting on API
- Input validation on all forms
- No sensitive data in logs

## Support

**Issues?** Check:
1. Backend console for error messages
2. Browser console (F12) for frontend errors
3. Check QUICK_START.md for setup help
4. Check IMAGE_PDF_QUICK_FIX.md for PDF issues

## License

This project is production-grade enterprise software.

---

## Quick Reference

**Start everything:**
```bash
# Terminal 1
cd backend
python main.py

# Terminal 2
cd frontend
npm run dev

# Then go to http://localhost:3000
```

**Upload → Chat → Search**
That's it! Simple as that.

---

**Version**: 1.0.0  
**Status**: Production Ready  
**Last Updated**: July 5, 2026
