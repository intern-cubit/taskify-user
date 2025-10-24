const { app, BrowserWindow, dialog, ipcMain, session } = require("electron"); // Import session for clearing data
const path = require("path");
const { spawn } = require("child_process");
const fs = require("fs");
const http = require("http");
const { autoUpdater } = require("electron-updater");
const log = require("electron-log");
const { exec } = require("child_process");

function killPort(port) {
    return new Promise((resolve, reject) => {
        console.log(`[KILLPORT] Attempting to kill process on port ${port}...`);
        const command = `for /f "tokens=5" %a in ('netstat -aon ^| find ":${port}" ^| find "LISTENING"') do taskkill /F /PID %a`;

        exec(command, (err, stdout, stderr) => {
            if (err) {
                if (
                    stderr.includes("No process found") ||
                    stderr.includes("not found")
                ) {
                    console.log(
                        `[KILLPORT] No process found on port ${port}, proceeding.`
                    );
                    resolve();
                } else {
                    console.error(
                        `[KILLPORT] Error killing port ${port}: ${stderr}`
                    );
                    resolve();
                }
            } else {
                console.log(`[KILLPORT] Port ${port} cleared: ${stdout}`);
                resolve();
            }
        });
    });
}

let backendProcess;
let mainWindow = null;
const BACKEND_PORT = 8000;
const BACKEND_HEALTH_URL = `http://localhost:${BACKEND_PORT}/health`;
const BACKEND_SHUTDOWN_URL = `http://localhost:${BACKEND_PORT}/shutdown`;

log.transports.file.level = "info";
autoUpdater.logger = log;
autoUpdater.autoDownload = true;

autoUpdater.on("checking-for-update", () => {
    log.info("Checking for update...");
    if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send("update-status", "Checking for update...");
    }
});

autoUpdater.on("update-available", (info) => {
    log.info(`Update available: v${info.version}`);
    if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send(
            "update-status",
            `Update available: v${info.version}`
        );
        mainWindow.webContents.send("update-available", info.version);
    }
});

autoUpdater.on("update-not-available", () => {
    log.info("Update not available.");
    if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send(
            "update-status",
            "No new update available."
        );
    }
});

autoUpdater.on("download-progress", (progressObj) => {
    let log_message = `Download speed: ${progressObj.bytesPerSecond} B/s`;
    log_message += ` - Downloaded ${progressObj.percent.toFixed(2)}%`;
    log_message += ` (${progressObj.transferred} / ${progressObj.total} bytes)`;
    log.info(log_message);
    if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send("update-progress", progressObj.percent);
    }
});

autoUpdater.on("update-downloaded", (info) => {
    log.info("Update downloaded.");
    if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send(
            "update-status",
            `Update downloaded: v${info.version}. Click 'Restart & Install' to apply.`
        );
        mainWindow.webContents.send("update-downloaded");
    }
});

autoUpdater.on("error", (err) => {
    log.error("Error in auto-updater:", err);
    if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send(
            "update-status",
            `Error during update: ${err.message}`
        );
    }
});

ipcMain.on("restart_app", () => {
    log.info("Restarting app to install update...");
    autoUpdater.quitAndInstall();
});

ipcMain.on("reload_app", () => {
    log.info("Received 'reload_app' signal. Reloading current window.");
    if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.reload(); 
    }
});

ipcMain.on("quit_app", async (event) => {
    log.info("Received 'quit_app' signal. Showing quit confirmation dialog.");
    const options = {
        type: "question",
        buttons: ["OK", "Cancel"],
        defaultId: 0, 
        title: "WA BOMB", 
        message: "Are you sure you want to quit the application?",
        icon: path.join(__dirname, "build", "icon.ico"),
    };

    const response = await dialog.showMessageBox(mainWindow, options);

    if (response.response === 0) {
        app.quit();
    }
});

ipcMain.on("show-logout-dialog", async (event) => {
    log.info(
        "Received 'show-logout-dialog' signal. Showing logout confirmation dialog."
    );
    const options = {
        type: "info", 
        buttons: ["OK"],
        defaultId: 0,
        title: "WA BOMB",
        message: "You have been logged out. The application will now restart.",
        icon: path.join(__dirname, "build", "icon.ico"),
    };

    await dialog.showMessageBox(mainWindow, options);

    log.info("Initiating logout and relaunch.");
    try {
        if (session && session.defaultSession) {
            await session.defaultSession.clearStorageData(); 
            await session.defaultSession.clearCache(); 
            log.info("Electron session data and cache cleared.");
        } else {
            log.warn("Electron session is not available for clearing data.");
        }
    } catch (error) {
        log.error("Failed to clear session data:", error);
    }

    app.relaunch(); 
    app.quit(); 
});

