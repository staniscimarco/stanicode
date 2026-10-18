# STANICODE

Applicazione desktop locale in sviluppo. **Non è una release Windows offline completa.**

È implementata una prima integrazione React/TypeScript → Tauri → backend Python: scelta cartella, proposta di file tramite llama-server locale, approvazione, scrittura, test Python reali, tentativi di riparazione, cronologia SQLite, ripristino e rapporti. Interfaccia italiano/inglese con temi chiaro/scuro.

Il modello e il runtime di inferenza non sono inclusi. I test end-to-end usano un modello simulato dichiarato. Mancano ancora validazione su modello reale, sandbox, funzionalità per altri linguaggi, memoria con recupero dei casi, pacchetto portatile completo e test Windows puliti. Nessuna release è stata pubblicata.

Per sviluppare: `npm ci`, `python3 -m unittest discover -s tests -v`, `npm run build`, quindi `npm run desktop -- dev` con i prerequisiti nativi Tauri installati. Su Windows usare `python`. Vedi [README](README.md), [stato](docs/STATUS.md) e [sicurezza](SECURITY.md). I test approvati eseguono codice con i permessi dell’utente: non sono isolati dal sistema operativo.
