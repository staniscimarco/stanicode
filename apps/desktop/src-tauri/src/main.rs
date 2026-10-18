#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
use serde::{Deserialize, Serialize};
use std::{io::{BufRead, BufReader}, process::{Child, ChildStdin, Command, Stdio}, sync::Mutex};
use tauri::Manager;

#[derive(Clone, Deserialize, Serialize)]
struct Connection { port: u16, token: String }
struct Backend { child: Mutex<Child>, _input: Mutex<Option<ChildStdin>>, connection: Connection }
impl Drop for Backend {
    fn drop(&mut self) {
        // Closing stdin asks the backend to shut down its supervised inference runtime.
        if let Ok(input) = self._input.get_mut() { input.take(); }
        if let Ok(child) = self.child.get_mut() {
            for _ in 0..70 {
                if matches!(child.try_wait(), Ok(Some(_))) { return; }
                std::thread::sleep(std::time::Duration::from_millis(100));
            }
            let _ = child.kill(); let _ = child.wait();
        }
    }
}
#[tauri::command]
fn connection(state: tauri::State<'_, Backend>) -> Connection { state.connection.clone() }
fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .setup(|app| {
            let data = app.path().app_local_data_dir()?;
            std::fs::create_dir_all(&data)?;
            let mut command;
            let bundle;
            if cfg!(debug_assertions) {
                let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).ancestors().nth(3).unwrap();
                command = Command::new(std::env::var("STANICODE_PYTHON").unwrap_or_else(|_| if cfg!(windows) {"python".into()} else {"python3".into()}));
                command.arg(root.join("services/agent/server.py"));
                bundle = root.join("models");
            } else {
                let payload = app.path().resource_dir()?.join("payload");
                command = Command::new(payload.join(if cfg!(windows) {"stanicode-agent.exe"} else {"stanicode-agent"}));
                bundle = payload.join("models");
            }
            command.arg("--data").arg(data).arg("--bundle").arg(bundle).arg("--parent-stdin");
            command.stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::null());
            #[cfg(windows)] {
                use std::os::windows::process::CommandExt;
                command.creation_flags(0x08000000);
            }
            let mut child = command.spawn()?;
            let input = child.stdin.take();
            let stdout = child.stdout.take().ok_or("Backend stdout unavailable")?;
            let (sender, receiver) = std::sync::mpsc::channel();
            std::thread::spawn(move || {
                let mut line=String::new();
                let result=BufReader::new(stdout).read_line(&mut line).map(|_|line);
                let _=sender.send(result);
            });
            let result = receiver.recv_timeout(std::time::Duration::from_secs(30));
            let connection: Connection = match result {
                Ok(Ok(line)) => match serde_json::from_str(&line) {
                    Ok(value) => value,
                    Err(e) => { let _=child.kill(); return Err(e.into()); }
                },
                _ => { let _=child.kill(); return Err("Backend startup timed out or failed".into()); }
            };
            app.manage(Backend { child: Mutex::new(child), _input: Mutex::new(input), connection });
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![connection])
        .run(tauri::generate_context!())
        .expect("STANICODE could not start its native shell");
}