ipcMain.on("logout-and-relaunch", async (event) => {
    log.info(
        "Received 'logout-and-relaunch' signal (deprecated for direct call from show-logout-dialog)."
    );
    // This handler can now be simplified or removed if show-logout-dialog handles the full flow.
    // Keeping it for now, but its functionality is now essentially duplicated by show-logout-dialog's action.
    try {
        if (session && session.defaultSession) {
            await session.defaultSession.clearStorageData();
            await session.defaultSession.clearCache();
            log.info("Electron session data and cache cleared.");
        } else {
            log.warn("Electron session is not available for clearing data.");
        }
    } catch (error) {
        log.error("Failed to clear session data:", error);
    }

    app.relaunch();
    app.quit();
});
// --- END NEW IPC LISTENERS ---

function getBackendExecutablePath() {
    if (app.isPackaged) {
        return path.join(process.resourcesPath, "fastapibackend.exe");
    } else {
        return path.join(__dirname, "backend", "dist", "fastapibackend.exe");
    }
}

function startBackend() {
    const backendExePath = getBackendExecutablePath();

    console.log(`[BACKEND] Backend executable path: ${backendExePath}`);

    if (!fs.existsSync(backendExePath)) {
        dialog.showErrorBox(
            "Backend Error",
            `Backend executable not found at: ${backendExePath}\nPlease ensure you have built your Python backend with PyInstaller and that it's correctly placed by Electron Builder (check 'extraResources' in package.json).`
        );
        app.quit();
        return;
    }

    console.log(
        `[BACKEND] Attempting to spawn backend from: ${backendExePath}`
    );
    backendProcess = spawn(backendExePath);

    backendProcess.stdout.on("data", (data) => {
        console.log(`[BACKEND] stdout: ${data.toString().trim()}`);
    });

    backendProcess.stderr.on("data", (data) => {
        console.error(`[BACKEND] stderr: ${data.toString().trim()}`);
    });

    backendProcess.on("close", (code) => {
        console.log(`[BACKEND] process exited with code ${code}`);
        // Exit code 0, null, or 15 (SIGTERM) are considered normal shutdowns
        if (code !== 0 && code !== null && code !== 15) {
            dialog.showErrorBox(
                "Backend Crashed",
                `The backend application exited unexpectedly with code ${code}. Please check console for errors.`
            );
        } else if (code === 15) {
            console.log("[BACKEND] Backend shutdown gracefully (SIGTERM).");
        }
    });

    backendProcess.on("error", (err) => {
        console.error(
            `[BACKEND] Failed to start backend process: ${err.message}`
        );
        dialog.showErrorBox(
            "Backend Launch Error",
            `Could not start the backend application. Error: ${err.message}`
        );
        app.quit();
    });
    console.log("[BACKEND] Backend process spawned.");
}

function pollBackendReady(callback, retries = 30, delay = 1000) {
    let attempts = 0;

    const check = () => {
        attempts++;
        console.log(
            `[BACKEND] Checking backend readiness... Attempt ${attempts}/${retries}`
        );
        const request = http.get(BACKEND_HEALTH_URL, (res) => {
            if (res.statusCode === 200) {
                console.log("[BACKEND] Backend is ready!");
                callback();
            } else {
                console.warn(
                    `[BACKEND] Backend responded with status ${res.statusCode}. Retrying...`
                );
                if (attempts < retries) {
                    setTimeout(check, delay);
                } else {
                    dialog.showErrorBox(
                        "Backend Timeout",
                        `Backend did not become ready within the expected time. Please check backend logs. URL: ${BACKEND_HEALTH_URL}`
                    );
                    app.quit();
                }
            }
        });

        request.on("error", (err) => {
            console.warn(
                `[BACKEND] Connection to backend failed: ${err.message}. Retrying...`
            );
            if (attempts < retries) {
                setTimeout(check, delay);
            } else {
                dialog.showErrorBox(
                    "Backend Timeout",
                    `Could not connect to backend within the expected time. Please ensure the backend is running and accessible at ${BACKEND_HEALTH_URL}. Error: ${err.message}`
                );
                app.quit();
            }
        });

        request.end();
    };
    check();
}

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1200,
        height: 800,
        minWidth: 800,
        minHeight: 600,
        webPreferences: {
            preload: path.join(__dirname, "preload.js"),
            nodeIntegration: false,
            contextIsolation: true,
        },
        autoHideMenuBar: true,
        icon: path.join(__dirname, "build", "icon.ico"), 
    });

    const frontendPath = path.join(__dirname, "frontend", "dist", "index.html");
    console.log(`[FRONTEND] Loading frontend from: ${frontendPath}`);

    if (fs.existsSync(frontendPath)) {
        mainWindow.loadFile(frontendPath);
    } else {
        dialog.showErrorBox(
            "Frontend Build Missing",
            `Frontend build not found at ${frontendPath}. Please run 'npm run build' in your 'frontend/' directory.`
        );
        app.quit();
    }

    mainWindow.on("closed", () => {
        console.log(
            "[MAIN WINDOW] mainWindow was closed, setting reference to null."
        );
        mainWindow = null;
    });
}

