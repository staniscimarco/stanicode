# STANICODE

Applicazione desktop locale. **Il pacchetto Windows completo è disponibile come candidato da provare.**

[Scarica lo ZIP completo (5,65 GB)](https://github.com/staniscimarco/stanicode/actions/runs/39125576752/artifacts/12135978883). Chiudi la vecchia versione, estrai tutto lo ZIP e apri `STANICODE/STANICODE.exe`. Scegli la cartella del progetto, scrivi la richiesta e premi Avvia sviluppo. Modello, Python e WebView2 sono inclusi. [Dimensione esatta, SHA-256 e istruzioni](docs/WINDOWS_DELIVERY.md).

È implementata l’integrazione React/TypeScript → Tauri → backend Python: scelta cartella, proposta di file tramite llama-server locale, approvazione, scrittura, test reali Python/Node/Rust, ruoli sequenziali, riparazione, memoria SQLite con ricerca dei casi, checkpoint Git, ripristino e rapporti. Interfaccia italiano/inglese con temi chiaro/scuro.

Il workflow Windows completo acquisisce e verifica Qwen2.5-Coder 7B, llama.cpp CPU, WebView2 e le relative licenze. La prova reale del modello ha superato generazione, approvazione, test e revisione indipendente. I test rapidi del browser usano invece un modello simulato dichiarato. La verifica nativa offline, il riavvio e gli audit di DLL/licenze sono passati su un runner Windows; la creazione e il caricamento dello ZIP completo sono riusciti; i test su Windows 10/11 puliti restano un requisito separato. Nessuna release completa è stata pubblicata. L’installer di sviluppo già disponibile non contiene il modello.

Per sviluppare: `npm ci`, `python3 -m unittest discover -s tests -v`, `npm run build`, quindi `npm run desktop -- dev` con i prerequisiti nativi Tauri installati. Su Windows usare `python`. Vedi [README](README.md), [stato](docs/STATUS.md) e [sicurezza](SECURITY.md). I test approvati eseguono codice con i permessi dell’utente: non sono isolati dal sistema operativo.

Sono disponibili anche comandi sperimentali di preparazione dei dataset revisionati e delle configurazioni LoRA/MergeKit. Non eseguono addestramento né cambiano i pesi del modello: vedi [ricerca sperimentale](docs/EXPERIMENTAL_RESEARCH.md).
