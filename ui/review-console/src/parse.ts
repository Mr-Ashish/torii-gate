/** Client-side parse of Torii Gate review.md when loading raw markdown only. */
export function parseReviewMd(md: string) {
  const field = (name: string) => {
    const m = md.match(new RegExp(`^\\*\\*${name}:\\*\\*\\s*(.+)$`, "m"));
    return m?.[1]?.trim() ?? "";
  };
  const section = (heading: string) => {
    const re = new RegExp(
      `^### ${heading}\\s*\\n([\\s\\S]*?)(?=^### |\\Z)`,
      "m",
    );
    const m = md.match(re);
    return m?.[1]?.trim() ?? "";
  };
  const findings: {
    severity: string;
    file: string;
    issue: string;
    trigger: string;
  }[] = [];
  for (const line of section("Key findings").split("\n")) {
    const t = line.trim();
    if (!t.startsWith("|") || /^\|\s*-+/.test(t)) continue;
    const cells = t
      .replace(/^\||\|$/g, "")
      .split("|")
      .map((c) => c.trim());
    if (cells.length < 3 || ["severity", "sev"].includes(cells[0].toLowerCase()))
      continue;
    findings.push({
      severity: cells[0],
      file: cells[1] ?? "",
      issue: cells[2] ?? "",
      trigger: cells[3] ?? "",
    });
  }
  const blocking: string[] = [];
  for (const line of section("Blocking").split("\n")) {
    const s = line.trim();
    if (s.startsWith("- ") || s.startsWith("* "))
      blocking.push(s.replace(/^[-*]\s+/, "").slice(0, 500));
  }
  return {
    verdict: field("Verdict"),
    score: field("Score"),
    effort: field("Review effort"),
    confidence: field("Confidence"),
    summary: section("Summary"),
    walkthrough: section("Walkthrough"),
    blocking,
    findings,
    security: section("Security audit") || field("Security audit"),
    suggestions: section("Suggestions"),
    review_md: md,
  };
}
