import { createContext, useCallback, useContext, useMemo, useState } from "react";
import type { ReactNode } from "react";

// UI-chrome internationalization: English (default) and Chinese, persisted per
// browser. Scope is deliberately chrome-only — evidence content (trajectory
// text, commands, judge findings, statuses, categories, run ids, file paths)
// is data and always renders untranslated.

export type Language = "en" | "zh";

export const LANGUAGE_STORAGE_KEY = "hy3-workbench-language";

export const MESSAGES = {
  // App shell
  "app.eyebrow": { en: "Hy3 process evaluation workbench", zh: "Hy3 过程评估工作台" },
  "app.title": { en: "Evidence debugger", zh: "证据调试器" },
  "nav.runs": { en: "Runs", zh: "运行" },
  "nav.analytics": { en: "Analytics", zh: "分析" },
  "nav.regressions": { en: "Regressions", zh: "回归" },
  "health.checking": { en: "checking API…", zh: "正在检查 API…" },
  "health.unreachable": { en: "API unreachable", zh: "API 不可达" },

  // Shared fragments
  "common.step": { en: "step {n}", zh: "第 {n} 步" },
  "common.stepTitle": { en: "Step {n}", zh: "第 {n} 步" },
  "common.notEvaluated": { en: "not evaluated", zh: "未评估" },
  "common.none": { en: "None.", zh: "无。" },

  // Runs list
  "runs.title": { en: "Imported runs", zh: "已导入的运行" },
  "runs.lede": {
    en: "Every run below has immutable artifacts; open one to inspect its evidence.",
    zh: "下方每个运行都带有不可变的产物；打开任意一个以检查其证据。",
  },
  "runs.filter.outcome": { en: "Outcome", zh: "结果" },
  "runs.filter.process": { en: "Process", zh: "过程" },
  "runs.filter.all": { en: "all", zh: "全部" },
  "runs.loading": { en: "Loading runs…", zh: "正在加载运行…" },
  "runs.error": {
    en: "The run list could not be loaded from the local API.",
    zh: "无法从本地 API 加载运行列表。",
  },
  "runs.col.run": { en: "Run", zh: "运行" },
  "runs.col.repository": { en: "Repository", zh: "代码仓库" },
  "runs.col.difficulty": { en: "Difficulty", zh: "难度" },
  "runs.col.outcome": { en: "Outcome", zh: "结果" },
  "runs.col.process": { en: "Process", zh: "过程" },
  "runs.col.firstError": { en: "First error", zh: "第一处错误" },
  "runs.col.reviews": { en: "Reviews", zh: "评审" },
  "runs.empty": {
    en: "No runs match the current filters.",
    zh: "没有符合当前筛选条件的运行。",
  },

  // Run detail
  "run.back": { en: "← All runs", zh: "← 全部运行" },
  "run.difficulty": { en: "difficulty", zh: "难度" },
  "run.loading": { en: "Loading run…", zh: "正在加载运行…" },
  "run.error": {
    en: "This run could not be loaded from the local API.",
    zh: "无法从本地 API 加载该运行。",
  },
  "run.outcome": { en: "outcome: {status}", zh: "结果：{status}" },
  "run.process": { en: "process: {status}", zh: "过程：{status}" },
  "run.processHidden": {
    en: "process: hidden until your initial label",
    zh: "过程：在您保存初始标注前隐藏",
  },
  "run.correctResultInvalidProcess": {
    en: "correct result, invalid process",
    zh: "结果对、过程有问题",
  },
  "run.firstErrorAt": { en: "First error at step {n}", zh: "第一处错误位于第 {n} 步" },
  "run.firstErrorUnlocatable": {
    en: "A material error exists, but its first step is unlocatable",
    zh: "存在实质性错误，但无法定位其首个步骤",
  },
  "run.primaryCategory": { en: "Primary category: {category}", zh: "主要类别：{category}" },
  "run.noVerdict": { en: "No process verdict", zh: "无过程结论" },
  "run.noVerdictBody": {
    en: "The evidence cannot support a defensible judgment. Recorded reasons are listed in the verifier tab.",
    zh: "证据不足以支持可辩护的判断。记录的原因列在验证器标签页中。",
  },
  "run.tab.timeline": { en: "Timeline", zh: "时间线" },
  "run.tab.patch": { en: "Patch", zh: "补丁" },
  "run.tab.verifier": { en: "Verifier", zh: "验证器" },
  "run.tab.task": { en: "Task", zh: "任务" },
  "run.trajectoryInvalid": {
    en: "The stored trajectory failed validation and cannot be shown.",
    zh: "存储的轨迹未通过校验，无法显示。",
  },
  "run.trajectoryLoading": { en: "Loading trajectory…", zh: "正在加载轨迹…" },

  // Timeline
  "timeline.firstError": { en: "First error", zh: "第一处错误" },
  "timeline.downstream": { en: "downstream", zh: "下游" },
  "timeline.downstreamOf": { en: "downstream of step {n}", zh: "第 {n} 步的下游" },

  // Output rendering
  "output.showHiddenLine": {
    en: "Show 1 hidden line ({chars} chars total)",
    zh: "显示 1 行隐藏内容（共 {chars} 字符）",
  },
  "output.showHiddenLines": {
    en: "Show {n} hidden lines ({chars} chars total)",
    zh: "显示 {n} 行隐藏内容（共 {chars} 字符）",
  },
  "output.collapse": { en: "Collapse to preview", zh: "折叠为预览" },
  "output.noOutput": { en: "no output", zh: "无输出" },
  "output.showAll": { en: "show all ({chars} chars)", zh: "展开全部（{chars} 字符）" },
  "output.showLess": { en: "show less", zh: "收起" },

  // Evidence panel
  "evidence.showingLanes": {
    en: "Showing evidence lanes. Items citing step {n} are marked.",
    zh: "正在显示证据通道。引用第 {n} 步的条目已标记。",
  },
  "evidence.findings": { en: "Findings", zh: "判定发现" },
  "evidence.noFindings": { en: "No findings.", zh: "暂无发现。" },
  "evidence.checks": { en: "Deterministic checks", zh: "确定性检查" },
  "evidence.citesStep": { en: "cites step {n}", zh: "引用第 {n} 步" },
  "evidence.hardFailure": { en: "hard failure", zh: "硬性失败" },
  "evidence.propagation": { en: "recorded propagation:", zh: "记录的传播：" },
  "evidence.patchChip": { en: "patch", zh: "补丁" },
  "evidence.verifierChip": { en: "verifier", zh: "验证器" },
  "evidence.taskChip": { en: "task", zh: "任务" },
  "evidence.hiddenWhileBlinded": {
    en: "Semantic findings are hidden until your blinded initial label is saved.",
    zh: "在您保存盲评初始标注前，语义发现保持隐藏。",
  },

  // Review panel
  "review.history": { en: "Review history", zh: "评审历史" },
  "review.blindedInitial": { en: "Blinded initial review", zh: "盲评初始评审" },
  "review.blindedNote": {
    en: "The evaluator verdict stays hidden until you record your own label from the task, trajectory, patch, and verifier evidence.",
    zh: "在您基于任务、轨迹、补丁与验证器证据记录自己的标注之前，评估器结论保持隐藏。",
  },
  "review.reviewerAlias": { en: "Reviewer alias", zh: "评审者别名" },
  "review.yourLabel": { en: "Your label", zh: "您的标注" },
  "review.finalLabel": { en: "Final label", zh: "最终标注" },
  "review.processStatus": { en: "Process status", zh: "过程状态" },
  "review.firstError": { en: "First error", zh: "第一处错误" },
  "review.stepId": { en: "Step ID", zh: "步骤编号" },
  "review.primaryCategory": { en: "Primary category", zh: "主要类别" },
  "review.labelNotes": { en: "Label notes", zh: "标注备注" },
  "review.saveInitial": {
    en: "Save initial label and reveal the verdict",
    zh: "保存初始标注并揭示评估结论",
  },
  "review.adjudication": { en: "Adjudication", zh: "裁定" },
  "review.decision": { en: "Decision", zh: "裁定决定" },
  "review.findingDecisions": { en: "Finding decisions", zh: "发现裁定" },
  "review.appendAdjudication": { en: "Append adjudication", zh: "追加裁定" },
  "review.initialLabelIs": { en: "Blinded initial label: {label}", zh: "盲评初始标注：{label}" },
  "review.finalLabelIs": { en: "Final label: {label}", zh: "最终标注：{label}" },
  "review.firstErrorAtStep": { en: "first error at step {n}", zh: "第一处错误位于第 {n} 步" },
  "review.firstErrorLocation": { en: "first error {location}", zh: "第一处错误 {location}" },

  // Artifact views
  "patch.empty": {
    en: "No verified patch artifact is available.",
    zh: "没有可用的已验证补丁产物。",
  },
  "verifier.testCol": { en: "Declared behavioral test", zh: "声明的行为测试" },
  "verifier.resultCol": { en: "Result", zh: "结果" },
  "verifier.missing": { en: "missing", zh: "缺失" },
  "verifier.excluded": { en: "Excluded from grading", zh: "已排除在评分之外" },
  "verifier.empty": {
    en: "No gradeable per-test verifier evidence exists for this run.",
    zh: "该运行没有可评分的逐测试验证器证据。",
  },
  "verifier.passedAll": {
    en: "{n}/{d} declared tests passed — show the full list",
    zh: "声明的测试 {n}/{d} 全部通过 — 展开完整列表",
  },
  "verifier.passedRemaining": {
    en: "{n}/{d} declared remaining tests passed — show the full list",
    zh: "其余声明的测试 {n}/{d} 全部通过 — 展开完整列表",
  },
  "verifier.rawOutput": { en: "Raw test output", zh: "原始测试输出" },
  "verifier.runLog": { en: "Verifier run log", zh: "验证器运行日志" },
  "task.problem": { en: "Problem statement", zh: "问题描述" },
  "task.contract": { en: "Behavioral contract", zh: "行为契约" },
  "task.protectedPaths": { en: "Protected paths", zh: "受保护路径" },

  // Analytics
  "analytics.loading": { en: "Computing analytics…", zh: "正在计算分析…" },
  "analytics.error": {
    en: "Analytics could not be loaded from the local API.",
    zh: "无法从本地 API 加载分析数据。",
  },
  "analytics.title": { en: "Aggregate analytics", zh: "汇总分析" },
  "analytics.lede": {
    en: "{runs} runs · {evaluated} evaluated · {reviewed} reviewed · {adjudicated} adjudicated. Every number carries its provenance:",
    zh: "{runs} 个运行 · {evaluated} 已评估 · {reviewed} 已评审 · {adjudicated} 已裁定。每个数字都带有其来源标注：",
  },
  "analytics.scope": { en: "Scope:", zh: "范围：" },
  "analytics.scopeSlice": {
    en: "— frozen evaluation slice with {n} tasks",
    zh: "— 冻结评估切片，包含 {n} 个任务",
  },
  "analytics.scopeMissing": { en: " (no runs yet: {tasks})", zh: "（尚无运行：{tasks}）" },
  "analytics.viewAll": { en: "View all runs", zh: "查看全部运行" },
  "analytics.quadrant": { en: "Outcome × process", zh: "结果 × 过程" },
  "analytics.quadrantCorner": { en: "outcome \\ process", zh: "结果 \\ 过程" },
  "analytics.errorDistribution": { en: "Primary error distribution", zh: "主要错误分布" },
  "analytics.noInvalid": { en: "No invalid processes yet.", zh: "暂无有问题的过程。" },
  "analytics.humanCount": { en: "{n} human", zh: "人工 {n}" },
  "analytics.evaluatorCount": { en: "{n} evaluator", zh: "评估器 {n}" },
  "analytics.requiredMetrics": { en: "Required metrics", zh: "必需指标" },
  "analytics.col.metric": { en: "Metric", zh: "指标" },
  "analytics.col.value": { en: "Value", zh: "数值" },
  "analytics.col.provenance": { en: "Provenance", zh: "来源" },
  "analytics.col.exclusions": { en: "Exclusions", zh: "排除项" },
  "analytics.excludedCount": { en: "{n} excluded", zh: "{n} 项被排除" },
  "analytics.byDifficulty": { en: "Results by official difficulty", zh: "按官方难度的结果" },
  "analytics.col.difficulty": { en: "Difficulty", zh: "难度" },
  "analytics.col.runs": { en: "Runs", zh: "运行数" },
  "analytics.col.resolved": { en: "Resolved", zh: "已解决" },
  "analytics.col.outcomeRate": { en: "Outcome rate", zh: "结果率" },
  "analytics.col.processValid": { en: "Process valid", zh: "过程有效" },
  "analytics.col.processRate": { en: "Process rate", zh: "过程有效率" },
  "analytics.col.inconclusive": { en: "Inconclusive", zh: "不确定" },
  "analytics.declineObserved": { en: "Observed decline interval:", zh: "观察到的下降区间:" },
  "analytics.declineSupported": { en: "statistically supported:", zh: "统计支持:" },
  "analytics.declineConfig": {
    en: "(bootstrap seed {seed}, {n} resamples)",
    zh: "（自举种子 {seed}，重采样 {n} 次）",
  },
  "analytics.effort": { en: "Agent effort by difficulty × outcome", zh: "按难度 × 结果的智能体工作量" },
  "analytics.effortNote": {
    en: "Steps and tool calls counted from the stored ATIF trajectories; a run whose trajectory cannot be read is reported as missing, never interpolated.",
    zh: "步数与工具调用数统计自存储的 ATIF 轨迹；轨迹无法读取的运行会如实报告缺失，绝不插值。",
  },
  "analytics.noRuns": { en: "No runs yet.", zh: "暂无运行。" },
  "analytics.col.outcome": { en: "Outcome", zh: "结果" },
  "analytics.col.medianSteps": { en: "Median steps", zh: "步数中位数" },
  "analytics.col.stepsRange": { en: "Steps range", zh: "步数范围" },
  "analytics.col.medianToolCalls": { en: "Median tool calls", zh: "工具调用中位数" },
  "analytics.withoutTrajectory": {
    en: " ({n} without trajectory)",
    zh: "（{n} 个缺少轨迹）",
  },
  "analytics.excludedRuns": { en: "Excluded / inconclusive runs", zh: "已排除 / 不确定的运行" },
  "analytics.cases": { en: "Representative cases", zh: "代表性案例" },
  "analytics.noCases": { en: "None yet.", zh: "暂无。" },
  "analytics.rejectedFalsePositive": { en: "rejected: false positive", zh: "已驳回：误报" },
  "analytics.humanAdjudication": { en: "human {adjudication}", zh: "人工 {adjudication}" },

  // Regressions
  "regressions.title": { en: "Regression evidence", zh: "回归证据" },
  "regressions.lede": {
    en: "Frozen validation records committed under results/. Each regression card re-evaluates the frozen slice under a newer evaluator and scores both versions against the frozen adjudicated human labels; judge-stability records repeat the semantic judge on one input. This page renders the committed files read-only — nothing is recomputed.",
    zh: "提交在 results/ 下的冻结验证记录。每张回归卡都会在较新的评估器下重新评估冻结切片，并将两个版本对照冻结的已裁定人工标注打分；评审稳定性记录则在同一输入上重复运行语义评审。本页面只读渲染已提交文件 — 不做任何重新计算。",
  },
  "regressions.loading": {
    en: "Loading committed validation records…",
    zh: "正在加载已提交的验证记录…",
  },
  "regressions.error": {
    en: "Validation records could not be loaded from the local API.",
    zh: "无法从本地 API 加载验证记录。",
  },
  "regressions.unreadable": { en: "Unreadable committed files", zh: "无法读取的已提交文件" },
  "regressions.empty": {
    en: "No committed validation records found under results/.",
    zh: "在 results/ 下未找到已提交的验证记录。",
  },
  "regressions.recorded": { en: "recorded {date}", zh: "记录于 {date}" },
  "regressions.scoreCol": { en: "Check vs. frozen human labels", zh: "对照冻结人工标注的检查项" },
  "regressions.changeCol": { en: "Change", zh: "变化" },
  "regressions.improved": { en: "improved", zh: "有改进" },
  "regressions.regressed": { en: "regressed", zh: "退步" },
  "regressions.unchanged": { en: "unchanged", zh: "不变" },
  "regressions.falsePositives": { en: "False positives (lower is better)", zh: "误报（越低越好）" },
  "regressions.detection": { en: "Invalid-process detection", zh: "有问题过程的检出" },
  "regressions.exactLocalization": { en: "Exact first-error localization", zh: "第一处错误精确定位" },
  "regressions.withinOne": { en: "Localization within one step", zh: "一步以内定位" },
  "regressions.col.task": { en: "Task", zh: "任务" },
  "regressions.col.human": { en: "Human label", zh: "人工标注" },
  "regressions.col.stored": { en: "{version} (stored)", zh: "{version}（存储）" },
  "regressions.col.reevaluated": { en: "{version} (re-evaluated)", zh: "{version}（重新评估）" },
  "regressions.col.evidence": { en: "Evidence", zh: "证据" },
  "regressions.matchesHuman": { en: "matches human", zh: "与人工一致" },
  "regressions.stepDiffers": { en: "step differs", zh: "步骤不一致" },
  "regressions.differsFromHuman": { en: "differs from human", zh: "与人工不一致" },
  "regressions.abstained": { en: "abstained", zh: "弃权" },
  "regressions.evidenceSummary": { en: "evidence", zh: "证据" },
  "regressions.protectedPaths": { en: "protected paths {status}", zh: "受保护路径 {status}" },
  "regressions.exclusions": { en: "{version} exclusions: {reasons}", zh: "{version} 排除项：{reasons}" },
  "regressions.condensedInput": { en: "condensed input", zh: "压缩输入" },
  "regressions.evaluationStatus": {
    en: "evaluation status: {stored} {storedStatus} · {reevaluated} {reevaluatedStatus}",
    zh: "评估状态：{stored} {storedStatus} · {reevaluated} {reevaluatedStatus}",
  },
  "stability.title": { en: "Judge stability", zh: "评审模型稳定性" },
  "stability.lede": {
    en: "Repeated live judge calls on the same input, recorded at the judge's real sampling settings — the run-to-run variance the semantic lane has to live with.",
    zh: "在同一输入上重复调用线上评审模型，并按其真实采样设置记录 — 这是语义通道必须承受的逐次运行方差。",
  },
  "stability.meta": { en: "{n} live repeats · recorded {date} ·", zh: "{n} 次实时重复 · 记录于 {date} ·" },
  "stability.unanimous": { en: "verdict unanimous", zh: "结论一致" },
  "stability.split": { en: "verdicts split", zh: "结论分歧" },
  "stability.firstErrorStep": { en: "first error step {steps}", zh: "第一处错误步骤 {steps}" },
  "stability.judgeLine": {
    en: "judge: {model} · effort {effort} · temperature {temperature} · top_p {topP} ·",
    zh: "评审模型：{model} · 推理强度 {effort} · 温度 {temperature} · top_p {topP} ·",
  },
  "stability.col.attempt": { en: "Attempt", zh: "尝试" },
  "stability.col.status": { en: "Status", zh: "状态" },
  "stability.col.verdict": { en: "Verdict", zh: "结论" },
  "stability.col.firstError": { en: "First error", zh: "第一处错误" },
  "stability.col.category": { en: "Category", zh: "类别" },
  "stability.col.findings": { en: "Findings", zh: "发现数" },
  "stability.col.repairs": { en: "Schema repairs", zh: "模式修复次数" },
} as const satisfies Record<string, { en: string; zh: string }>;

