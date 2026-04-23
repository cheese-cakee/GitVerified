# GitVerified - Local AI-Powered Candidate Evaluation

**100% Free. 100% Private. 100% Local.**

Evaluate candidates using local AI models - no API tokens, no subscriptions, no data leaving your machine.

## 🚀 Quick Start (5 Minutes)

### 1. Install Ollama

Download from [ollama.ai](https://ollama.ai/download) or:

```bash
# Windows: Download installer from website
# Mac/Linux:
curl -fsSL https://ollama.ai/install.sh | sh
```

### 2. Download AI Model

```bash
ollama pull qwen3.5:4b
```

### 3. Start Backend

```bash
# Windows
start.bat

# Or manually:
python api_server.py
```

### 4. Start Frontend

```bash
cd gitverified-web
npm install
npm run dev
```

### 5. Open http://localhost:3000/engine

## 🏗️ Architecture

```
Frontend (Next.js :3000)
    │
    ▼
Backend (Python :3001)
    │
    ├── Integrity Agent
    ├── Code Quality Agent
    ├── Uniqueness Agent
    └── Relevance Agent
         │
         ▼
     Ollama (qwen3.5:4b :11434)
```

## 📊 What Gets Evaluated

| Agent        | Score | What It Checks                                     |
| ------------ | ----- | -------------------------------------------------- |
| Integrity    | 0-10  | Resume authenticity, hidden text, keyword stuffing |
| Code Quality | 0-100 | Security, best practices, documentation            |
| Uniqueness   | 0-10  | Original work vs tutorial clones                   |
| Relevance    | 0-10  | Job requirements match                             |

## 💰 Cost Comparison

| Solution         | Cost           | Privacy           |
| ---------------- | -------------- | ----------------- |
| Traditional SaaS | $0.10+/eval    | ❌ Data shared    |
| **GitVerified**  | **$0 forever** | ✅ **100% local** |

## 📁 Project Structure

```
candidateai/
├── api_server.py         # Python API server
├── agents/               # AI evaluation agents
│   ├── hybrid_model.py   # Ollama integration
│   ├── integrity.py
│   ├── code_quality.py
│   ├── uniqueness.py
│   └── relevance.py
├── gitverified-web/      # Next.js frontend
├── start.bat             # Windows quick start
└── docker-compose.simple.yml
```

## 📄 License

MIT License - Use freely in your hiring process.

---

**Built for engineers who value privacy and hate subscriptions.**
