// preload.js
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
    restartApp: () => ipcRenderer.send('restart_app'),
    onUpdateStatus: (callback) => ipcRenderer.on('update-status', (_event, value) => callback(value)),
    onUpdateAvailable: (callback) => ipcRenderer.on('update-available', (_event, version) => callback(version)),
    onUpdateDownloaded: (callback) => ipcRenderer.on('update-downloaded', (_event) => callback()),
    onUpdateProgress: (callback) => ipcRenderer.on('update-progress', (_event, percent) => callback(percent)),
    downloadUpdate: () => ipcRenderer.send('download_update'),
    reloadApp: () => ipcRenderer.send('reload_app'), 
    quitApp: () => ipcRenderer.send('quit_app'),    
    showLogoutDialog: () => ipcRenderer.send('show-logout-dialog'),
});