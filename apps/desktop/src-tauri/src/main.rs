#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
use serde::{Deserialize, Serialize};
use std::{
    io::{BufRead, BufReader},
    process::{Child, ChildStdin, Command, Stdio},
    sync::Mutex,
};
use tauri::Manager;

#[derive(Clone, Deserialize, Serialize)]
struct Connection {
    port: u16,
    token: String,
}
struct Backend {
    child: Mutex<Child>,
    _input: Mutex<Option<ChildStdin>>,
    connection: Connection,
}
impl Drop for Backend {
    fn drop(&mut self) {
        // Closing stdin asks the backend to shut down its supervised inference runtime.
        if let Ok(input) = self._input.get_mut() {
            input.take();
        }
        if let Ok(child) = self.child.get_mut() {
            for _ in 0..70 {
                if matches!(child.try_wait(), Ok(Some(_))) {
                    return;
                }
                std::thread::sleep(std::time::Duration::from_millis(100));
            }
            let _ = child.kill();
            let _ = child.wait();
        }
    }
}
#[tauri::command]
fn connection(state: tauri::State<'_, Backend>) -> Connection {
    state.connection.clone()
}
fn main() {
    // A portable Windows payload carries its own fixed WebView2 runtime.
    // Set this before the native webview is constructed; no first-run download.
    #[cfg(windows)]
    if !cfg!(debug_assertions) {
        if let Ok(executable) = std::env::current_exe() {
            if let Some(directory) = executable.parent() {
                let runtime = directory.join("payload").join("webview2");
                if runtime.join("msedgewebview2.exe").is_file() {
                    // Microsoft's Fixed Version >=120 Win32 distribution
                    // contract requires these read/execute package SIDs on
                    // Windows 10. Apply only to the bundled public runtime;
                    // no workspace, model or user-data ACL is changed.
                    use std::os::windows::process::CommandExt;
                    let system = std::env::var_os("SystemRoot")
                        .map(std::path::PathBuf::from)
                        .unwrap_or_else(|| std::path::PathBuf::from("C:\\Windows"));
                    let _ = Command::new(system.join("System32").join("icacls.exe"))
                        .arg(&runtime)
                        .args([
                            "/grant",
                            "*S-1-15-2-2:(OI)(CI)(RX)",
                            "*S-1-15-2-1:(OI)(CI)(RX)",
                        ])
                        .creation_flags(0x08000000)
                        .stdout(Stdio::null())
                        .stderr(Stdio::null())
                        .status();
                    std::env::set_var("WEBVIEW2_BROWSER_EXECUTABLE_FOLDER", runtime);
                }
            }
        }
    }
    let builder = tauri::Builder::default();
    #[cfg(windows)]
    let builder = builder.plugin(tauri_plugin_single_instance::init(|app, _, _| {
        if let Some(window) = app.get_webview_window("main") {
            let _ = window.show();
            let _ = window.unminimize();
            let _ = window.set_focus();
        }
    }));
    builder
        .plugin(tauri_plugin_dialog::init())
        .setup(|app| {
            let data = app.path().app_local_data_dir()?;
            std::fs::create_dir_all(&data)?;
            let mut command;
            let bundle;
            if cfg!(debug_assertions) {
                let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
                    .ancestors()
                    .nth(3)
                    .unwrap();
                command = Command::new(std::env::var("STANICODE_PYTHON").unwrap_or_else(|_| {
                    if cfg!(windows) {
                        "python".into()
                    } else {
                        "python3".into()
                    }
                }));
                command.arg(root.join("services/agent/server.py"));
                bundle = root.join("models");
            } else {
                let payload = app.path().resource_dir()?.join("payload");
                command = Command::new(payload.join(if cfg!(windows) {
                    "stanicode-agent.exe"
                } else {
                    "stanicode-agent"
                }));
                bundle = payload.join("models");
            }
            command
                .arg("--data")
                .arg(data)
                .arg("--bundle")
                .arg(bundle)
                .arg("--parent-stdin");
            // Expert opt-in only. The ordinary launcher always uses its bundle;
            // the adapter never downloads or installs an external service/model.
            if let Ok(model) = std::env::var("STANICODE_ADVANCED_OLLAMA_MODEL") {
                command.arg("--ollama-model").arg(model);
            }
            command
                .stdin(Stdio::piped())
                .stdout(Stdio::piped())
                .stderr(Stdio::null());
            #[cfg(windows)]
            {
                use std::os::windows::process::CommandExt;
                command.creation_flags(0x08000000);
            }
            let mut child = command.spawn()?;
            let input = child.stdin.take();
            let stdout = child.stdout.take().ok_or("Backend stdout unavailable")?;
            let (sender, receiver) = std::sync::mpsc::channel();
            std::thread::spawn(move || {
                let mut line = String::new();
                let result = BufReader::new(stdout).read_line(&mut line).map(|_| line);
                let _ = sender.send(result);
            });
            let result = receiver.recv_timeout(std::time::Duration::from_secs(30));
            let connection: Connection = match result {
                Ok(Ok(line)) => match serde_json::from_str(&line) {
                    Ok(value) => value,
                    Err(e) => {
                        let _ = child.kill();
                        return Err(e.into());
                    }
                },
                _ => {
                    let _ = child.kill();
                    return Err("Backend startup timed out or failed".into());
                }
            };
            app.manage(Backend {
                child: Mutex::new(child),
                _input: Mutex::new(input),
                connection,
            });
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![connection])
        .run(tauri::generate_context!())
        .expect("STANICODE could not start its native shell");
}
