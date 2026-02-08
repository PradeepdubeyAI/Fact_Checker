# ClaimAI Desktop - Quick Start Guide

## 🎯 Choose Your Method

### Method 1: One-Click Start (Easiest) ⚡

**Windows:**
1. Double-click `START.bat`
2. Wait for the app to open
3. Done! 🎉

**macOS/Linux:**
```bash
chmod +x START.sh
./START.sh
```

### Method 2: Manual Start (More Control) 🛠️

**Step 1: Setup (First Time Only)**

```bash
# Install Python dependencies
cd apps/desktop/python-backend
python -m venv venv

# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt

# Install Electron dependencies
cd ../electron
npm install
```

**Step 2: Run App**

**Terminal 1 - Python Backend:**
```bash
cd apps/desktop/python-backend
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

python server.py
```

**Terminal 2 - Electron App:**
```bash
cd apps/desktop/electron
npm start
```

## 🔑 First Launch Setup

1. Click the ⚙️ (Settings) icon in the top-right
2. Enter your API keys:
   - **OpenAI API Key**: Get from https://platform.openai.com/api-keys
   - **Tavily API Key**: Get from https://tavily.com/
3. Click "Save"

## 📦 Building Installer (Optional)

Create a standalone installer for distribution:

```bash
cd apps/desktop/electron

# Windows Installer
npm run build:win

# macOS App
npm run build:mac

# Linux Package
npm run build:linux
```

Find the installer in `apps/desktop/electron/dist/`

## ❓ Common Issues

### "Python not found"
Install Python 3.11+ from https://python.org/

### "npm not found"
Install Node.js 18+ from https://nodejs.org/

### Backend won't connect
- Check if port 8765 is available
- Restart the app
- Check firewall settings

### Blank screen on launch
- Open DevTools (Ctrl+Shift+I)
- Check for errors in Console
- Verify API keys are configured

## 🎮 How to Use

### Full Text Analysis
1. Click "📝 Full Text Analysis" tab
2. Paste your text
3. Click "Analyze Text"
4. Select claims to verify
5. Click "Verify Selected Claims"
6. Review results!

### Single Fact
1. Click "🎯 Single Fact Check" tab
2. Type a fact
3. Click "Verify Fact"
4. See verdict instantly!

## 🚀 Next Steps

- Explore the full README.md for detailed documentation
- Customize the UI in `electron/build/` folder
- Add new features in `python-backend/server.py`

Enjoy ClaimAI Desktop! 🎉
