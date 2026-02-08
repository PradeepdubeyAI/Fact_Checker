# How to Share ClaimAI with Your Friends

## Option 1: Share Installer (RECOMMENDED - If build succeeds)

Once the build completes, you'll find the installer in:
```
apps/desktop/electron/dist/ClaimAI Setup 1.0.0.exe
```

**To share:**
1. Upload `ClaimAI Setup 1.0.0.exe` to Google Drive / OneDrive / Dropbox
2. Share the link with your friends
3. They just double-click to install - that's it!

**What they need:**
- Nothing! Python is bundled inside the installer
- They will need their own API keys (or you can share yours)

---

## Option 2: Share Folder (If installer build fails)

**What to share:**
1. Zip these two folders:
   - `apps/desktop/electron/`
   - `apps/desktop/python-backend/`

2. Share the zip file

**Setup steps for your friends:**

### Step 1: Install Prerequisites
- **Python 3.11+**: Download from python.org
- **Node.js**: Download from nodejs.org

### Step 2: Setup Python Backend
```powershell
cd python-backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### Step 3: Add API Keys
Edit `python-backend/config.ini` and add:
```ini
[API_KEYS]
OPENAI_API_KEY=sk-your-key-here
TAVILY_API_KEY=tvly-your-key-here
```

### Step 4: Setup Electron App
```powershell
cd electron
npm install
```

### Step 5: Run the App
```powershell
npm start
```

---

## API Keys

Your friends need OpenAI and Tavily API keys. Options:

1. **Share your keys** (in config.ini) - easiest but costs you money
2. **They get their own keys**:
   - OpenAI: https://platform.openai.com/api-keys
   - Tavily: https://tavily.com/

---

## Troubleshooting

**"Python backend failed to start"**
- Make sure Python 3.11+ is installed
- Run `pip install -r requirements.txt` again

**"Cannot find module"**
- Delete `node_modules` folder
- Run `npm install` again

**"Port 8765 already in use"**
- Close any other Python processes
- Or restart your computer