export type MessageKey = keyof typeof MESSAGES;

type Translate = (key: MessageKey, params?: Record<string, string | number>) => string;

type I18nValue = {
  language: Language;
  setLanguage: (language: Language) => void;
  t: Translate;
};

const I18nContext = createContext<I18nValue | null>(null);

function readStoredLanguage(): Language {
  try {
    return window.localStorage.getItem(LANGUAGE_STORAGE_KEY) === "zh" ? "zh" : "en";
  } catch {
    return "en";
  }
}

export function translate(
  language: Language,
  key: MessageKey,
  params?: Record<string, string | number>,
): string {
  let text: string = MESSAGES[key][language];
  if (params) {
    for (const [name, value] of Object.entries(params)) {
      text = text.replaceAll(`{${name}}`, String(value));
    }
  }
  return text;
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>(readStoredLanguage);
  const setLanguage = useCallback((next: Language) => {
    setLanguageState(next);
    try {
      window.localStorage.setItem(LANGUAGE_STORAGE_KEY, next);
    } catch {
      // Persistence is a convenience; the in-memory choice still applies.
    }
  }, []);
  const t = useCallback<Translate>(
    (key, params) => translate(language, key, params),
    [language],
  );
  const value = useMemo(() => ({ language, setLanguage, t }), [language, setLanguage, t]);
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

// Outside a provider (component-level tests) the default English chrome
// applies and language changes are inert.
const DEFAULT_I18N: I18nValue = {
  language: "en",
  setLanguage: () => {},
  t: (key, params) => translate("en", key, params),
};

export function useI18n(): I18nValue {
  return useContext(I18nContext) ?? DEFAULT_I18N;
}
