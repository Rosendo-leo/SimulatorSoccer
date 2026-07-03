use std::sync::Mutex;

use tauri::{Manager, RunEvent};
use tauri_plugin_shell::process::CommandChild;
use tauri_plugin_shell::ShellExt;

/// Handle do sidecar Python (rcj-server) para encerrá-lo junto com o app.
struct ServerProcess(Mutex<Option<CommandChild>>);

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .manage(ServerProcess(Mutex::new(None)))
        .setup(|app| {
            let (_rx, child) = app
                .shell()
                .sidecar("rcj-server")
                .expect("sidecar rcj-server não encontrado no bundle")
                .env("RCJ_SERVER_PORT", "8765")
                .spawn()
                .expect("falha ao iniciar o servidor de simulação");
            app.state::<ServerProcess>()
                .0
                .lock()
                .unwrap()
                .replace(child);
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("erro ao iniciar o app Tauri");

    app.run(|app_handle, event| {
        if let RunEvent::Exit = event {
            if let Some(child) = app_handle
                .state::<ServerProcess>()
                .0
                .lock()
                .unwrap()
                .take()
            {
                let _ = child.kill();
            }
        }
    });
}
