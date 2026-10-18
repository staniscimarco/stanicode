# STANICODE

Applicazione desktop locale in sviluppo. **Non è una release Windows offline completa.**

È implementata l’integrazione React/TypeScript → Tauri → backend Python: scelta cartella, proposta di file tramite llama-server locale, approvazione, scrittura, test reali Python/Node/Rust, ruoli sequenziali, riparazione, memoria SQLite con ricerca dei casi, checkpoint Git, ripristino e rapporti. Interfaccia italiano/inglese con temi chiaro/scuro.

Il workflow Windows completo acquisisce e verifica Qwen2.5-Coder 7B, llama.cpp CPU, WebView2 e le relative licenze. La prova reale del modello ha superato generazione, approvazione, test e revisione indipendente. I test rapidi del browser usano invece un modello simulato dichiarato. La verifica nativa offline e la creazione dello ZIP completo sono ancora in corso; i test su Windows 10/11 puliti restano un requisito separato. Nessuna release completa è stata pubblicata. L’installer di sviluppo già disponibile non contiene il modello.

Per sviluppare: `npm ci`, `python3 -m unittest discover -s tests -v`, `npm run build`, quindi `npm run desktop -- dev` con i prerequisiti nativi Tauri installati. Su Windows usare `python`. Vedi [README](README.md), [stato](docs/STATUS.md) e [sicurezza](SECURITY.md). I test approvati eseguono codice con i permessi dell’utente: non sono isolati dal sistema operativo.
