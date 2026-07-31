import { useCallback, useEffect, useMemo, useState } from "react";
import type { RunBundle, TabId } from "./types";
import { TABS } from "./types";

function verdictClass(v?: string): string {
  const u = (v || "").toUpperCase();
  if (u.includes("APPROVE")) return "ok";
  if (u.includes("REQUEST") || u.includes("CHANGES")) return "bad";
  if (u.includes("COMMENT")) return "warn";
  return "gold";
}

function fmtUsd(v: unknown): string {
  if (v == null || v === "") return "—";
  const n = Number(v);
  if (Number.isNaN(n)) return String(v);
  if (n >= 0.01) return `$${n.toFixed(2)}`;
  if (n > 0) return `$${n.toFixed(4)}`;
  return "$0";
}

function fmtBytes(n?: number): string {
  if (n == null) return "—";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

function shortSha(s?: string): string {
  if (!s) return "—";
  return s.length > 12 ? s.slice(0, 12) : s;
}

/** F32: build local/modal trigger commands (mirror scripts/trigger-review.sh print). */
function buildTriggerCommands(
  repo: string,
  pr: string,
  model: string,
  post: boolean,
): { local: string; modal: string; bit4: string; print: string } {
  const r = repo.trim() || "owner/repo";
  const n = pr.trim() || "1";
  const m = model.trim();
  const envLocal: string[] = [];
  if (m) envLocal.push(`TORII_MODEL=${m}`);
  if (post) envLocal.push("POST_COMMENT=1");
  const local =
    (envLocal.length ? envLocal.join(" ") + " " : "") +
    `./scripts/review-local.sh ${r} ${n}`;
  const modalParts = [
    "modal run modal_app/app.py --bit 3",
    `--repo ${r}`,
    `--pr ${n}`,
  ];
  if (m) modalParts.push(`--model ${m}`);
  if (!post) modalParts.push("--no-post-comment");
  const modal = modalParts.join(" ");
  const bit4 = [
    "modal run modal_app/app.py --bit 4",
    `--repo ${r}`,
    `--pr ${n}`,
    m ? `--model ${m}` : "",
  ]
    .filter(Boolean)
    .join(" ");
  const print = `./scripts/trigger-review.sh print ${r} ${n}`;
  return { local, modal, bit4, print };
}

function TriggerPanel({
  initialRepo = "",
  initialPr = "",
  initialModel = "openai/gpt-4.1-mini",
}: {
  initialRepo?: string;
  initialPr?: string;
  initialModel?: string;
}) {
  const [repo, setRepo] = useState(initialRepo);
  const [pr, setPr] = useState(initialPr);
  const [model, setModel] = useState(initialModel);
  const [post, setPost] = useState(true);
  const [copied, setCopied] = useState("");
  const cmds = useMemo(
    () => buildTriggerCommands(repo, pr, model, post),
    [repo, pr, model, post],
  );

  const copy = async (label: string, text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(label);
      setTimeout(() => setCopied(""), 1500);
    } catch {
      setCopied("failed");
    }
  };

  return (
    <div className="trigger-panel">
      <p className="section-title">Trigger a review (F32)</p>
      <p className="hint" style={{ marginTop: 0 }}>
        Console stays static — copy a command or POST the Modal webhook after{" "}
        <code className="inline-code">modal deploy modal_app/app.py</code>. Hermes
        never runs in the browser.
      </p>
      <div className="trigger-grid">
        <label>
          Repo
          <input
            value={repo}
            onChange={(e) => setRepo(e.target.value)}
            placeholder="owner/name"
            spellCheck={false}
          />
        </label>
        <label>
          PR
          <input
            value={pr}
            onChange={(e) => setPr(e.target.value)}
            placeholder="123"
            inputMode="numeric"
            spellCheck={false}
          />
        </label>
        <label className="wide">
          Model
          <input
            value={model}
            onChange={(e) => setModel(e.target.value)}
            placeholder="openai/gpt-4.1-mini"
            spellCheck={false}
          />
        </label>
        <label className="check">
          <input
            type="checkbox"
            checked={post}
            onChange={(e) => setPost(e.target.checked)}
          />
          Post PR comment
        </label>
      </div>
      {(
        [
          ["print", cmds.print],
          ["local", cmds.local],
          ["modal bit3", cmds.modal],
          ["modal bit4 dry", cmds.bit4],
        ] as const
      ).map(([label, cmd]) => (
        <div className="trigger-cmd" key={label}>
          <div className="trigger-cmd-head">
            <span className="tag mono">{label}</span>
            <button type="button" className="btn" onClick={() => copy(label, cmd)}>
              {copied === label ? "Copied" : "Copy"}
            </button>
          </div>
          <pre className="scroll-code compact">{cmd}</pre>
        </div>
      ))}
      <div className="block" style={{ marginTop: "1rem" }}>
        <h3>Webhook body (bit 4 + F33 auth)</h3>
        <pre className="scroll-code compact">
          {JSON.stringify(
            {
              repo: repo.trim() || "owner/repo",
              pr: Number(pr) || 0,
              model: model.trim() || "openai/gpt-4.1-mini",
              post_comment: post,
            },
            null,
            2,
          )}
        </pre>
        <p className="hint">
          Headers: <code className="inline-code">Authorization: Bearer $TORII_WEBHOOK_TOKEN</code>{" "}
          or GitHub <code className="inline-code">X-Hub-Signature-256</code> with{" "}
          <code className="inline-code">TORII_WEBHOOK_SECRET</code>.{" "}
          <code className="inline-code">issue_comment</code> +{" "}
          <code className="inline-code">@torii review</code> on a PR also accepted.
          Handler only <strong>spawns</strong> the worker.
        </p>
      </div>
    </div>
  );
}

