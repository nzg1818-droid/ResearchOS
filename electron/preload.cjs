const { contextBridge, ipcRenderer } = require("electron");
contextBridge.exposeInMainWorld("desktop", {
  config: () => ipcRenderer.invoke("config"),
  pickPDFs: (folder = false) => ipcRenderer.invoke("pick-pdfs", folder),
  openExternal: (url) => ipcRenderer.invoke("open-external", url),
  fullscreen: (enabled) => ipcRenderer.invoke("fullscreen", enabled),
  choosePath: (kind) => ipcRenderer.invoke("choose-path", kind),
  useDataRoot: (path) => ipcRenderer.invoke("use-data-root", path),
});
