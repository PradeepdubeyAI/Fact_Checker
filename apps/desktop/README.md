# ClaimAI Desktop Application

A standalone desktop application for AI-powered fact-checking built with Electron and Python.

## 🚀 Features

- **Full Text Analysis**: Paste text, auto-detect language, translate, extract claims, and verify
- **Single Fact Check**: Quick verification of individual facts
- **Video Analysis**: Process video files for fact-checking (coming soon)
- **Native Desktop App**: Windows, macOS, and Linux support
- **Offline-capable**: Runs locally with your own API keys
- **Modern UI**: Dark theme with smooth animations

## 📋 Prerequisites

- **Node.js** 18+ ([Download](https://nodejs.org/))
- **Python** 3.11+ ([Download](https://www.python.org/))
- **API Keys**:
  - OpenAI API key ([Get one](https://platform.openai.com/api-keys))
  - Tavily API key ([Get one](https://tavily.com/))

## 🛠️ Installation & Setup

### Step 1: Install Python Dependencies

```bash
cd apps/desktop/python-backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### Step 2: Install Electron Dependencies

```bash
cd ../electron
npm install
```

### Step 3: Configure API Keys

On first launch, click the settings icon (⚙️) and enter your API keys:
- OpenAI API Key
- Tavily API Key

## 🎮 Running the App

### Development Mode

From the `apps/desktop/electron` directory:

```bash
npm run dev
```

This will:
1. Start the Python backend server on port 8765
2. Launch the Electron app in development mode with DevTools

### Production Build

Build standalone executables:

```bash
# Windows
npm run build:win

# macOS
npm run build:mac

# Linux
npm run build:linux

# All platforms
npm run build
```

The built applications will be in `apps/desktop/electron/dist/`

## 📁 Project Structure

```
apps/desktop/
├── electron/                 # Electron app (frontend)
│   ├── build/               # Compiled frontend assets
│   │   ├── index.html       # Main HTML
│   │   ├── styles.css       # Styling
│   │   └── app.js           # Frontend logic
│   ├── main.js              # Electron main process
│   ├── preload.js           # Preload script (IPC bridge)
│   └── package.json         # Node dependencies
│
└── python-backend/          # Python FastAPI server
    ├── server.py            # REST API server
    └── requirements.txt     # Python dependencies
```

## 🔧 How It Works

1. **Electron Main Process** (`main.js`):
   - Spawns Python backend as subprocess
   - Creates native window
   - Manages IPC communication

2. **Python Backend** (`server.py`):
   - Wraps existing LangGraph agents
   - Exposes REST API endpoints
   - Runs on `localhost:8765`

3. **Frontend** (`build/` folder):
   - HTML/CSS/JavaScript UI
   - Communicates with Python via Electron IPC
   - Similar interface to Streamlit app

## 🎯 Usage

### Full Text Analysis
1. Switch to "📝 Full Text Analysis" tab
2. Paste your text
3. Click "Analyze Text" - auto-detects language and translates
4. Review translation (if needed)
5. Click "Extract Claims" - AI extracts factual claims
6. Select which claims to verify
7. Click "Verify Selected Claims"
8. Review results with verdicts and evidence

### Single Fact Check
1. Switch to "🎯 Single Fact Check" tab
2. Enter a single fact
3. Click "Verify Fact"
4. Get instant verdict with explanation and sources

## 📦 Building for Distribution

### Windows Installer
```bash
npm run build:win
```
Creates:
- `ClaimAI-Setup-1.0.0.exe` (NSIS installer)
- `ClaimAI-1.0.0.exe` (Portable)

### macOS App
```bash
npm run build:mac
```
Creates:
- `ClaimAI-1.0.0.dmg` (Disk image)
- `ClaimAI-1.0.0-mac.zip` (ZIP archive)

### Linux Package
```bash
npm run build:linux
```
Creates:
- `ClaimAI-1.0.0.AppImage` (Universal Linux app)
- `claimeai_1.0.0_amd64.deb` (Debian/Ubuntu)

## 🔐 Security Notes

- API keys are stored securely using `electron-store`
- Python backend only accepts local connections (`127.0.0.1`)
- No data is sent to external servers except AI APIs

## 🐛 Troubleshooting

### Backend won't start
- Check Python is in PATH: `python --version`
- Verify virtual environment is activated
- Install dependencies: `pip install -r requirements.txt`

### Electron app won't launch
- Check Node.js version: `node --version` (need 18+)
- Reinstall dependencies: `rm -rf node_modules && npm install`

### Build fails
- Install electron-builder globally: `npm install -g electron-builder`
- Check disk space (builds need ~500MB)

## 📝 Development Notes

### Adding New Features
1. Add REST endpoint in `python-backend/server.py`
2. Add IPC handler in `electron/preload.js`
3. Add UI in `electron/build/` files
4. Test in dev mode: `npm run dev`

### Debugging
- Backend logs: Check terminal where `npm run dev` was run
- Frontend logs: Open DevTools (automatically opened in dev mode)
- Python errors: Check backend terminal output

## 🎨 Customization

### Change App Icon
Replace icons in `electron/assets/`:
- `icon.ico` (Windows)
- `icon.icns` (macOS)
- `icon.png` (Linux)

### Modify UI Theme
Edit colors in `electron/build/styles.css`:
```css
:root {
    --bg-primary: #0f172a;
    --accent: #3b82f6;
    /* ... other variables */
}
```

## 🚀 Performance Tips

- The Python backend stays running for faster responses
- Claims are verified in parallel for speed
- Translation caching reduces API calls

## 📄 License

Same as parent project (see LICENSE file in root)

## 🤝 Contributing

To report issues or suggest features, please create an issue in the main repository.

## 🙋 Need Help?

- Check existing error messages in DevTools Console
- Review Python backend logs in terminal
- Ensure API keys are configured correctly
- Verify all dependencies are installed
