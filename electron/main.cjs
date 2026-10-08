const { app, BrowserWindow, ipcMain, dialog, shell } = require("electron");
const { spawn } = require("node:child_process");
const { randomBytes } = require("node:crypto");
const path = require("node:path");
const net = require("node:net");
const fs = require("node:fs");
let backend;
const token = randomBytes(32).toString("hex");
let base;
if (!app.requestSingleInstanceLock()) app.quit();
else
  app
    .whenReady()
    .then(async () => {
      const port = await new Promise((resolve, reject) => {
        const server = net.createServer();
        server.on("error", reject);
        server.listen(0, "127.0.0.1", () => {
          const port = server.address().port;
          server.close(() => resolve(port));
        });
      });
      base = `http://127.0.0.1:${port}`;
      const preferencesPath = path.join(
        app.getPath("userData"),
        "storage.json",
      );
      let preferences = {};
      try {
        preferences = JSON.parse(fs.readFileSync(preferencesPath, "utf8"));
      } catch {}
      const data =
        process.env.RESEARCHOS_DATA_DIR ||
        preferences.dataRoot ||
        path.join(app.getPath("userData"), "library");
      fs.mkdirSync(data, { recursive: true });
      const executable = app.isPackaged
        ? path.join(process.resourcesPath, "backend", "researchos-backend.exe")
        : path.join(__dirname, "..", ".venv", "Scripts", "python.exe");
      const args = app.isPackaged
        ? []
        : [path.join(__dirname, "..", "backend", "run.py")];
      const log = fs.openSync(path.join(data, "sidecar.log"), "a");
      backend = spawn(executable, args, {
        windowsHide: true,
        stdio: ["ignore", log, log],
        env: {
          ...process.env,
          RESEARCHOS_PORT: String(port),
          RESEARCHOS_TOKEN: token,
          RESEARCHOS_DATA_DIR: data,
        },
      });
      let failure;
      backend.on("error", (e) => {
        failure = e.message;
      });
      backend.on("exit", (code) => {
        failure = `Backend exited (${code}). See ${path.join(data, "sidecar.log")}`;
      });
      let ready = false;
      for (let i = 0; i < 120; i++) {
        if (failure) throw new Error(failure);
        try {
          const r = await fetch(base + "/health", {
            headers: { "X-ResearchOS-Token": token },
          });
          if (r.ok) {
            ready = true;
            break;
          }
        } catch {}
        await new Promise((r) => setTimeout(r, 500));
      }
      if (!ready)
        throw new Error(
          "Backend startup timed out. See sidecar.log in the library folder.",
        );
      ipcMain.handle("config", () => ({ base, token }));
      ipcMain.handle("choose-path", async (_, kind) => {
        if (kind === "save-backup")
          return (
            await dialog.showSaveDialog({
              defaultPath: "ResearchOS-backup.zip",
              filters: [{ name: "ResearchOS backup", extensions: ["zip"] }],
            })
          ).filePath;
        if (kind === "open-backup")
          return (
            await dialog.showOpenDialog({
              properties: ["openFile"],
              filters: [{ name: "ResearchOS backup", extensions: ["zip"] }],
            })
          ).filePaths[0];
        throw new Error("Unknown file picker");
      });
      ipcMain.handle("use-data-root", async (_, directory) => {
        if (
          typeof directory !== "string" ||
          !path.isAbsolute(directory) ||
          !fs.existsSync(path.join(directory, "researchos.db"))
        )
          throw new Error("Choose a restored ResearchOS data folder");
        fs.writeFileSync(
          preferencesPath,
          JSON.stringify({ dataRoot: path.resolve(directory) }),
        );
        delete process.env.RESEARCHOS_DATA_DIR;
        app.relaunch();
        app.quit();
      });
      ipcMain.handle(
        "pick-pdfs",
        async (_, folder) =>
          (
            await dialog.showOpenDialog({
              properties: folder
                ? ["openDirectory"]
                : ["openFile", "multiSelections"],
              filters: [{ name: "PDF", extensions: ["pdf"] }],
            })
          ).filePaths,
      );
      ipcMain.handle("open-external", async (_, value) => {
        const url = new URL(value);
        if (
          !["https:", "http:"].includes(url.protocol) ||
          url.username ||
          url.password
        )
          throw new Error("Only HTTP(S) literature links are supported");
        await shell.openExternal(url.href);
      });
      const win = new BrowserWindow({
        width: 1440,
        height: 960,
        minWidth: 1000,
        minHeight: 720,
        backgroundColor: "#f5f7fa",
        webPreferences: {
          preload: path.join(__dirname, "preload.cjs"),
          contextIsolation: true,
          nodeIntegration: false,
          sandbox: true,
        },
      });
      win.webContents.setWindowOpenHandler(() => ({ action: "deny" }));
      ipcMain.handle("fullscreen", (_, enabled) => {
        win.setFullScreen(enabled === true);
        return win.isFullScreen();
      });
      win.webContents.on("before-input-event", (_, input) => {
        if (input.key === "Escape" && win.isFullScreen())
          win.setFullScreen(false);
      });
      win.webContents.on("will-navigate", (e) => e.preventDefault());
      if (process.env.RESEARCHOS_DEV_URL && !app.isPackaged)
        await win.loadURL(process.env.RESEARCHOS_DEV_URL);
      else await win.loadFile(path.join(__dirname, "..", "dist", "index.html"));
    })
    .catch((e) => {
      dialog.showErrorBox("ResearchOS could not start", e.message);
      app.quit();
    });
app.on("window-all-closed", () => app.quit());
app.on("before-quit", () => {
  if (backend) backend.kill();
});
