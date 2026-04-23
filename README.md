# 🎯 Face Recognition Attendance System

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![InsightFace](https://img.shields.io/badge/InsightFace-buffalo__l-FF6B35?style=for-the-badge)](https://github.com/deepinsight/insightface)
[![FAISS](https://img.shields.io/badge/FAISS-1.9-blue?style=for-the-badge)](https://github.com/facebookresearch/faiss)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

**A production-grade, real-time face recognition attendance platform.**  
Upload reference photos → train in one click → recognize faces live via webcam or video stream.

[Features](#-features) • [How It Works](#-how-it-works) • [Installation](#-installation) • [Usage](#-usage) • [API](#-api-reference) • [Results](#-results)

</div>

---

## 🔍 Project Overview

### What does this project do?

This system automates attendance tracking using **face recognition**. Instead of manually signing in, a person simply walks past a camera. The system detects their face, compares it against a database of known people, and marks their attendance automatically — all in real time.

### The problem it solves

Traditional attendance systems (paper sign-ins, card swipes, PIN entry) are:
- **Slow** — queues form at entry points
- **Forgeable** — colleagues can sign in for each other ("buddy punching")
- **Manual** — require administrative overhead to reconcile records

This system solves all three: it's instant, biometric (you can't lend your face), and fully automated with a dashboard for analytics.

---

## ✨ Features

| Category | Details |
|---|---|
| **Backend** | Async FastAPI, SQLAlchemy ORM, SQLite |
| **Auth** | JWT with refresh tokens, bcrypt hashing, login rate limiting |
| **Face AI** | InsightFace `buffalo_l` model — detection + 512-d embeddings |
| **Search** | FAISS `IndexFlatIP` for cosine-similarity vector search |
| **Streaming** | WebSocket live recognition from webcam / file / RTSP |
| **Frontend** | React + Vite + Tailwind + Chart.js — dashboard, heatmap, trends, CRUD |
| **CUDA** | Auto-detects GPU; gracefully falls back to CPU |
| **Testing** | pytest suite for recognition logic and attendance cooldown |

---

## 🧠 How It Works

> **New to deep learning?** This section explains the core concepts from first principles.  
> Skip to [Installation](#-installation) if you're already familiar.

### Part 1 — Neural Networks & Deep Learning

#### What is a neural network?

Think of a neural network like a chain of filters that progressively extract meaning from raw data.

Imagine you're trying to teach a child to recognise a dog in a photo:
1. First they notice **edges** — where light meets dark
2. Then they see **shapes** — ears, snout, paws
3. Then they recognise the **whole animal**

A neural network does exactly this, but with numbers:

```
Raw pixel values → Layer 1 (edges) → Layer 2 (shapes) → Layer 3 (parts) → Layer N (identity)
    [0..255]         [gradients]       [curves/lines]     [eyes/nose]       [Person A]
```

Each "layer" is a collection of **neurons** — mathematical functions that take a weighted sum of their inputs and pass it through an activation function (like ReLU: `max(0, x)`). The weights are **learned** from data, not programmed by hand.

#### Why neural networks for faces?

Faces are incredibly complex. Lighting, angle, age, glasses, and expressions all alter pixel values dramatically. Hand-crafted rules ("if pixel 42 > 180, it's a nose") fail almost immediately. Neural networks learn **invariant representations** — features that stay consistent regardless of these surface-level changes.

---

### Part 2 — Convolutional Neural Networks (CNNs)

#### Why CNNs specifically for images?

A plain neural network treats each pixel independently. For a 224×224 image, that's **150,528 inputs** — computationally brutal, and it ignores spatial relationships (the pixels forming an eye are *next to each other*, not scattered randomly).

A **CNN** exploits this spatial structure using **convolution**: a small filter (e.g., 3×3 pixels) slides across the entire image and looks for a specific pattern wherever it appears.

```
Image patch:          Filter (detects edges):    Output (high = edge found):
  10  10  10            -1  0  1                    0   0   0
  10  10 200            -1  0  1         →           0   0 190
  10  10 200            -1  0  1                    0   0 190
```

The network learns what filters to use. Early layers learn basic edges; deeper layers combine these into complex facial features.

```
Input Image
    │
    ▼
[Conv Layer 1]  ──► detects: edges, corners
    │
    ▼
[Conv Layer 2]  ──► detects: curves, textures
    │
    ▼
[Conv Layer 3]  ──► detects: eyes, nose, mouth
    │
    ▼
[Fully Connected] ──► combines all features
    │
    ▼
[Output]        ──► 512-dimensional face embedding vector
```

---

### Part 3 — This Project's Training Pipeline

This project uses **transfer learning** via the pre-trained `InsightFace buffalo_l` model. Here's what that means and how the full pipeline works:

#### What is transfer learning?

Training a face recognition model from scratch requires millions of labelled face images and weeks of GPU time. **Transfer learning** skips this: we download a model already trained on massive public datasets (like MS1MV3 with 5 million faces), then use it directly or fine-tune it on our specific data.

**Analogy:** You don't re-learn English from scratch to read a new book. You use the language skills you already have and apply them to new content.

#### The training pipeline in this project

```
Step 1: Upload reference images (2–10 photos per person)
           ↓
Step 2: Face Detection (InsightFace MTCNN-style detector)
         → finds bounding boxes around faces in each photo
           ↓
Step 3: Alignment
         → rotates/crops face to a standard 112×112 format
         → ensures eyes are always at the same position
           ↓
Step 4: Embedding Extraction (buffalo_l backbone)
         → runs the aligned face through the CNN
         → outputs a 512-dimensional float vector
           ↓
Step 5: Averaging
         → all embeddings for one person are averaged
         → produces one representative "identity vector"
           ↓
Step 6: Index Building (FAISS)
         → all identity vectors are stored in a FAISS index
         → optimised for cosine similarity search (IndexFlatIP)
           ↓
Done: Index saved to disk, ready for real-time recognition
```

#### Key hyperparameters (what they mean)

| Parameter | What it is | Default in this project |
|---|---|---|
| `RECOGNITION_THRESHOLD` | Cosine similarity score below which a face is called "Unknown" | `0.35` |
| `FACE_DETECTION_THRESHOLD` | Confidence score for the detector to report a face | `0.5` |
| `ATTENDANCE_COOLDOWN_SECONDS` | Minimum gap between two attendance marks for the same person | `60` |
| `FRAME_PROCESS_INTERVAL` | Process every Nth video frame (reduces CPU load) | configurable |

---

### Part 4 — Face Recognition: Detection → Embedding → Matching

#### Face detection vs. face recognition

These are different problems often confused:

| Task | Question answered | Output |
|---|---|---|
| **Face Detection** | "Is there a face in this image? Where?" | Bounding box coordinates |
| **Face Recognition** | "Whose face is this?" | A person's identity |

This project does **both** in sequence.

#### The full recognition pipeline

```
Video Frame (raw pixels)
        │
        ▼
  ┌─────────────┐
  │   DETECTOR  │  InsightFace's detection head
  │  (buffalo_l)│  → finds all faces in the frame
  └─────────────┘
        │  bounding box + landmarks (eyes, nose, mouth corners)
        ▼
  ┌─────────────┐
  │  ALIGNMENT  │  Affine transform
  │             │  → warps face to 112×112 canonical pose
  └─────────────┘
        │  normalised face crop
        ▼
  ┌─────────────┐
  │  EMBEDDING  │  CNN backbone (ResNet-style)
  │  EXTRACTION │  → outputs 512-float vector
  └─────────────┘
        │  query vector  q ∈ ℝ⁵¹²
        ▼
  ┌─────────────┐
  │   MATCHING  │  FAISS IndexFlatIP
  │  (FAISS)    │  → computes cosine similarity vs. all stored identities
  └─────────────┘
        │  top match + similarity score
        ▼
  score > threshold?
  ├─ YES → Mark attendance for matched person
  └─ NO  → Label as "Unknown"
```

#### What are face embeddings?

A face embedding is a **compressed numeric fingerprint** of a face.

The CNN maps each face to a point in a 512-dimensional space. The key property learned during training: **faces of the same person cluster together; faces of different people are far apart.**

```
                  ● ● (Alice: different photos)
                ●
                            ● ● (Bob: different lighting)
                          ●

         Distance between Alice cluster ≪ Distance between Alice & Bob
```

#### Similarity metrics

**Cosine similarity** measures the *angle* between two vectors (not their length), making it robust to brightness/scale variations:

```
cosine_similarity(A, B) = (A · B) / (|A| × |B|)

Range: -1 (opposite) to +1 (identical)
Typical same-person score: > 0.5
Typical different-person score: < 0.3
Threshold in this project: 0.35 (configurable via RECOGNITION_THRESHOLD)
```

FAISS `IndexFlatIP` computes inner products on L2-normalised vectors, which is equivalent to cosine similarity — and does it much faster than a naive Python loop.

#### Matching threshold — how the "match vs. no match" decision works

```
similarity = dot(query_embedding, stored_embedding)

if similarity > RECOGNITION_THRESHOLD:
    → "Recognised as Person X" ✅
else:
    → "Unknown" ❌
```

Setting the threshold too **high** → misses real matches (false negatives, legitimate users turned away).  
Setting it too **low** → wrong matches (false positives, wrong person's attendance marked).

The default `0.35` is conservative. In high-security settings, raise it to `0.5`+.

#### Known limitations

| Limitation | Why it happens | Mitigation |
|---|---|---|
| **Poor lighting** | Dark/blown-out images degrade embedding quality | Ensure adequate, consistent lighting |
| **Extreme head pose** | Profile faces align poorly to the frontal 112×112 template | Capture reference images at multiple angles |
| **Occlusion** | Masks, hats, hands covering the face reduce detector confidence | Use `FACE_DETECTION_THRESHOLD` to filter weak detections |
| **Identical twins** | Two people whose faces are biologically near-identical | Add secondary verification or train on many varied images |
| **Low resolution** | Faces smaller than ~40×40 pixels lose discriminative features | Ensure camera placement gives adequately sized face crops |

---

## 📦 Installation

### Prerequisites

| Tool | Minimum version | Check with |
|---|---|---|
| Python | 3.11 | `python --version` |
| Node.js | 20 | `node -v` |
| npm | 10 | `npm -v` |
| Git | any | `git --version` |

**Linux only** — OpenCV runtime libs:
```bash
sudo apt-get update && sudo apt-get install -y libglib2.0-0 libgl1
```

### 1. Clone the repository

```bash
git clone https://github.com/itsrishitacodeforspace/face-recognition-attendance.git
cd face-recognition-attendance
```

### 2. Backend setup

**Linux / macOS:**
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip setuptools wheel
cp .env.example .env          # edit values as needed
pip install -r requirements.txt
```

**Windows (PowerShell):**
```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip setuptools wheel
Copy-Item .env.example .env   # edit values as needed
pip install -r requirements.txt
```

### 3. Frontend setup

```bash
cd frontend
npm install
```

### 4. (Optional) Docker Compose — starts everything at once

```bash
docker compose up --build
```

---

## 🚀 Usage

### Start the backend API server

```bash
cd backend
source .venv/bin/activate     # Windows: .\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

API docs auto-generated at: **http://127.0.0.1:8000/docs**

### Start the frontend dashboard

```bash
cd frontend
npm run dev
```

Dashboard available at: **http://localhost:5173**

Default login:
- **Username:** `admin`
- **Password:** `admin123`

*(Override via `ADMIN_USERNAME` / `ADMIN_PASSWORD` in `backend/.env`)*

---

### How to add a new person and run recognition

```
1. Go to the Persons page in the dashboard
2. Click "Add Person" → fill in name/employee ID
3. Upload 3–10 clear, well-lit reference photos of the face
4. Navigate to the Training page → click "Train Model"
   Wait for the status to show "Training complete"
5. Navigate to Live Recognition → select webcam or upload a video
6. Press "Start" — matches are shown in real time and attendance is recorded
```

### Run via API directly

```bash
# 1. Add a person
curl -X POST http://localhost:8000/api/persons \
  -H "Authorization: Bearer <token>" \
  -F "name=Alice Smith" -F "employee_id=EMP001"

# 2. Upload a reference image
curl -X POST http://localhost:8000/api/persons/1/images \
  -H "Authorization: Bearer <token>" \
  -F "file=@alice_photo.jpg"

# 3. Trigger training
curl -X POST http://localhost:8000/api/train \
  -H "Authorization: Bearer <token>"

# 4. Check training status
curl http://localhost:8000/api/train/status \
  -H "Authorization: Bearer <token>"
```

### Run tests

```bash
cd backend
source .venv/bin/activate
pytest -q
```

---

## 🗂️ Project Structure

```
face-recognition-attendance/
├── backend/                        # Python / FastAPI application
│   ├── app/
│   │   ├── main.py                 # FastAPI app factory, CORS, lifespan hooks
│   │   ├── config.py               # Pydantic Settings — all env vars with defaults
│   │   ├── database.py             # Async SQLAlchemy engine and session factory
│   │   ├── api/
│   │   │   ├── auth.py             # JWT login, token refresh endpoints
│   │   │   ├── persons.py          # Person CRUD + image upload/delete
│   │   │   ├── training.py         # Train trigger, status, and log endpoints
│   │   │   ├── attendance.py       # Attendance list, today, export, heatmap, trends
│   │   │   ├── video.py            # Video source configuration endpoint
│   │   │   └── deps.py             # Shared FastAPI dependencies (auth, DB session)
│   │   ├── models/                 # SQLAlchemy ORM table definitions
│   │   ├── schemas/                # Pydantic request/response schemas
│   │   ├── services/
│   │   │   ├── face_recognition.py # Core: InsightFace + FAISS training & inference
│   │   │   ├── attendance_service.py # Cooldown logic, attendance creation
│   │   │   ├── analytics_service.py  # Heatmap and trend aggregation queries
│   │   │   └── video_ingestion.py  # Frame-reading from webcam / file / RTSP
│   │   ├── websocket/              # WebSocket handler for live recognition stream
│   │   └── utils/                  # Shared helpers (image preprocessing, etc.)
│   ├── tests/                      # pytest test suite
│   ├── requirements.txt            # Pinned Python dependencies
│   ├── .env.example                # Environment variable template
│   └── Dockerfile                  # Backend container image
│
├── frontend/                       # React + Vite + Tailwind dashboard
│   ├── src/
│   │   ├── App.jsx                 # Router setup, protected routes
│   │   ├── main.jsx                # React entry point
│   │   ├── pages/
│   │   │   ├── Login.jsx           # Login form with JWT storage
│   │   │   ├── Dashboard.jsx       # Overview stats cards
│   │   │   ├── PersonsPage.jsx     # Person CRUD with image gallery
│   │   │   ├── TrainingPage.jsx    # Train trigger, log viewer, status polling
│   │   │   ├── LiveRecognitionPage.jsx # WebSocket stream, bounding box overlay
│   │   │   ├── AttendancePage.jsx  # Paginated attendance table with CSV export
│   │   │   ├── HeatmapPage.jsx     # Attendance heatmap calendar view
│   │   │   └── TrendsPage.jsx      # Chart.js line charts for attendance trends
│   │   ├── components/             # Shared UI components (Navbar, cards, modals)
│   │   └── services/               # Axios API client wrappers
│   ├── package.json
│   ├── vite.config.js
│   └── tailwind.config.js
│
├── docker-compose.yml              # Orchestrates backend + frontend containers
├── .gitignore                      # Python, Node, ML model, dataset exclusions
├── CHANGELOG.md                    # Version history
├── CONTRIBUTING.md                 # Contribution guidelines
├── LICENSE                         # MIT License
└── README.md                       # This file
```

---

## 📊 Results

> ⚠️ *This section will be updated with benchmark results from your deployment.*

### Accuracy Metrics

| Metric | Value |
|---|---|
| Identification Accuracy | _to be measured_ |
| False Accept Rate (FAR) | _to be measured_ |
| False Reject Rate (FRR) | _to be measured_ |
| Average inference latency (CPU) | _to be measured_ |
| Average inference latency (GPU) | _to be measured_ |

### Sample Output

> _Add demo GIFs of the live recognition stream and dashboard screenshots here._

```
📸 Demo GIF placeholder — capture with OBS or ffmpeg:
   ffmpeg -f gdigrab -i desktop -t 15 demo.gif
```

---

## ⚙️ Environment Variables

Full reference for `backend/.env`:

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | SQLAlchemy async DB URL | `sqlite+aiosqlite:///./attendance.db` |
| `SECRET_KEY` | JWT signing secret | _generate with `openssl rand -hex 32`_ |
| `RECOGNITION_THRESHOLD` | Cosine similarity threshold for identity match | `0.35` |
| `FACE_DETECTION_THRESHOLD` | Minimum detector confidence to accept a face | `0.5` |
| `ATTENDANCE_COOLDOWN_SECONDS` | Minimum seconds between attendance marks per person | `60` |
| `FRAME_PROCESS_INTERVAL` | Process every Nth frame from video stream | `5` |
| `INSIGHTFACE_MODEL` | InsightFace model pack name | `buffalo_l` |
| `VIDEO_SOURCE_TYPE` | `webcam`, `file`, or `rtsp` | `webcam` |
| `VIDEO_SOURCE_PATH` | Path/URL for `file` or `rtsp` source | — |
| `CUDA_ENABLED` | Enable CUDA acceleration | `false` |
| `GPU_STRICT_MODE` | Fail hard if CUDA unavailable | `false` |
| `CORS_ORIGINS` | Comma-separated allowed frontend origins | `http://localhost:5173` |
| `ADMIN_USERNAME` | Bootstrap admin account username | `admin` |
| `ADMIN_PASSWORD` | Bootstrap admin account password | `admin123` |

---

## 📡 API Reference

Interactive docs: **http://localhost:8000/docs** (Swagger UI)

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/login` | Obtain access + refresh tokens |
| `POST` | `/api/auth/refresh` | Exchange refresh token for new access token |

### Persons

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/persons` | Create a new person |
| `GET` | `/api/persons` | List all persons |
| `GET` | `/api/persons/{id}` | Get person by ID |
| `PUT` | `/api/persons/{id}` | Update person details |
| `DELETE` | `/api/persons/{id}` | Delete person and all their images |
| `POST` | `/api/persons/{id}/images` | Upload a reference image |
| `GET` | `/api/persons/{id}/images` | List reference images |
| `DELETE` | `/api/images/{id}` | Delete a specific reference image |

### Training

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/train` | Trigger model training (async) |
| `GET` | `/api/train/status` | Get current training status |
| `GET` | `/api/train/logs` | Stream training log output |

### Attendance

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/attendance` | List all records (paginated) |
| `GET` | `/api/attendance/today` | Today's attendance records |
| `GET` | `/api/attendance/export` | Download CSV export |
| `GET` | `/api/attendance/heatmap` | Heatmap aggregated data |
| `GET` | `/api/attendance/trends` | Time-series trend data |
| `DELETE` | `/api/attendance/{id}` | Delete a specific record |

### WebSocket

| Endpoint | Description |
|---|---|
| `WS /ws/process` | Bidirectional stream: send frames, receive recognition events + bounding boxes |

---

## 📚 References & Key Papers

| Paper | Description | Link |
|---|---|---|
| **ArcFace** (Deng et al., 2019) | Training loss for face recognition embeddings — used by InsightFace | [arXiv:1801.07698](https://arxiv.org/abs/1801.07698) |
| **RetinaFace** (Deng et al., 2020) | Face detection with landmark regression | [arXiv:1905.00641](https://arxiv.org/abs/1905.00641) |
| **InsightFace** (Guo et al.) | Production face analysis library (detection + recognition) | [GitHub](https://github.com/deepinsight/insightface) |
| **FAISS** (Johnson et al., 2019) | Efficient similarity search for dense vectors | [arXiv:1702.08734](https://arxiv.org/abs/1702.08734) |
| **FaceNet** (Schroff et al., 2015) | Pioneered embedding-based face recognition | [arXiv:1503.03832](https://arxiv.org/abs/1503.03832) |
| **Deep Residual Networks** (He et al., 2016) | ResNet backbone architecture used by buffalo_l | [arXiv:1512.03385](https://arxiv.org/abs/1512.03385) |

---

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to open issues, submit pull requests, and follow the code style.

---

## 📄 License

This project is licensed under the **MIT License** — see [LICENSE](LICENSE) for full text.

---

<div align="center">
Built with ❤️ using FastAPI, InsightFace, FAISS, and React.
</div>
