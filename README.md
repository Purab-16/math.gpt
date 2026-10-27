# Math Solver 📐

A web application where users can input a math problem via text or by uploading an image. The application returns a step-by-step solution rendered with KaTeX and recommends related educational YouTube videos for the topic.

---

## Tech Stack

- **Backend:** Python + FastAPI
- **AI Solving:** Google Gemini API (multimodal text & image processing)
- **Video Recommendations:** YouTube Data API v3
- **Frontend:** Plain HTML, CSS, JavaScript (served directly by FastAPI)
- **Math Rendering:** KaTeX (loaded via CDN)

---

## Folder Structure

```
math-solver/
  app/
    main.py                 # FastAPI application, routing, and static file mounting
    config.py               # Environment configuration (.env loader)
    schemas.py              # Pydantic data schemas for requests and responses
    routes/
      solve.py              # POST /solve endpoint handler
    services/
      ai_service.py         # Gemini API service stub
      youtube_service.py    # YouTube Data API v3 service stub
  static/
    index.html              # Frontend user interface
    style.css               # Clean and responsive styling
    script.js               # Client-side form handling and KaTeX math rendering
  .env.example              # Template for required environment variables
  .gitignore                # Git ignore rules for venv, cache, and secrets
  requirements.txt          # Python project dependencies
  README.md                 # Project documentation and setup guide
```

---

## Setup Instructions

### 1. Navigate to the project directory
Open your terminal and navigate to the project folder:
```bash
cd math-solver
```

### 2. Create and activate a virtual environment
- **On Windows (PowerShell):**
  ```powershell
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  ```
- **On Windows (Command Prompt):**
  ```cmd
  python -m venv venv
  venv\Scripts\activate.bat
  ```
- **On macOS / Linux:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

### 3. Install dependencies
Install the required Python packages:
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables
Create a `.env` file from the example template:
- **On Windows (PowerShell / CMD):**
  ```powershell
  copy .env.example .env
  ```
- **On macOS / Linux:**
  ```bash
  cp .env.example .env
  ```

Open `.env` and configure your API keys:
```env
GEMINI_API_KEY=your_gemini_api_key_here
YOUTUBE_API_KEY=your_youtube_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```

---

## Running the Application

Start the FastAPI development server:
```bash
uvicorn app.main:app --reload
```

The server will start at: `http://127.0.0.1:8000`

---

## Testing the Setup

1. **Verify Health Check Endpoint:**
   - In your browser, open: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
   - Or using `curl`:
     ```bash
     curl http://127.0.0.1:8000/health
     ```
   - Expected response:
     ```json
     {"status": "ok"}
     ```

2. **Access the Web App:**
   - Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.
   - Enter a math question or choose an image, then click **Solve Problem**.
   - You will see the dummy step-by-step solution rendered with KaTeX and sample video recommendations.

3. **Interactive API Documentation:**
   - Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
   - ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
