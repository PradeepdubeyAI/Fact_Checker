const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const axios = require('axios');
const Store = require('electron-store');

const store = new Store();
let mainWindow;
let pythonProcess;
const PYTHON_PORT = 8765;

// Check if Python backend is running
async function checkBackendHealth(retries = 10) {
  for (let i = 0; i < retries; i++) {
    try {
      const response = await axios.get(`http://127.0.0.1:${PYTHON_PORT}/health`, {
        timeout: 2000
      });
      if (response.data && response.data.status === 'ok') {
        console.log('✅ Python backend is ready');
        return true;
      }
    } catch (error) {
      console.log(`⏳ Waiting for backend... (${i + 1}/${retries})`);
      if (i === retries - 1) {
        console.error('❌ Backend health check failed:', error.message);
      }
      await new Promise(resolve => setTimeout(resolve, 2000));
    }
  }
  return false;
}

// Start Python backend server
function startPythonBackend() {
  return new Promise((resolve, reject) => {
    // Determine if we're running from packaged app or development
    const isDev = !app.isPackaged;
    
    let pythonPath, scriptPath, backendDir;
    
    if (isDev) {
      // Development mode - use venv
      backendDir = path.join(__dirname, '..', 'python-backend');
      pythonPath = path.join(backendDir, 'venv', 'Scripts', 'python.exe');
      scriptPath = path.join(backendDir, 'server.py');
    } else {
      // Production mode - python-backend is in resources/python-backend
      backendDir = path.join(process.resourcesPath, 'python-backend');
      pythonPath = path.join(backendDir, 'venv', 'Scripts', 'python.exe');
      scriptPath = path.join(backendDir, 'server.py');
      
      // Fallback: try system Python if venv doesn't exist
      if (!fs.existsSync(pythonPath)) {
        pythonPath = 'python';
        console.log('⚠️ Using system Python (venv not found in packaged app)');
      }
    }

    console.log(`🐍 Starting Python backend: ${pythonPath} ${scriptPath}`);
    console.log(`📁 Backend directory: ${backendDir}`);
    
    pythonProcess = spawn(pythonPath, [scriptPath], {
      cwd: backendDir,
      env: {
        ...process.env,
        PYTHONUNBUFFERED: '1',
        PORT: PYTHON_PORT.toString()
      }
    });

    pythonProcess.stdout.on('data', (data) => {
      console.log(`[Python] ${data.toString()}`);
      if (data.toString().includes('Uvicorn running')) {
        resolve();
      }
    });

    pythonProcess.stderr.on('data', (data) => {
      console.error(`[Python Error] ${data.toString()}`);
    });

    pythonProcess.on('close', (code) => {
      console.log(`Python process exited with code ${code}`);
    });

    // Timeout fallback
    setTimeout(() => resolve(), 5000);
  });
}

// Create the main application window
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1200,
    minHeight: 700,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
      enableRemoteModule: false
    },
    icon: path.join(__dirname, 'assets', 'icon.png'),
    backgroundColor: '#0f172a',
    show: false
  });

  // Load the frontend
  mainWindow.loadFile(path.join(__dirname, 'build', 'index.html'));

  // Show window when ready
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  // Open DevTools in development
  if (process.argv.includes('--dev')) {
    mainWindow.webContents.openDevTools();
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// IPC Handlers
ipcMain.handle('get-api-keys', async () => {
  return {
    openai: store.get('OPENAI_API_KEY', ''),
    tavily: store.get('TAVILY_API_KEY', '')
  };
});

ipcMain.handle('set-api-keys', async (event, keys) => {
  if (keys.openai) store.set('OPENAI_API_KEY', keys.openai);
  if (keys.tavily) store.set('TAVILY_API_KEY', keys.tavily);
  
  // Update Python backend environment
  try {
    await axios.post(`http://127.0.0.1:${PYTHON_PORT}/api/config`, {
      openai_api_key: keys.openai,
      tavily_api_key: keys.tavily
    });
    return { success: true };
  } catch (error) {
    console.error('Failed to update backend config:', error);
    return { success: false, error: error.message };
  }
});

ipcMain.handle('open-file-dialog', async (event, options) => {
  const result = await dialog.showOpenDialog(mainWindow, options);
  return result;
});

ipcMain.handle('backend-request', async (event, { endpoint, method, data }) => {
  try {
    const config = {
      method: method || 'POST',
      url: `http://127.0.0.1:${PYTHON_PORT}${endpoint}`,
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': store.get('OPENAI_API_KEY', ''),
        'X-Tavily-Key': store.get('TAVILY_API_KEY', '')
      }
    };
    
    if (data) {
      config.data = data;
    }
    
    const response = await axios(config);
    return { success: true, data: response.data };
  } catch (error) {
    console.error('Backend request failed:', error);
    return { 
      success: false, 
      error: error.response?.data?.detail || error.message 
    };
  }
});

// App lifecycle
app.whenReady().then(async () => {
  console.log('🚀 Starting ClaimAI Desktop...');
  
  // Start Python backend
  await startPythonBackend();
  
  // Wait for backend to be ready (don't quit if it fails, just warn)
  const backendReady = await checkBackendHealth();
  
  if (!backendReady) {
    console.warn('⚠️  Backend not responding yet. Window will open anyway.');
    console.warn('📋 Make sure Python backend is running on port 8765');
  }
  
  // Create window regardless
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  // Kill Python process
  if (pythonProcess) {
    console.log('🛑 Stopping Python backend...');
    pythonProcess.kill();
  }
});

// Handle uncaught exceptions
process.on('uncaughtException', (error) => {
  console.error('Uncaught Exception:', error);
  dialog.showErrorBox('Application Error', error.message);
});
