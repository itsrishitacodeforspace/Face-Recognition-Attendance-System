# Login Configuration - Quick Setup

## ✅ CORS Configuration Fixed

Your CORS (Cross-Origin Resource Sharing) settings have been configured to allow the frontend to communicate with the backend API for login.

### What Changed

**Backend Configuration** (`backend/.env`):
```
DEBUG=true                          # Enable development debugging
ENVIRONMENT=development             # Use development mode
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000,http://localhost:4173,http://127.0.0.1:4173
VITE_API_URL=http://localhost:8000  # Frontend knows where backend is
```

**Frontend Configuration** (`frontend/.env`):
```
VITE_API_URL=http://localhost:8000  # Point to backend API
```

## 🚀 How to Start

### Option 1: Using npm/python directly

**Terminal 1 - Start Backend:**
```bash
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Start Frontend:**
```bash
cd frontend
npm install  # if not already installed
npm run dev  # starts on http://localhost:5173
```

### Option 2: Using docker-compose

```bash
docker-compose up --build
# Backend: http://localhost:8000
# Frontend: http://localhost:5173
```

## 🔐 Login Credentials

- **Username**: `admin`
- **Password**: `admin123`

Login URL: **http://localhost:5173**

## ⚙️ CORS Explained

CORS (Cross-Origin Resource Sharing) is a browser security feature. When:
- Frontend runs on: `http://localhost:5173`
- Backend runs on: `http://localhost:8000`

They're on different ports → browser blocks requests → CORS needed

The `CORS_ALLOWED_ORIGINS` setting tells the backend which frontend can access it.

## 🔧 Customizing CORS (if needed)

If your frontend runs on a different port/host:

```bash
# Edit backend/.env
CORS_ALLOWED_ORIGINS=http://your-frontend-host:port,http://localhost:5173
```

Example - if frontend is on port 8080:
```
CORS_ALLOWED_ORIGINS=http://localhost:8080,http://127.0.0.1:8080,http://localhost:5173,http://127.0.0.1:5173
```

Then restart the backend.

## ✅ Troubleshooting

**If login still fails:**

1. **Check backend is running:**
   ```bash
   curl http://localhost:8000/health
   # Should return: {"status":"ok"}
   ```

2. **Check frontend API URL:**
   - Open browser DevTools (F12) → Console
   - Should see no CORS errors
   - Network tab should show requests to `http://localhost:8000/api/auth/login`

3. **Check environment variables are loaded:**
   - Backend logs should show: `CORS allowed origins: [...]`
   - If not, restart backend

4. **Clear browser cache:**
   ```
   Ctrl+Shift+Delete and clear all
   ```

## 📝 Summary

✅ Backend configured to accept frontend requests
✅ Frontend configured to send requests to backend API
✅ CORS allows all standard localhost development ports
✅ Ready for login!

Now start both services and you should be able to login! 🎉