const gotTheLock = app.requestSingleInstanceLock();
console.log(
    `[APP LIFECYCLE] Single instance lock attempt: ${
        gotTheLock ? "Acquired" : "Failed (another instance detected)"
    }`
);

if (!gotTheLock) {
    console.log(
        "[APP LIFECYCLE] Another instance of the application is already running. Quitting this instance."
    );
    app.quit();
} else {
    app.on("second-instance", (event, commandLine, workingDirectory) => {
        console.log(
            "[APP LIFECYCLE] Second instance attempted to launch. Focusing existing window."
        );
        if (mainWindow) {
            if (mainWindow.isMinimized()) mainWindow.restore();
            mainWindow.focus();
        }
    });

    app.on("ready", async () => {
        console.log("[APP LIFECYCLE] Electron app 'ready' event fired.");

        try {
            await killPort(BACKEND_PORT);
            console.log("[APP LIFECYCLE] killPort operation completed.");
        } catch (error) {
            console.error(
                `[APP LIFECYCLE] Critical error during killPort operation: ${error.message}. Quitting application.`
            );
            dialog.showErrorBox(
                "Port Cleaning Error",
                `Could not ensure port ${BACKEND_PORT} is free: ${error.message}. Application will quit.`
            );
            app.quit();
            return;
        }

        startBackend();

        pollBackendReady(() => {
            createWindow();
            setTimeout(() => {
                autoUpdater.checkForUpdatesAndNotify();
            }, 5000);
        });

        app.on("activate", function () {
            if (BrowserWindow.getAllWindows().length === 0) {
                console.log(
                    "[APP LIFECYCLE] Activate event: No windows open, creating one."
                );
                createWindow();
            } else {
                console.log(
                    "[APP LIFECYCLE] Activate event: Windows already open, focusing."
                );
                if (mainWindow) {
                    if (mainWindow.isMinimized()) mainWindow.restore();
                    mainWindow.focus();
                }
            }
        });
    });
}

app.on("window-all-closed", () => {
    console.log("[APP LIFECYCLE] All windows closed.");
    if (process.platform !== "darwin") {
        app.quit();
    }
});

app.on("will-quit", async (event) => {
    event.preventDefault();
    console.log(
        "[APP LIFECYCLE] 'will-quit' event fired. Initiating backend termination sequence."
    );

    if (backendProcess) {
        console.log("Terminating backend process...");

        let killTimeout;
        let isShuttingDown = false;

        const cleanupAndExit = () => {
            if (killTimeout) clearTimeout(killTimeout);
            backendProcess = null;
            console.log(
                "[APP LIFECYCLE] Backend process reference cleared. Allowing Electron to exit."
            );
            app.exit(0);
        };

        const checkAndKill = () => {
            try {
                process.kill(backendProcess.pid, 0);
                console.log(
                    "Backend process still running after timeout, sending SIGKILL..."
                );
                backendProcess.kill("SIGKILL");
            } catch (e) {
                console.log(
                    "Backend process already terminated (during force kill check)."
                );
            } finally {
                cleanupAndExit();
            }
        };

        backendProcess.once("close", (code) => {
            if (!isShuttingDown) {
                isShuttingDown = true;
                console.log(`Backend process closed with code ${code}`);
                cleanupAndExit();
            }
        });

        backendProcess.once("error", (err) => {
            if (!isShuttingDown) {
                isShuttingDown = true;
                console.error(
                    `Error with backend process during termination: ${err.message}`
                );
                cleanupAndExit();
            }
        });

        try {
            console.log("Sending shutdown request to backend API endpoint...");
            const { default: fetch } = await import("node-fetch");

            const response = await fetch(BACKEND_SHUTDOWN_URL, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
            });

            if (response.ok) {
                console.log(
                    "Backend shutdown endpoint called successfully. Waiting for process to exit..."
                );
                // Set a timeout to force kill if graceful shutdown takes too long
                killTimeout = setTimeout(checkAndKill, 5000);
            } else {
                console.error(
                    `Backend shutdown endpoint returned error: ${response.status} ${response.statusText}. Proceeding with signal termination.`
                );
                backendProcess.kill("SIGTERM");
                console.log("Sent SIGTERM to backend process (as fallback).");
                killTimeout = setTimeout(checkAndKill, 5000);
            }
        } catch (error) {
            console.error(
                `Error calling backend shutdown endpoint: ${error.message}. Proceeding with signal termination.`
            );
            try {
                backendProcess.kill("SIGTERM");
                console.log("Sent SIGTERM to backend process (as fallback).");
            } catch (killError) {
                console.error(`Error sending SIGTERM: ${killError.message}`);
            }
            killTimeout = setTimeout(checkAndKill, 5000);
        }
    } else {
        console.log("No backend process to terminate.");
        app.exit(0);
    }
});