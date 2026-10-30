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
    main.py               # app setup, error handlers, security headers
    config.py             # reads the .env file
    schemas.py            # request and response models
    exceptions.py         # our own error types
    cache.py              # small in-memory cache
    rate_limit.py         # limits requests per IP
    image_utils.py        # checks uploaded images
    routes/
      solve.py            # /solve and /solve/image
    services/
      ai_service.py       # talks to Gemini
      youtube_service.py  # finds YouTube videos
  tests/
    conftest.py           # clean state before each test
    test_solve.py
    test_image.py
    test_cache.py
    test_security.py
    test_youtube.py
  static/
    index.html            # the page
    style.css             # light and dark themes
    script.js             # form, photo upload, history
    theme.js              # sets the saved theme early
    fonts/                # Atkinson Hyperlegible Next
  .env.example            # copy this to .env
  requirements.txt
  README.md
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

