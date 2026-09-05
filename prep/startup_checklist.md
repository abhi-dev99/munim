# Munim.ai — Full System Startup Checklist

Run this top-to-bottom every time you restart the machine.
Estimated time to fully up: ~3 minutes.

---

## STEP 1 — Docker Desktop (Redis dependency)

- [ ] Open **Docker Desktop** from Start menu or taskbar
- [ ] Wait until the Docker whale icon in the system tray stops animating (engine running)
- [ ] Then in any terminal:
  ```
  docker start redis
  ```
- [ ] Verify: `docker ps` → should show `redis` with status `Up`

> ⚠️ If the `redis` container doesn't exist yet (first time after reinstall):
> ```
> docker run -d --name redis -p 6379:6379 redis:alpine
> ```

---

## STEP 2 — Backend + Frontend (one command)

In a terminal at `d:\hackathob\kleos-4.0`:
```
.\start_dev.bat
```

This starts:
- **FastAPI backend** on `http://localhost:8000` (uvicorn --reload)
- **Next.js frontend** on `http://localhost:3000`

- [ ] Backend healthy: `curl http://localhost:8000/health` → `{"status":"ok"}`
- [ ] Frontend live: open `http://localhost:3000` in browser → dashboard loads

---

## STEP 3 — ngrok (WhatsApp webhook tunnel)

In a **new terminal** (keep it open, don't close):
```
ngrok http 8000
```

- [ ] ngrok window shows a `Forwarding` URL like:
  `https://xxxx-xxxx-xxxx.ngrok-free.app → http://localhost:8000`
- [ ] Copy that HTTPS URL

> ⚠️ **CRITICAL:** ngrok gives a NEW URL every time it starts (on the free plan).
> You MUST update the Meta webhook URL if the URL changed.

---

## STEP 4 — Update Meta Webhook (only if ngrok URL changed)

1. Go to [developers.facebook.com](https://developers.facebook.com)
2. Your App → WhatsApp → Configuration → Webhook
3. Replace the Callback URL with:
   `https://YOUR-NEW-NGROK-URL/api/v1/webhook`
4. Verify Token: (whatever is set in your `backend/.env` as `WHATSAPP_VERIFY_TOKEN`)
5. Click **Verify and Save**

- [ ] Send "Hi" to your WhatsApp bot number — bot should respond with onboarding message

> 💡 To check current ngrok URL without opening the window:
> ```
> curl http://127.0.0.1:4040/api/tunnels
> ```
> Look for `public_url` in the JSON.

---

## STEP 5 — Verify the Full Stack

Run these checks in order:

```powershell
# 1. Redis
python -c "import redis; r = redis.from_url('redis://localhost:6379/0', socket_connect_timeout=2); print('Redis:', r.ping())"

# 2. Backend
curl.exe http://localhost:8000/health

# 3. Gemini API key
python -c "import os; from dotenv import load_dotenv; load_dotenv('backend/.env'); from google import genai; from google.genai import types; c=genai.Client(api_key=os.environ['GEMINI_API_KEY']); r=c.models.generate_content(model='gemini-2.5-flash',contents='OK',config=types.GenerateContentConfig(max_output_tokens=5)); print('Gemini:', r.text.strip())"

# 4. Supabase connection
python -c "import os; from dotenv import load_dotenv; load_dotenv('backend/.env'); from supabase import create_client; db=create_client(os.environ['SUPABASE_URL'],os.environ['SUPABASE_SERVICE_ROLE_KEY']); r=db.table('traders').select('id').limit(1).execute(); print('Supabase: OK, traders:', len(r.data))"

# 5. ngrok tunnel
curl.exe -s http://127.0.0.1:4040/api/tunnels | python -c "import sys,json; d=json.load(sys.stdin); print('ngrok:', d['tunnels'][0]['public_url'])"
```

- [ ] Redis: True
- [ ] Backend: `{"status":"ok"}`
- [ ] Gemini: OK / WORKING
- [ ] Supabase: OK, traders: 2+
- [ ] ngrok: shows public URL

---

## STEP 6 — End-to-End WhatsApp Test

- [ ] Send `Hi` to bot → onboarding message received
- [ ] Send a clear invoice photo → "Invoice mil gaya! Processing ho raha hai..." → ITC verdict received
- [ ] Open `http://localhost:3000` → invoice appears in live feed on dashboard

---

## What Each Service Does

| Service | Port | Purpose | Started by |
|---|---|---|---|
| FastAPI backend | 8000 | Webhook handler, invoice pipeline, dashboard API | `start_dev.bat` |
| Next.js frontend | 3000 | CA dashboard | `start_dev.bat` |
| Redis | 6379 | WhatsApp conversation state (onboarding flow) | Docker |
| ngrok | 4040 (local API) | Exposes localhost:8000 to Meta's servers | Manual terminal |
| Docker Desktop | — | Required to run Redis container | Manual / Start menu |

---

## Things That Do NOT Need Restarting

| Service | Why |
|---|---|
| Supabase | Cloud — always on |
| Meta WhatsApp Cloud API | Cloud — always on |
| Gemini API | Cloud — always on |
| GitHub | Cloud — always on |

---

## Common Issues

**Bot not responding after restart:**
→ ngrok URL changed → update Meta webhook (Step 4)

**"Redis connection refused":**
→ Docker Desktop not fully started yet → wait 30s, run `docker start redis` again

**Backend crashes on startup:**
→ Check `backend/.env` exists and has all keys
→ Run `cd backend; pip install -r requirements.txt` if packages missing

**Frontend shows no data / loading forever:**
→ Backend not running → check `http://localhost:8000/health`
→ `NEXT_PUBLIC_API_URL` in `frontend/.env.local` should be `http://localhost:8000`

**Gemini 429 quota error:**
→ Daily limit hit (20 RPD on free tier) → resets at ~12:30 PM IST next day
→ Bot will send a clear Hindi message to the user about this — not a silent failure
