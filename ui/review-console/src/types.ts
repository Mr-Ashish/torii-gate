export type TabId =
  | "overview"
  | "run"
  | "pr"
  | "result"
  | "findings"
  | "diff"
  | "trace"
  | "loop"
  | "cost"
  | "memory"
  | "artifacts"
  | "raw";

export interface RunBundle {
  schema_version: number;
  host: string;
  packed_from?: string;
  run: {
    trace_id: string;
    run_id: string;
    run_attempt: string;
    status: string;
    model: string;
    started_at?: string;
    ended_at?: string;
    total_seconds?: number;
    github_sha?: string;
    github_ref?: string;
    github_event_name?: string;
    trigger_comment?: string;
    comment_url?: string;
    hermes_rc?: number | null;
  };
  pr: {
    repo: string;
    number: string;
    title: string;
    url: string;
    base?: string;
    head?: string;
    author?: string;
    additions?: number;
    deletions?: number;
    files?: { path?: string; additions?: number; deletions?: number }[];
    body?: string;
  };
  result: {
    verdict?: string;
    score?: string;
    effort?: string;
    confidence?: string;
    summary?: string;
    walkthrough?: string;
    blocking?: string[];
    findings?: {
      severity: string;
      file: string;
      issue: string;
      trigger: string;
    }[];
    security?: string;
    suggestions?: string;
    review_md?: string;
    review_raw_md?: string | null;
  };
  cost: Record<string, unknown>;
  timings: {
    total_seconds?: number;
    stages?: { name: string; seconds: number; exit_code: number }[];
  };
  /** F40/F41: ops gates — timeout, path-skip, budget, truncation, max-turns */
  signals?: {
    any?: boolean;
    flags?: string[];
    timeout?: boolean;
    timeout_seconds?: number | null;
    timeout_stage?: string;
    path_skip?: boolean;
    path_skip_sample?: string;
    path_skip_globs?: string;
    diff_truncated?: boolean;
    over_budget?: boolean;
    budget_max_usd?: number;
    max_turns_hit?: boolean;
    max_turns?: number | string | null;
    /** F42 auto model tier */
    model_tier_mode?: string | null;
    model_tier?: string | null;
    model_tier_reason?: string | null;
    model?: string | null;
    preflight_refuse?: boolean;
    preflight_forced_cheap?: boolean;
    preflight_estimated_usd?: number | string | null;
    preflight_decision?: string;
    preflight_reason?: string;
  };
  /** F41: Hermes agent-loop metrics */
  loop?: {
    tool_call_turns?: number | null;
    message_count?: number | null;
    step_count?: number | null;
    max_turns?: number | string | null;
    max_turns_enabled?: boolean;
    max_turns_hit?: boolean;
  };
  memory: {
    health?: Record<string, string>;
    after_md?: string | null;
  };
  trace: {
    meta?: Record<string, unknown>;
    agent_loop_md?: string | null;
    agent_log?: string | null;
    hermes_stderr?: string | null;
    prompt_md?: string | null;
    context_md?: string | null;
    files_txt?: string | null;
    meta_env?: string | null;
    artifacts?: { path: string; bytes?: number }[];
  };
  diff: {
    pr_diff?: string | null;
  };
}

export const TABS: { id: TabId; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "run", label: "Run" },
  { id: "pr", label: "Pull request" },
  { id: "result", label: "Result" },
  { id: "findings", label: "Findings" },
  { id: "diff", label: "Diff" },
  { id: "trace", label: "Trace" },
  { id: "loop", label: "Agent loop" },
  { id: "cost", label: "Cost" },
  { id: "memory", label: "Memory" },
  { id: "artifacts", label: "Artifacts" },
  { id: "raw", label: "Raw review" },
];
