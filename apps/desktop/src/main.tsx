import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { invoke } from "@tauri-apps/api/core";
import { open } from "@tauri-apps/plugin-dialog";
import "./style.css";

type Connection = { port: number; token: string };
type MemoryCase = {
  id: string;
  request: string;
  summary: string;
  recipe: string;
  evidence: string;
  metadata: { model: string };
  created: number;
};
type Change = { path: string; before: string | null; after: string };
type Task = {
  id: string;
  workspace: string;
  prompt: string;
  state: string;
  events: { phase: string; message: string; time: number }[];
  changes: Change[];
  pending: Change[] | null;
  approval_id: string | null;
};
type Health = {
  backend: boolean;
  project_tools?: { supported: boolean; installed: boolean; version: string; phase: string; error: string; busy: boolean } | null;
  inference: {
    ready: boolean;
    phase?: string;
    provider?: string;
    detail: string;
  };
};
const words = {
  it: {
    workspace: "Cartella progetto",
    choose: "Scegli cartella",
    request: "Cosa vuoi sviluppare?",
    start: "Avvia sviluppo",
    activity: "Attività",
    changes: "Modifiche",
    history: "Sessioni",
    memory: "Memoria",
    settings: "Impostazioni",
    about: "Informazioni",
    approve: "Approva modifiche e test",
    reject: "Rifiuta",
    cancel: "Annulla",
    pause: "Pausa",
    resume: "Riprendi",
    rollback: "Ripristina file",
    export: "Esporta rapporto",
    empty: "Le attività reali dell’agente appariranno qui.",
    offline: "Inferenza locale disponibile",
    unavailable: "Modello locale non disponibile",
    notice:
      "Prima versione di sviluppo. I test eseguono codice con i tuoi permessi: non sono isolati dal sistema operativo.",
    prompt: "Descrivi il risultato desiderato e come verificarlo…",
  },
  en: {
    workspace: "Project folder",
    choose: "Choose folder",
    request: "What do you want to build?",
    start: "Start Development",
    activity: "Activity",
    changes: "Changes",
    history: "Sessions",
    memory: "Memory",
    settings: "Settings",
    about: "About",
    approve: "Approve changes and tests",
    reject: "Reject",
    cancel: "Cancel",
    pause: "Pause",
    resume: "Resume",
    rollback: "Restore files",
    export: "Export report",
    empty: "Real agent activity will appear here.",
    offline: "Local inference available",
    unavailable: "Local model unavailable",
    notice:
      "Early development version. Tests execute code with your permissions; there is no operating-system sandbox.",
    prompt: "Describe the desired result and how to verify it…",
  },
};
export function App() {
  const [lang, setLang] = useState<"it" | "en">(
    (localStorage.getItem("locale") as "it" | "en") === "en" ? "en" : "it",
  );
  const [theme, setTheme] = useState(localStorage.getItem("theme") || "dark");
  const [connection, setConnection] = useState<Connection | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState("");
  const [workspace, setWorkspace] = useState("");
  const [prompt, setPrompt] = useState("");
  const [tasks, setTasks] = useState<Task[]>([]);
  const [selected, setSelected] = useState("");
  const [tab, setTab] = useState("activity");
  const [memory, setMemory] = useState<MemoryCase[]>([]);
  const [memoryQuery, setMemoryQuery] = useState("");
  const [busy, setBusy] = useState(false);
  const [toolBusy, setToolBusy] = useState(false);
  const w = words[lang];
  const modelStatus = health?.inference.ready
    ? w.offline
    : health?.inference.phase === "verifying"
      ? lang === "it"
        ? "Verifica del modello locale…"
        : "Verifying local model…"
      : health?.inference.phase === "loading"
        ? lang === "it"
          ? "Caricamento del modello locale…"
          : "Loading local model…"
        : !health
          ? lang === "it"
            ? "Avvio del motore locale…"
            : "Starting local engine…"
          : w.unavailable;
  const statusLabels: Record<string, string> =
    lang === "it"
      ? {
          running: "In corso",
          paused: "In pausa",
          awaiting_approval: "Da approvare",
          completed: "Completata",
          failed: "Non riuscita",
          cancelled: "Annullata",
          interrupted: "Interrotta",
          rolled_back: "Ripristinata",
        }
      : {
          running: "Running",
          paused: "Paused",
          awaiting_approval: "Awaiting approval",
          completed: "Completed",
          failed: "Failed",
          cancelled: "Cancelled",
          interrupted: "Interrupted",
          rolled_back: "Restored",
        };
  const task = tasks.find((t) => t.id === selected) || tasks[0];
  async function api<T>(path: string, body?: unknown): Promise<T> {
    if (!connection) throw Error("Desktop backend is not connected");
    const response = await fetch(`http://127.0.0.1:${connection.port}${path}`, {
      method: body ? "POST" : "GET",
      headers: {
        Authorization: `Bearer ${connection.token}`,
        ...(body ? { "Content-Type": "application/json" } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
    });
    const data = await response.json();
    if (!response.ok) throw Error(data.error || response.statusText);
    return data;
  }
  useEffect(() => {
    invoke<Connection>("connection")
      .then(setConnection)
      .catch((e) => setError(`Native desktop required: ${String(e)}`));
  }, []);
  useEffect(() => {
    if (!connection) return;
    let active = true;
    let running = false;
    const refresh = async () => {
      if (running) return;
      running = true;
      try {
        const [h, t] = await Promise.all([
          api<Health>("/health"),
          api<Task[]>("/tasks"),
        ]);
        if (active) {
          setHealth(h);
          setTasks(t);
        }
      } catch (e) {
        if (active) setError(String(e));
      } finally {
        running = false;
      }
    };
    void refresh();
    const timer = setInterval(refresh, 1000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [connection]);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("theme", theme);
  }, [theme]);
  useEffect(() => {
    document.documentElement.lang = lang;
    localStorage.setItem("locale", lang);
  }, [lang]);
  async function act(action: string) {
    if (!task) return;
    try {
      await api("/control", {
        id: task.id,
        action,
        approval_id: task.approval_id,
      });
      setError("");
    } catch (e) {
      setError(String(e));
    }
  }
  function exportJson(value: unknown) {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(
      new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }),
    );
    a.download = "STANICODE-report.json";
    a.click();
    URL.revokeObjectURL(a.href);
  }
  return (
    <div className="shell">
      <aside>
        <div className="brand">
          <img src="/brand.svg" alt="STANICODE" />
          <strong>STANICODE</strong>
        </div>
        <p className="eyebrow">LOCAL DEVELOPMENT STUDIO</p>
        <nav>
          {[
            "activity",
            "changes",
            "history",
            "memory",
            "settings",
            "about",
          ].map((t) => (
            <button
              className={tab === t ? "active" : ""}
              key={t}
              onClick={() => {
                setTab(t);
                if (t === "memory")
                  api<MemoryCase[]>("/memory")
                    .then(setMemory)
                    .catch((e) => setError(String(e)));
              }}
            >
              {w[t as keyof typeof w]}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <span className={"dot " + (health?.inference.ready ? "ready" : "")} />
          <span role="status">{modelStatus}</span>
          <small>v0.1.0-dev · local</small>
        </div>
      </aside>
      <main>
        <header>
          <div>
            <p className="eyebrow">YOUR WORKSPACE, YOUR MACHINE</p>
            <h1>{w.request}</h1>
          </div>
          <select
            aria-label="Language"
            value={lang}
            onChange={(e) => setLang(e.target.value as "it" | "en")}
          >
            <option value="it">Italiano</option>
            <option value="en">English</option>
          </select>
        </header>
        {error && (
          <div role="alert" className="error">
            {error}
            <button onClick={() => setError("")}>×</button>
          </div>
        )}
        <section className="composer">
          <div className="workspace">
            <span>{w.workspace}</span>
            <code>{workspace || "—"}</code>
            <button
              onClick={async () => {
                try {
                  const p = await open({ directory: true, multiple: false });
                  if (typeof p === "string") setWorkspace(p);
                } catch (e) {
                  setError(String(e));
                }
              }}
            >
              {w.choose}
            </button>
          </div>
          <textarea
            aria-label={w.request}
            placeholder={w.prompt}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
          />
          <div className="composer-footer">
            <span>
              Python · Node · Rust ·{" "}
              {lang === "it"
                ? "approvazione obbligatoria"
                : "approval required"}
            </span>
            <button
              className="primary"
              disabled={
                busy ||
                toolBusy || health?.project_tools?.busy || !workspace ||
                !prompt.trim() ||
                !health?.inference.ready ||
                tasks.some((t) =>
                  ["running", "paused", "awaiting_approval"].includes(t.state),
                )
              }
              onClick={async () => {
                setBusy(true);
                try {
                  const t = await api<{ id: string }>("/tasks", {
                    workspace,
                    prompt,
                  });
                  setSelected(t.id);
                  setTab("activity");
                  setError("");
                } catch (e) {
                  setError(String(e));
                } finally {
                  setBusy(false);
                }
              }}
            >
              {w.start} ↗
            </button>
          </div>
        </section>
        <p className="notice">{w.notice}</p>
        {tab === "settings" ? (
          <section className="panel">
            <h2>{w.settings}</h2>
            <label>
              Theme{" "}
              <select value={theme} onChange={(e) => setTheme(e.target.value)}>
                <option value="dark">Dark</option>
                <option value="light">Light</option>
              </select>
            </label>
            <p>{health?.inference.detail}</p>
            {health?.project_tools?.supported && (
              <div className="project-tools">
                <h3>{lang === "it" ? "Strumenti per i progetti JavaScript" : "JavaScript project tools"}</h3>
                <p>{lang === "it"
                  ? "Node.js e npm servono per verificare i progetti JavaScript. La configurazione scarica il pacchetto ufficiale e lo usa solo nei processi di verifica dell’app. STANICODE si avvia anche senza questi strumenti."
                  : "Node.js and npm validate JavaScript projects. Setup downloads the official package and uses it only in the app’s validation processes. STANICODE can start without these tools."}</p>
                <button disabled={toolBusy || health.project_tools.busy || tasks.some((item) => ["running", "paused", "awaiting_approval"].includes(item.state))}
                  onClick={async () => {
                    setToolBusy(true);
                    try {
                      const proposal = await api<{ approval_id: string; version: string; destination: string }>("/project-tools/node/propose", {});
                      const message = lang === "it"
                        ? `Autorizzi lo scaricamento di Node.js ${proposal.version} e npm da nodejs.org?\nDestinazione: ${proposal.destination}\nIl pacchetto e la firma verranno verificati. Nessuna modifica al PATH di sistema e nessun privilegio di amministratore.`
                        : `Approve downloading Node.js ${proposal.version} and npm from nodejs.org?\nDestination: ${proposal.destination}\nThe package and signature will be verified. No system PATH changes or administrator privileges.`;
                      if (confirm(message)) {
                        await api("/project-tools/node/install", { approval_id: proposal.approval_id });
                        setError("");
                      }
                    } catch (e) { setError(String(e)); }
                    finally { setToolBusy(false); }
                  }}>
                  {toolBusy || health.project_tools.busy
                    ? lang === "it" ? "Configurazione in corso…" : "Setting up…"
                    : health.project_tools.installed
                      ? lang === "it" ? "Verifica Node.js gestito" : "Verify managed Node.js"
                      : lang === "it" ? "Configura Node.js e npm" : "Set up Node.js and npm"}
                </button>
                <p role="status">{health.project_tools.installed ? `Node.js ${health.project_tools.version} · npm` : health.project_tools.error}</p>
              </div>
            )}
            <p>
              {lang === "it"
                ? "Nessuna chiave cloud e nessuna telemetria applicativa. Il modello e il runtime sono avviati localmente dal pacchetto completo."
                : "No cloud keys or application telemetry. The complete package starts its model and runtime locally."}
            </p>
          </section>
        ) : tab === "about" ? (
          <section className="panel">
            <h2>STANICODE</h2>
            <p>Autonomous AI Development Studio</p>
            <p>
              v0.1.0 ·{" "}
              {lang === "it"
                ? "Candidato in verifica"
                : "Candidate under validation"}
            </p>
            <p>
              {health?.inference.provider === "ollama"
                ? lang === "it"
                  ? "Adattatore Ollama locale avanzato: modello già installato e scelto dall’utente."
                  : "Advanced local Ollama adapter: an existing user-selected model."
                : lang === "it"
                  ? "Modello locale Qwen2.5-Coder 7B Q4_K_M · llama.cpp · CPU. Nessun abbonamento, account o servizio AI cloud."
                  : "Local Qwen2.5-Coder 7B Q4_K_M model · llama.cpp · CPU. No subscription, account or cloud AI service."}
            </p>
            <p>
              {lang === "it"
                ? "Il confronto e l’approvazione delle modifiche restano sotto il tuo controllo. La memoria conserva casi verificati dai test; non modifica i pesi del modello."
                : "You control change review and approval. Memory retains test-backed cases; it does not modify model weights."}
            </p>
            <p>
              {lang === "it"
                ? "Licenze e inventario delle dipendenze sono inclusi nel pacchetto completo."
                : "Licenses and dependency inventory are included in the complete package."}
            </p>
            <p>
              {lang === "it"
                ? "Microsoft WebView2 include Defender SmartScreen e può raccogliere e inviare dati di utilizzo a Microsoft secondo le condizioni incluse e https://aka.ms/privacy. Il lavoro AI locale funziona anche senza Internet."
                : "Microsoft WebView2 includes Defender SmartScreen and may collect and send usage information to Microsoft under its included terms and https://aka.ms/privacy. The local AI workflow also works without Internet."}
            </p>
          </section>
        ) : tab === "memory" ? (
          <section className="panel">
            <h2>{w.memory}</h2>
            <p>
              {lang === "it"
                ? "Solo evidenze di test superati. Nessun addestramento dei pesi."
                : "Passed test evidence only. No weight training."}
            </p>
            <div className="memory-search">
              <input
                aria-label={
                  lang === "it" ? "Cerca nella memoria" : "Search memory"
                }
                value={memoryQuery}
                onChange={(e) => setMemoryQuery(e.target.value)}
                placeholder={
                  lang === "it"
                    ? "Cerca un problema già risolto…"
                    : "Find a previously solved problem…"
                }
              />
              <button
                onClick={() =>
                  api<MemoryCase[]>(
                    "/memory?query=" + encodeURIComponent(memoryQuery),
                  )
                    .then(setMemory)
                    .catch((e) => setError(String(e)))
                }
              >
                {lang === "it" ? "Cerca" : "Search"}
              </button>
            </div>
            {memory.map((item) => (
              <details key={item.id}>
                <summary>{item.request}</summary>
                <p>{item.summary}</p>
                <small>
                  {item.recipe} · {item.metadata.model} ·{" "}
                  {new Date(item.created * 1000).toLocaleDateString(lang)}
                </small>
                <pre>{item.evidence}</pre>
              </details>
            ))}
            <button onClick={() => exportJson(memory)}>{w.export}</button>
            <button
              onClick={async () => {
                if (
                  confirm(
                    lang === "it"
                      ? "Eliminare tutti i casi salvati?"
                      : "Delete all saved cases?",
                  )
                ) {
                  try {
                    await api("/memory/delete", {});
                    setMemory([]);
                  } catch (e) {
                    setError(String(e));
                  }
                }
              }}
            >
              {lang === "it" ? "Elimina memoria" : "Delete memory"}
            </button>
          </section>
        ) : tab === "history" ? (
          <section className="panel">
            <h2>{w.history}</h2>
            {tasks.map((t) => (
              <button
                className="session"
                key={t.id}
                onClick={() => {
                  setSelected(t.id);
                  setTab("activity");
                }}
              >
                <span>{t.prompt}</span>
                <code>{statusLabels[t.state] || t.state}</code>
              </button>
            ))}
          </section>
        ) : (
          <section className="panel">
            <div className="panel-title">
              <h2>{tab === "changes" ? w.changes : w.activity}</h2>
              {task && (
                <span className="badge" data-state={task.state}>
                  {statusLabels[task.state] || task.state}
                </span>
              )}
            </div>
            {task ? (
              <>
                <div className="controls">
                  {["pause", "resume", "cancel"].map((a) => (
                    <button
                      key={a}
                      disabled={
                        !["running", "paused", "awaiting_approval"].includes(
                          task.state,
                        )
                      }
                      onClick={() => act(a)}
                    >
                      {w[a as keyof typeof w]}
                    </button>
                  ))}
                  <button onClick={() => exportJson(task)}>{w.export}</button>
                  <button
                    disabled={
                      ["running", "paused", "awaiting_approval"].includes(
                        task.state,
                      ) || !task.changes.length
                    }
                    onClick={async () => {
                      if (confirm(w.rollback + "?")) {
                        try {
                          await api("/rollback", { id: task.id });
                        } catch (e) {
                          setError(String(e));
                        }
                      }
                    }}
                  >
                    {w.rollback}
                  </button>
                </div>
                {task.state === "awaiting_approval" && (
                  <div className="approval">
                    <strong>
                      {lang === "it"
                        ? "Modifiche in attesa di revisione"
                        : "Changes await review"}
                    </strong>
                    <p>
                      {lang === "it"
                        ? "Esamina i file prima di autorizzare scrittura ed esecuzione dei test."
                        : "Inspect files before allowing writes and test execution."}
                    </p>
                    <button className="primary" onClick={() => act("approve")}>
                      {w.approve}
                    </button>
                    <button onClick={() => act("reject")}>{w.reject}</button>
                  </div>
                )}
                {tab === "changes" || task.state === "awaiting_approval"
                  ? (task.pending || task.changes).map((c, i) => (
                      <details
                        key={i}
                        open={task.state === "awaiting_approval"}
                      >
                        <summary>{c.path}</summary>
                        <div className="diff">
                          <div>
                            <small>BEFORE</small>
                            <pre>{c.before ?? "(new file)"}</pre>
                          </div>
                          <div>
                            <small>AFTER</small>
                            <pre>{c.after}</pre>
                          </div>
                        </div>
                      </details>
                    ))
                  : task.events.map((event, i) => (
                      <article className="event" key={i}>
                        <span>
                          {new Date(event.time * 1000).toLocaleTimeString(lang)}
                        </span>
                        <div>
                          <strong>{event.phase}</strong>
                          <pre>{event.message}</pre>
                        </div>
                      </article>
                    ))}
              </>
            ) : (
              <div className="empty">
                <span>◇</span>
                <p>{w.empty}</p>
              </div>
            )}
          </section>
        )}
      </main>
    </div>
  );
}
const root = document.getElementById("root");
if (root) createRoot(root).render(<App />);
