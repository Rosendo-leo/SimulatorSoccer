// Auto-update do app desktop (Tauri). No navegador é um no-op — os plugins
// são importados dinamicamente só quando o webview do Tauri está presente.
const inTauri = typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window

export async function checkForAppUpdate() {
  if (!inTauri) return
  const { check }    = await import('@tauri-apps/plugin-updater')
  const { relaunch } = await import('@tauri-apps/plugin-process')
  const { ask, message } = await import('@tauri-apps/plugin-dialog')

  const update = await check()
  if (!update) return

  const yes = await ask(
    `Versão ${update.version} disponível (você está na ${update.currentVersion}).\n\n` +
    `Baixar e instalar agora?`,
    { title: 'Atualização disponível', kind: 'info' },
  )
  if (!yes) return

  await update.downloadAndInstall()
  const restart = await ask(
    'Atualização instalada. Reiniciar o app agora?',
    { title: 'Atualização pronta', kind: 'info' },
  )
  if (restart) await relaunch()
  else await message('A nova versão será usada na próxima vez que o app abrir.')
}