export default function App() {
  const [bundle, setBundle] = useState<RunBundle | null>(null);
  const [tab, setTab] = useState<TabId>("overview");
  const [error, setError] = useState("");
  const [sourceLabel, setSourceLabel] = useState("Loading…");
  const [booting, setBooting] = useState(true);

  const loadBundle = useCallback((data: RunBundle, label: string) => {
    setBundle(data);
    setSourceLabel(label);
    setError("");
    setTab("overview");
  }, []);

  useEffect(() => {
    let cancel = false;
    (async () => {
      try {
        const res = await fetch("/fixtures/run-bundle.json");
        if (!res.ok) throw new Error(`Missing fixture (${res.status}). Run npm run pack-fixture.`);
        const data = (await res.json()) as RunBundle;
        if (!cancel) loadBundle(data, "Fixture · e2e odoo PR #3 showcase");
      } catch (e) {
        if (!cancel) {
          setError(String(e));
          setSourceLabel("No fixture — use Load bundle or Run tab");
        }
      } finally {
        if (!cancel) setBooting(false);
      }
    })();
    return () => {
      cancel = true;
    };
  }, [loadBundle]);

  const onFile = async (file: File | null) => {
    if (!file) return;
    try {
      const text = await file.text();
      if (file.name.endsWith(".json") || text.trimStart().startsWith("{")) {
        loadBundle(JSON.parse(text) as RunBundle, `File · ${file.name}`);
        return;
      }
      setError("Expected a run-bundle.json from scripts/pack-run-for-ui.py");
    } catch (e) {
      setError(String(e));
    }
  };

  const stages = bundle?.timings?.stages ?? [];
  const maxSec = useMemo(
    () => Math.max(1, ...stages.map((s) => s.seconds || 0)),
    [stages],
  );

  if (booting && !bundle) {
    return (
      <div className="shell">
        <div className="strip">
          <p className="wordmark">Torii</p>
          <span className="tag">Loading run…</span>
        </div>
      </div>
    );
  }

  // No bundle yet — still allow F32 trigger + load
  if (!bundle) {
    return (
      <div className="shell">
        <header className="strip">
          <p className="wordmark">Torii</p>
          <div className="strip-meta">
            <span className="tag">Run console</span>
            <span className="tag mono">{sourceLabel}</span>
          </div>
          <div className="strip-actions">
            <label className="btn">
              Load bundle
              <input
                className="file-input"
                type="file"
                accept="application/json,.json"
                onChange={(e) => onFile(e.target.files?.[0] ?? null)}
              />
            </label>
          </div>
        </header>
        <div className="main" style={{ padding: "1.25rem" }}>
          {error && <div className="banner-error">{error}</div>}
          <TriggerPanel />
        </div>
      </div>
    );
  }

  const { run, pr, result, cost, timings, memory, trace, diff } = bundle;
  const signals = bundle.signals;
  const loop = bundle.loop;
  const vClass = verdictClass(result.verdict);

  return (
    <div className="shell">
      <header className="strip">
        <p className="wordmark">Torii</p>
        <div className="strip-meta">
          <span className={`tag ${vClass}`}>{result.verdict || "—"}</span>
          <span className="tag mono">{run.trace_id}</span>
          <span className="tag">{bundle.host}</span>
          <span className="tag mono">{run.model}</span>
          {run.total_seconds != null && (
            <span className="tag mono">{run.total_seconds}s</span>
          )}
          <span className="tag mono">{run.status}</span>
          {signals?.flags?.map((f) => (
            <span className="tag bad mono" key={f}>
              {f}
            </span>
          ))}
        </div>
        <div className="strip-actions">
          {pr.url && (
            <a className="btn" href={pr.url} target="_blank" rel="noreferrer">
              Open PR
            </a>
          )}
          {run.comment_url && (
            <a className="btn" href={run.comment_url} target="_blank" rel="noreferrer">
              Comment
            </a>
          )}
          <label className="btn">
            Load bundle
            <input
              className="file-input"
              type="file"
              accept="application/json,.json"
              onChange={(e) => onFile(e.target.files?.[0] ?? null)}
            />
          </label>
        </div>
      </header>

      <div className="pr-band">
        <h2>
          {pr.repo}#{pr.number}
          {pr.title ? ` · ${pr.title}` : ""}
        </h2>
        <div className="sub">
          <span>{sourceLabel}</span>
          {pr.author && <span>@{pr.author}</span>}
          {pr.base && pr.head && (
            <span className="tag mono">
              {pr.base} ← {pr.head}
            </span>
          )}
          {(pr.additions != null || pr.deletions != null) && (
            <span className="tag mono">
              +{pr.additions ?? 0} / −{pr.deletions ?? 0}
            </span>
          )}
        </div>
      </div>

      <div className="workspace">
        <nav className="rail" aria-label="Run sections">
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              aria-current={tab === t.id ? "page" : undefined}
              onClick={() => setTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </nav>

        <main className="main">
          {error && <div className="banner-error">{error}</div>}

          {tab === "run" && (
            <TriggerPanel
              key={`${pr.repo}-${pr.number}-${run.model}`}
              initialRepo={pr.repo || ""}
              initialPr={pr.number || ""}
              initialModel={run.model || "openai/gpt-4.1-mini"}
            />
          )}

          {tab === "overview" && (
            <>
              <p className="section-title">Run overview</p>
              <div className="measures">
                <div className="measure">
                  <div className="lbl">Verdict</div>
                  <div className={`val ${vClass === "ok" ? "ok" : vClass === "bad" ? "bad" : ""}`}>
                    {result.verdict || "—"}
                  </div>
                </div>
                <div className="measure">
                  <div className="lbl">Score</div>
                  <div className="val">{result.score || "—"}</div>
                </div>
                <div className="measure">
                  <div className="lbl">Effort</div>
                  <div className="val">{result.effort || "—"}</div>
                </div>
                <div className="measure">
                  <div className="lbl">Cost</div>
                  <div className="val">{fmtUsd(cost.estimated_cost_usd)}</div>
                </div>
                <div className="measure">
                  <div className="lbl">Duration</div>
                  <div className="val">
                    {timings.total_seconds != null ? `${timings.total_seconds}s` : "—"}
                  </div>
                </div>
                <div className="measure">
                  <div className="lbl">SHA</div>
                  <div className="val mono">{shortSha(run.github_sha)}</div>
                </div>
              </div>

              {signals?.any && (
                <div className="block">
                  <h3>Ops signals (F40)</h3>
                  <p className="muted" style={{ marginBottom: "0.75rem" }}>
                    Gates that explain free-skips, hung kills, spend alerts, or
                    incomplete context — without opening raw logs.
                  </p>
                  <dl className="dl">
                    {signals.path_skip && (
                      <>
                        <dt>Path-skip (F38)</dt>
                        <dd>
                          Free skip — every changed path matched skip globs
                          {signals.path_skip_globs
                            ? ` (${signals.path_skip_globs})`
                            : ""}
                          {signals.path_skip_sample
                            ? ` · sample: ${signals.path_skip_sample}`
                            : ""}
                        </dd>
                      </>
                    )}
                    {signals.timeout && (
                      <>
                        <dt>Timeout (F36)</dt>
                        <dd>
                          Hermes wall-clock kill
                          {signals.timeout_seconds != null
                            ? ` after ${signals.timeout_seconds}s`
                            : ""}
                          {signals.timeout_stage
                            ? ` · stage ${signals.timeout_stage}`
                            : ""}
                        </dd>
                      </>
                    )}
                    {signals.over_budget && (
                      <>
                        <dt>Over budget (F29)</dt>
                        <dd>
                          Estimated cost exceeded soft max
                          {signals.budget_max_usd != null
                            ? ` ($${signals.budget_max_usd})`
                            : ""}
                        </dd>
                      </>
                    )}
                    {signals.diff_truncated && (
                      <>
                        <dt>Diff truncated (F27)</dt>
                        <dd>
                          Assembled PR diff hit MAX_DIFF_BYTES — findings may be
                          incomplete
                        </dd>
                      </>
                    )}
                    {signals.max_turns_hit && (
                      <>
                        <dt>Max turns (F41)</dt>
                        <dd>
                          Hermes iteration budget exhausted
                          {signals.max_turns != null
                            ? ` at ${signals.max_turns} turns`
                            : ""}{" "}
                          — raise <code>TORII_MAX_TURNS</code> or use a cheaper
                          model
                        </dd>
                      </>
                    )}
                    {(signals.model_tier_mode === "auto" ||
                      signals.model_tier_mode === "cheap" ||
                      signals.model_tier_mode === "full" ||
                      signals.model_tier === "cheap" ||
                      signals.model_tier === "full") && (
                      <>
                        <dt>Model tier (F42)</dt>
                        <dd>
                          {signals.model_tier_mode
                            ? `mode ${signals.model_tier_mode}`
                            : "tier"}
                          {signals.model_tier
                            ? ` · ${signals.model_tier}`
                            : ""}
                          {signals.model_tier_reason
                            ? ` · ${signals.model_tier_reason}`
                            : ""}
                          {signals.model ? (
                            <>
                              {" "}
                              · <code>{signals.model}</code>
                            </>
                          ) : null}
                        </dd>
                      </>
                    )}
                    {(signals.preflight_refuse ||
                      signals.preflight_forced_cheap) && (
                      <>
                        <dt>Preflight cost (F43)</dt>
                        <dd>
                          {signals.preflight_refuse
                            ? "Refused paid Hermes — estimate exceeded budget"
                            : "Forced cheap model — estimate exceeded budget on premium model"}
                          {signals.preflight_estimated_usd != null
                            ? ` · est $${signals.preflight_estimated_usd}`
                            : ""}
                          {signals.preflight_reason
                            ? ` · ${signals.preflight_reason}`
                            : ""}
                        </dd>
                      </>
                    )}
                  </dl>
                </div>
              )}

              {(loop?.tool_call_turns != null ||
                loop?.message_count != null ||
                loop?.max_turns != null) && (
                <div className="block">
                  <h3>Agent loop (F41)</h3>
                  <dl className="dl">
                    {loop.tool_call_turns != null && (
                      <>
                        <dt>Tool-call turns</dt>
                        <dd className="mono">{loop.tool_call_turns}</dd>
                      </>
                    )}
                    {loop.message_count != null && (
                      <>
                        <dt>Messages</dt>
                        <dd className="mono">{loop.message_count}</dd>
                      </>
                    )}
                    {loop.step_count != null && (
                      <>
                        <dt>Steps</dt>
                        <dd className="mono">{loop.step_count}</dd>
                      </>
                    )}
                    {loop.max_turns != null && (
                      <>
                        <dt>Max turns cap</dt>
                        <dd className="mono">
                          {loop.max_turns}
                          {loop.max_turns_hit ? " · HIT" : ""}
                        </dd>
                      </>
                    )}
                  </dl>
                </div>
              )}

              <div className="block">
                <h3>Summary</h3>
                <div className="prose">
                  {result.summary || "No summary in review."}
                </div>
              </div>

              {!!result.blocking?.length && (
                <div className="block">
                  <h3>Blocking</h3>
                  <ul className="list">
                    {result.blocking.map((b, i) => (
                      <li key={i}>{b}</li>
                    ))}
                  </ul>
                </div>
              )}

              {stages.length > 0 && (
                <div className="block">
                  <h3>Pipeline stages</h3>
                  <div className="stages">
                    {stages.map((s) => (
                      <div className="stage-row" key={s.name}>
                        <span className="name">{s.name}</span>
                        <div className="bar">
                          <span
                            className={s.exit_code !== 0 ? "fail" : undefined}
                            style={{
                              width: `${Math.max(4, (100 * (s.seconds || 0)) / maxSec)}%`,
                            }}
                          />
                        </div>
                        <span className="sec">{s.seconds}s</span>
                        <span className="rc">{s.exit_code}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <dl className="dl">
                <dt>Trace ID</dt>
                <dd>{run.trace_id}</dd>
                <dt>Run ID</dt>
                <dd>{run.run_id || "—"}</dd>
                <dt>Event</dt>
                <dd>{run.github_event_name || "—"}</dd>
                <dt>Started</dt>
                <dd>{run.started_at || "—"}</dd>
                <dt>Host</dt>
                <dd>{bundle.host}</dd>
              </dl>
            </>
          )}

          {tab === "pr" && (
            <>
              <p className="section-title">Pull request</p>
              <div className="block">
                <h3>{pr.title || "Untitled PR"}</h3>
                <dl className="dl">
                  <dt>Repo</dt>
                  <dd>{pr.repo}</dd>
                  <dt>Number</dt>
                  <dd>#{pr.number}</dd>
                  <dt>URL</dt>
                  <dd>
                    {pr.url ? (
                      <a href={pr.url} target="_blank" rel="noreferrer">
                        {pr.url}
                      </a>
                    ) : (
                      "—"
                    )}
                  </dd>
                  <dt>Author</dt>
                  <dd>{pr.author || "—"}</dd>
                  <dt>Branches</dt>
                  <dd>
                    {pr.base || "?"} ← {pr.head || "?"}
                  </dd>
                </dl>
              </div>
              {!!pr.files?.length && (
                <div className="block">
                  <h3>Changed files</h3>
                  <table className="grid">
                    <thead>
                      <tr>
                        <th>Path</th>
                        <th>+/−</th>
                      </tr>
                    </thead>
                    <tbody>
                      {pr.files.map((f) => (
                        <tr key={f.path}>
                          <td className="mono">{f.path}</td>
                          <td className="mono">
                            +{f.additions ?? 0} / −{f.deletions ?? 0}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              {pr.body && (
                <div className="block">
                  <h3>PR body</h3>
                  <div className="prose">{pr.body}</div>
                </div>
              )}
            </>
          )}

          {tab === "result" && (
            <>
              <p className="section-title">Review result</p>
              <div className="measures">
                <div className="measure">
                  <div className="lbl">Verdict</div>
                  <div className={`val ${vClass === "ok" ? "ok" : vClass === "bad" ? "bad" : ""}`}>
                    {result.verdict || "—"}
                  </div>
                </div>
                <div className="measure">
                  <div className="lbl">Score</div>
                  <div className="val">{result.score || "—"}</div>
                </div>
                <div className="measure">
                  <div className="lbl">Confidence</div>
                  <div className="val">{result.confidence || "—"}</div>
                </div>
                <div className="measure">
                  <div className="lbl">Effort</div>
                  <div className="val">{result.effort || "—"}</div>
                </div>
              </div>
              <div className="block">
                <h3>Summary</h3>
                <div className="prose">{result.summary || "—"}</div>
              </div>
              {result.walkthrough && (
                <div className="block">
                  <h3>Walkthrough</h3>
                  <div className="prose">{result.walkthrough}</div>
                </div>
              )}
              {result.security && (
                <div className="block">
                  <h3>Security audit</h3>
                  <div className="prose">{result.security}</div>
                </div>
              )}
              {result.suggestions && (
                <div className="block">
                  <h3>Suggestions</h3>
                  <div className="prose">{result.suggestions}</div>
                </div>
              )}
            </>
          )}

          {tab === "findings" && (
            <>
              <p className="section-title">Findings</p>
              {!!result.blocking?.length && (
                <div className="block">
                  <h3>Blocking</h3>
                  <ul className="list">
                    {result.blocking.map((b, i) => (
                      <li key={i}>{b}</li>
                    ))}
                  </ul>
                </div>
              )}
              {result.findings && result.findings.length > 0 ? (
                <table className="grid">
                  <thead>
                    <tr>
                      <th>Severity</th>
                      <th>File</th>
                      <th>Issue</th>
                      <th>Trigger</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.findings.map((f, i) => (
                      <tr key={i}>
                        <td>
                          <span className={`sev sev-${f.severity.toLowerCase()}`}>
                            {f.severity}
                          </span>
                        </td>
                        <td className="mono">{f.file}</td>
                        <td>{f.issue}</td>
                        <td>{f.trigger}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="empty">No structured findings table in this review.</p>
              )}
            </>
          )}

          {tab === "diff" && (
            <>
              <p className="section-title">PR diff</p>
              {diff.pr_diff ? (
                <pre className="scroll-code">{diff.pr_diff}</pre>
              ) : (
                <p className="empty">No pr.diff in this run package.</p>
              )}
            </>
          )}

          {tab === "trace" && (
            <>
              <p className="section-title">Trace & context</p>
              <div className="block">
                <h3>Run meta</h3>
                <dl className="dl">
                  <dt>Trace</dt>
                  <dd>{run.trace_id}</dd>
                  <dt>Ref</dt>
                  <dd>{run.github_ref || "—"}</dd>
                  <dt>SHA</dt>
                  <dd>{run.github_sha || "—"}</dd>
                  <dt>Trigger</dt>
                  <dd>{run.trigger_comment || "—"}</dd>
                </dl>
              </div>
              {trace.prompt_md && (
                <div className="block">
                  <h3>Prompt</h3>
                  <pre className="scroll-code">{trace.prompt_md}</pre>
                </div>
              )}
              {trace.context_md && (
                <div className="block">
                  <h3>Context</h3>
                  <pre className="scroll-code">{trace.context_md}</pre>
                </div>
              )}
              {trace.agent_log && (
                <div className="block">
                  <h3>Hermes / agent log</h3>
                  <pre className="scroll-code">{trace.agent_log}</pre>
                </div>
              )}
              {trace.hermes_stderr && (
                <div className="block">
                  <h3>Hermes stderr</h3>
                  <pre className="scroll-code">{trace.hermes_stderr}</pre>
                </div>
              )}
              {trace.meta_env && (
                <div className="block">
                  <h3>meta.env</h3>
                  <pre className="scroll-code">{trace.meta_env}</pre>
                </div>
              )}
            </>
          )}

          {tab === "loop" && (
            <>
              <p className="section-title">Agent loop</p>
              {(loop?.tool_call_turns != null ||
                loop?.message_count != null ||
                loop?.max_turns != null) && (
                <div className="measures">
                  {loop.tool_call_turns != null && (
                    <div className="measure">
                      <div className="lbl">Tool-call turns</div>
                      <div className="val mono">{loop.tool_call_turns}</div>
                    </div>
                  )}
                  {loop.message_count != null && (
                    <div className="measure">
                      <div className="lbl">Messages</div>
                      <div className="val mono">{loop.message_count}</div>
                    </div>
                  )}
                  {loop.step_count != null && (
                    <div className="measure">
                      <div className="lbl">Steps</div>
                      <div className="val mono">{loop.step_count}</div>
                    </div>
                  )}
                  {loop.max_turns != null && (
                    <div className="measure">
                      <div className="lbl">Max turns (F41)</div>
                      <div
                        className={`val mono${loop.max_turns_hit ? " bad" : ""}`}
                      >
                        {loop.max_turns}
                        {loop.max_turns_hit ? " HIT" : ""}
                      </div>
                    </div>
                  )}
                </div>
              )}
              {trace.agent_loop_md ? (
                <pre className="scroll-code">{trace.agent_loop_md}</pre>
              ) : (
                <p className="empty">No agent-loop.md in this package.</p>
              )}
            </>
          )}

          {tab === "cost" && (
            <>
              <p className="section-title">Cost & usage</p>
              <div className="measures">
                <div className="measure">
                  <div className="lbl">Estimated USD</div>
                  <div className="val">{fmtUsd(cost.estimated_cost_usd)}</div>
                </div>
                <div className="measure">
                  <div className="lbl">Tokens</div>
                  <div className="val">{String(cost.total_tokens ?? "—")}</div>
                </div>
                <div className="measure">
                  <div className="lbl">API calls</div>
                  <div className="val">{String(cost.api_calls ?? "—")}</div>
                </div>
                <div className="measure">
                  <div className="lbl">Model</div>
                  <div className="val mono">{String(cost.model ?? run.model)}</div>
                </div>
              </div>
              <dl className="dl">
                <dt>Input</dt>
                <dd>{String(cost.input_tokens ?? "—")}</dd>
                <dt>Output</dt>
                <dd>{String(cost.output_tokens ?? "—")}</dd>
                <dt>Cache read</dt>
                <dd>{String(cost.cache_read_tokens ?? "—")}</dd>
                <dt>Cache write</dt>
                <dd>{String(cost.cache_write_tokens ?? "—")}</dd>
                <dt>Provider</dt>
                <dd>{String(cost.provider ?? "—")}</dd>
                <dt>Status</dt>
                <dd>{String(cost.cost_status ?? "—")}</dd>
              </dl>
            </>
          )}

          {tab === "memory" && (
            <>
              <p className="section-title">Memory</p>
              {memory.health && Object.keys(memory.health).length > 0 ? (
                <div className="block">
                  <h3>Health (F30)</h3>
                  <dl className="dl">
                    {Object.entries(memory.health).map(([k, v]) => (
                      <>
                        <dt key={`${k}-k`}>{k}</dt>
                        <dd key={`${k}-v`}>{v}</dd>
                      </>
                    ))}
                  </dl>
                </div>
              ) : (
                <p className="empty">No memory-health.env in this package.</p>
              )}
              {memory.after_md && (
                <div className="block">
                  <h3>MEMORY after distill</h3>
                  <pre className="scroll-code">{memory.after_md}</pre>
                </div>
              )}
            </>
          )}

          {tab === "artifacts" && (
            <>
              <p className="section-title">Artifacts</p>
              {trace.artifacts && trace.artifacts.length > 0 ? (
                <table className="grid">
                  <thead>
                    <tr>
                      <th>Path</th>
                      <th>Size</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trace.artifacts.map((a) => (
                      <tr key={a.path}>
                        <td className="mono">{a.path}</td>
                        <td className="mono">{fmtBytes(a.bytes)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="empty">No artifact inventory.</p>
              )}
              {trace.files_txt && (
                <div className="block" style={{ marginTop: "1.5rem" }}>
                  <h3>files.txt</h3>
                  <pre className="scroll-code">{trace.files_txt}</pre>
                </div>
              )}
            </>
          )}

          {tab === "raw" && (
            <>
              <p className="section-title">Raw review Markdown</p>
              {result.review_md ? (
                <pre className="scroll-code">{result.review_md}</pre>
              ) : (
                <p className="empty">No review.md</p>
              )}
              {result.review_raw_md && (
                <div className="block" style={{ marginTop: "1.5rem" }}>
                  <h3>review.raw.md</h3>
                  <pre className="scroll-code">{result.review_raw_md}</pre>
                </div>
              )}
            </>
          )}

          <p className="hint">
            Pack any Torii run:{" "}
            <code style={{ fontFamily: "var(--mono)", fontSize: "0.7rem" }}>
              python3 scripts/pack-run-for-ui.py --dir path/to/.torii-out -o
              run-bundle.json
            </code>
            . Design system: Impeccable Neo kinpaku (Operate) · PRODUCT.md /
            DESIGN.md in this folder.
          </p>
        </main>
      </div>
    </div>
  );
}
