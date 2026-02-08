const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods to the renderer process
contextBridge.exposeInMainWorld('electronAPI', {
  // API Key management
  getApiKeys: () => ipcRenderer.invoke('get-api-keys'),
  setApiKeys: (keys) => ipcRenderer.invoke('set-api-keys', keys),
  
  // File dialog
  openFileDialog: (options) => ipcRenderer.invoke('open-file-dialog', options),
  
  // Backend communication
  backendRequest: (endpoint, method, data) => 
    ipcRenderer.invoke('backend-request', { endpoint, method, data }),
  
  // Helper methods for specific operations
  checkHealth: () => 
    ipcRenderer.invoke('backend-request', { endpoint: '/health', method: 'GET' }),
  
  detectLanguage: (text) =>
    ipcRenderer.invoke('backend-request', { 
      endpoint: '/api/detect-language', 
      method: 'POST', 
      data: { text } 
    }),
  
  translateText: (text) =>
    ipcRenderer.invoke('backend-request', { 
      endpoint: '/api/translate', 
      method: 'POST', 
      data: { text } 
    }),
  
  extractClaims: (text, translation = null) =>
    ipcRenderer.invoke('backend-request', { 
      endpoint: '/api/extract-claims', 
      method: 'POST', 
      data: { text, translation } 
    }),
  
  verifyClaims: (claims) =>
    ipcRenderer.invoke('backend-request', { 
      endpoint: '/api/verify-claims', 
      method: 'POST', 
      data: { claims } 
    }),
  
  processVideo: (videoPath) =>
    ipcRenderer.invoke('backend-request', { 
      endpoint: '/api/process-video', 
      method: 'POST', 
      data: { video_path: videoPath } 
    }),
  
  verifySingleFact: (fact) =>
    ipcRenderer.invoke('backend-request', { 
      endpoint: '/api/verify-single', 
      method: 'POST', 
      data: { fact } 
    })
});

console.log('✅ Preload script loaded');
