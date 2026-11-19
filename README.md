# 🏋️‍♂️ AI Real-time Gym Coach (AI_GYM_COACH)

An intelligent, real-time computer vision gym workout coach and form tracker powered by **MediaPipe**, **Streamlit**, and **Groq LLM Voice Coaching**.

---

## ⚡ Features

- **Real-Time Computer Vision Pose Tracking**: High-accuracy landmark detection powered by MediaPipe to track posture, joint angles, and movement form live through your webcam.
- **Supported Exercises**:
  - 🦵 **Squats** (Knee angle, depth detection, hip alignment)
  - 💪 **Push-ups** (Elbow angle, body alignment, chest depth)
  - 🏋️ **Biceps Curls** (Elbow flexion, upper-arm stability)
  - 🏋️‍♂️ **Shoulder Press** (Arm extension, overhead lockout, back arch)
  - 🏃 **Lunges** (Front knee angle, posture balance)
- **Proactive AI Voice Coaching**: Real-time auditory guidance and motivational feedback powered by Groq and Edge-TTS. No robotic delays.
- **Live Workout HUD**: Single source of truth dashboard showing Total Reps, Current Set Reps, and Completed Sets.
- **Workout History & Analytics**:
  - Detailed workout sessions with exact timestamps, sets, reps, and durations.
  - Daily aggregated workout volume breakdown.
  - Lifetime statistics tracking total sessions, lifetime reps, and active workout time.
- **Fully Responsive Modern UI**: Clean dark-mode design optimized for both desktop and mobile devices.

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10+ (or [uv](https://github.com/astral-sh/uv))
- Webcam for real-time video feed

### 2. Installation
Clone the repository:
```bash
git clone https://github.com/Aniketgupta4/AI_GYM_COACH.git
cd AI_GYM_COACH
```

Create and activate a virtual environment:
```bash
python -m venv .venv

# Windows:
.venv\Scripts\activate

# macOS / Linux:
source .venv/bin/activate
```

Install dependencies:
```bash
pip install -r requirements.txt
```

### 3. Environment Configuration
Create a `.env` file from `.env.example`:
```bash
cp .env.example .env
```
Add your free Groq API Key inside `.env`:
```env
GROQ_API_KEY=gsk_your_groq_api_key_here
```

### 4. Run the Application
```bash
streamlit run main.py
```
*(Or with uv: `uv run streamlit run main.py`)*

Open your browser at `http://localhost:8501`.

---

## 📂 Project Structure

```
AI_COACH/
├── core/                       # Base exercise classes & geometry helpers
├── detectors/                  # Exercise-specific angle & repetition detectors
│   ├── squat.py
│   ├── pushup.py
│   ├── biceps_curl.py
│   ├── shoulder_press.py
│   └── lunges.py
├── services/
│   ├── auth/                   # User session & profile management
│   ├── coaching/               # Groq LLM coach, TTS & audio streaming pipeline
│   ├── persistence/            # SQLite repository for sessions & history
│   ├── tracking/               # Real-time metrics synchronization & saving
│   ├── ui/                     # CSS injectors & responsive styling
│   └── vision/                 # WebRTC video frame processor
├── static/                     # Custom fonts & stylesheet (AdobeClean, style.css)
├── .env.example                # Sample environment template
├── requirements.txt            # Python dependencies
└── main.py                     # Streamlit application entry point
```

---

## 🛡️ License
MIT License. Free to use and build upon!
