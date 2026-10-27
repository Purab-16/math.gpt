# math.gpt 📐

math.gpt is a web application where users can input a math problem via text or by uploading an image. The application returns a step-by-step solution rendered with KaTeX and recommends related educational YouTube videos for the topic.

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
math-gpt/
  app/
    main.py                 # FastAPI app, error handlers, security headers, size limit
    config.py               # Environment configuration (.env loader)
    schemas.py              # Pydantic data schemas for requests and responses
    exceptions.py           # Custom exceptions (invalid input, AI errors, rate limits)
    cache.py                # Shared in-memory cache with expiry
    rate_limit.py           # Per-IP rate limiter for solve endpoints
    image_utils.py          # Safe image reading and type detection
    routes/
      solve.py              # POST /solve and POST /solve/image handlers
    services/
      ai_service.py         # Gemini math solver (text and image) with cache
      youtube_service.py    # YouTube Data API v3 video search with cache
  tests/
    conftest.py             # Resets caches and rate limiter before each test
    test_solve.py           # /solve endpoint tests (Gemini and YouTube are mocked)
    test_image.py           # /solve/image endpoint tests
    test_cache.py           # Cache and Gemini cache tests
    test_security.py        # Security headers, rate limit, request size tests
    test_youtube.py         # YouTube service tests (HTTP is mocked)
  static/
    index.html              # Frontend user interface
    style.css               # Styling, light and dark themes
    script.js               # Form handling, photo upload, live preview, KaTeX rendering
    theme.js                # Applies the saved light/dark theme before the page draws
    fonts/                  # Self-hosted Atkinson Hyperlegible Next font (OFL license)
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
cd math-gpt
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
GEMINI_MODEL=gemini-3.8-flash
APP_ENV=development
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
   - Enter a math question, or upload a photo of it (PNG, JPEG, WEBP, max 10 MB).
   - With an image, you can also type a hint like "Only solve Q3".
   - Pick a detail level and language, then click **Solve Problem**.
   - You will see a step-by-step solution from Gemini rendered with KaTeX.
   - Related YouTube videos appear below the solution. Hinglish mode shows both Hindi and English videos.
   - Large photos are resized and compressed in the browser before upload.
   - Solved questions are saved under **History** in your browser only (last 50). Click one to see it again without a new API call.

3. **Run the Tests:**
   ```bash
   pip install pytest
   pytest tests -v
   ```

4. **Interactive API Documentation (development only):**
   - Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
   - ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
   - These pages are turned off when `APP_ENV=production`.

---

## API Endpoints

| Method | Path | Input | Notes |
|---|---|---|---|
| GET | `/health` | none | Returns `{"status": "ok"}` |
| POST | `/solve` | JSON: `question`, `difficulty`, `language` | Text question |
| POST | `/solve/image` | Form data: `image`, `question` (optional), `difficulty`, `language` | Image question |

Both solve endpoints are limited to 10 requests per minute per IP address.

---

## Deploying to Render (Free Tier)

### Before you start
- Push the project to GitHub. Check that `.env` is **not** in the repo (it is in `.gitignore`, and the pre-commit hook blocks it).
- Keep your Gemini and YouTube keys ready. They go into the Render dashboard, never into code.

### Steps
1. Sign in at [render.com](https://render.com) and click **New > Web Service**.
2. Connect your GitHub repo.
3. Fill in the settings:

   | Setting | Value |
   |---|---|
   | Root Directory | Leave empty if the repo root is `math-gpt/`. Otherwise enter `math-gpt` |
   | Runtime | Python 3 |
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips="*"` |
   | Instance Type | Free |
   | Health Check Path | `/health` |

4. Under **Environment**, add these variables:

   | Key | Value |
   |---|---|
   | `GEMINI_API_KEY` | Your Gemini key |
   | `YOUTUBE_API_KEY` | Your YouTube key |
   | `GEMINI_MODEL` | `gemini-3.8-flash` |
   | `APP_ENV` | `production` |
   | `PYTHON_VERSION` | Your local version from `python --version` |

5. Click **Create Web Service**. After the build, open the `.onrender.com` URL.

### Notes
- `--proxy-headers` is required. Without it, every user looks like the same IP and the rate limiter blocks everyone together.
- The free tier sleeps after about 15 minutes with no traffic. The first request after that takes 30 to 60 seconds.
- Caches and rate limit counters live in memory, so they reset when the server sleeps or restarts.

---

## Security Checklist

### Built into the app
- Per-IP rate limit (10 requests per minute) on solve endpoints.
- Request size limit (about 11 MB) checked before the body is read.
- Images are checked by their first bytes (magic bytes), not by file name. Only PNG, JPEG, WEBP.
- Images are never saved to disk or logged. Only their size is logged.
- Security headers: Content-Security-Policy, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy, and HSTS in production.
- KaTeX CDN files are loaded with Subresource Integrity (SRI) hashes.
- No CORS headers, so other websites cannot call the API from a browser.
- Generic error messages. No stack traces, keys, or raw model output are returned.
- API docs are turned off in production.

### Do this yourself in Google Cloud Console
1. **YouTube key:** Go to **APIs & Services > Credentials**, open the key, and under **API restrictions** select only **YouTube Data API v3**.
2. **Gemini key:** In Google AI Studio or Cloud Console, set a usage or budget limit so a bug or abuse cannot run up costs.
3. Never share keys in chat, screenshots, or commits. If a key leaks, delete it and create a new one.
