const { contextBridge, ipcMain } = require('electron');

// Expose minimal API to renderer (not used yet, but good practice)
contextBridge.exposeInMainWorld('electron', {
  ipcRenderer: require('electron').ipcRenderer,
});
