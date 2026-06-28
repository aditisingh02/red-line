import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  AnimatePresence,
  motion,
  useReducedMotion,
  useScroll,
  useSpring,
  useTransform,
  type MotionValue,
} from "framer-motion";
import {
  ArrowRight,
  ArrowUp,
  Bot,
  Brain,
  Bug,
  CheckCircle2,
  CircleAlert,
  Code2,
  Crosshair,
  Download,
  FileSearch,
  FileText,
  Flame,
  GaugeCircle,
  Github,
  KeyRound,
  Layers,
  Plus,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  TerminalSquare,
  Wand2,
  Workflow,
  X,
  Zap,
} from "lucide-react";
import { Navbar } from "@/components/Navbar";
import { Button } from "@/components/ui/button";
import { TextGenerateEffect } from "@/components/aceternity/text-generate-effect";
import { cn } from "@/lib/utils";

/* ---------------- shared bits ---------------- */

/* Page-wide scroll position, sprung for a natural feel. Doubles as an
   orientation cue — motivated, not decoration. */
function ScrollProgress() {
  const { scrollYProgress } = useScroll();
  const scaleX = useSpring(scrollYProgress, {
    stiffness: 120,
    damping: 30,
    mass: 0.3,
  });
  return (
    <motion.div
      aria-hidden
      style={{ scaleX }}
      className="fixed inset-x-0 top-0 z-[60] h-[2.5px] origin-left bg-mint"
    />
  );
}

/* Reusable scroll-reveal: gentle rise + de-blur as the block enters the
   viewport, once. Fully lit immediately under reduced motion. */
function Reveal({
  children,
  className,
  delay = 0,
  y = 18,
}: {
  children: React.ReactNode;
  className?: string;
  delay?: number;
  y?: number;
}) {
  const reduce = useReducedMotion();
  return (
    <motion.div
      className={className}
      initial={reduce ? false : { opacity: 0, y, filter: "blur(6px)" }}
      whileInView={{ opacity: 1, y: 0, filter: "blur(0px)" }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.7, delay, ease: [0.16, 1, 0.3, 1] }}
    >
      {children}
    </motion.div>
  );
}

function SectionTitle({
  eyebrow,
  title,
  sub,
  align = "left",
}: {
  eyebrow?: string;
  title: string;
  sub?: string;
  align?: "left" | "center";
}) {
  return (
    <Reveal className={cn("max-w-2xl", align === "center" && "mx-auto text-center")}>
      {eyebrow && (
        <span className="mb-4 inline-flex items-center gap-2 rounded-full border border-redline-500/30 bg-redline-500/10 px-3 py-1 text-[11px] font-medium uppercase tracking-[0.18em] text-redline-300">
          <Flame className="h-3 w-3" />
          {eyebrow}
        </span>
      )}
      <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">
        {title}
      </h2>
      {sub && (
        <p className="mt-3 text-sm text-muted-foreground sm:text-base">{sub}</p>
      )}
    </Reveal>
  );
}

/* ---------------- hero ---------------- */

const CATEGORIES = [
  { key: "prompt_injection", label: "Prompt injection", icon: Wand2 },
  { key: "jailbreak", label: "Jailbreak", icon: KeyRound },
  { key: "role_confusion", label: "Role confusion", icon: Bot },
  { key: "data_exfiltration", label: "Data exfil", icon: FileSearch },
  { key: "boundary_violation", label: "Boundary", icon: ShieldAlert },
  { key: "adversarial_context", label: "Adversarial ctx", icon: Layers },
  { key: "chain_manipulation", label: "Chain hijack", icon: Workflow },
  { key: "hallucination_trigger", label: "Hallucination", icon: Brain },
  { key: "denial_of_service", label: "DoS", icon: GaugeCircle },
  { key: "social_engineering", label: "Social eng.", icon: Bug },
] as const;

type TermLine =
  | { kind: "cmd"; text: string }
  | { kind: "info"; text: string }
  | { kind: "vuln"; cat: string; score: string }
  | { kind: "safe"; cat: string; score: string }
  | { kind: "warn"; text: string }
  | { kind: "done"; text: string };

const TERMINAL_LINES: TermLine[] = [
  { kind: "cmd", text: "redline scan https://agent.example/chat \\\n           --categories prompt_injection,jailbreak,data_exfiltration" },
  { kind: "info", text: "loaded 47 payloads · atlas + owasp + garak" },
  { kind: "info", text: "scoring with fireworks/kimi-k2p5 · regex fallback ready" },
  { kind: "vuln", cat: "prompt_injection",   score: "0.92" },
  { kind: "vuln", cat: "jailbreak",          score: "0.78" },
  { kind: "safe", cat: "role_confusion",     score: "0.12" },
  { kind: "vuln", cat: "data_exfiltration",  score: "0.64" },
  { kind: "safe", cat: "boundary_violation", score: "0.21" },
  { kind: "warn", text: "alert · critical finding streamed to SSE listeners" },
  { kind: "done", text: "scan #a1b2c3 complete · 38 / 50 · risk = HIGH" },
];

function Terminal() {
  const [visible, setVisible] = useState(0);

  useEffect(() => {
    // line-by-line reveal, then pause and loop
    let cancelled = false;
    let timeouts: number[] = [];

    function start() {
      setVisible(0);
      TERMINAL_LINES.forEach((_, i) => {
        timeouts.push(
          window.setTimeout(() => {
            if (!cancelled) setVisible(i + 1);
          }, 350 * (i + 1)),
        );
      });
      timeouts.push(
        window.setTimeout(() => {
          if (!cancelled) start();
        }, 350 * TERMINAL_LINES.length + 6000),
      );
    }
    start();

    return () => {
      cancelled = true;
      timeouts.forEach(clearTimeout);
    };
  }, []);

  return (
    <motion.div
      initial={{ y: 30, opacity: 0 }}
      whileInView={{ y: 0, opacity: 1 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.6, ease: "easeOut" }}
      className="relative mx-auto mt-16 max-w-3xl text-left"
    >
      {/* red glow underneath */}
      <span className="absolute -inset-x-20 -inset-y-8 -z-10 rounded-[3rem] bg-redline-500/15 blur-3xl" />

      <div className="overflow-hidden rounded-2xl border border-white/10 bg-zinc-950/95 shadow-[0_30px_120px_-30px_hsl(var(--red-500)/0.6)] backdrop-blur">
        {/* title bar */}
        <div className="flex items-center justify-between border-b border-white/10 bg-zinc-900/80 px-4 py-2.5">
          <div className="flex items-center gap-1.5">
            <span className="h-3 w-3 rounded-full bg-zinc-700" />
            <span className="h-3 w-3 rounded-full bg-zinc-700" />
            <span className="h-3 w-3 rounded-full bg-zinc-700" />
          </div>
          <span className="font-mono text-[11px] text-zinc-400">
            ~/redline — zsh
          </span>
          <span className="w-12" />
        </div>

        {/* body */}
        <div className="space-y-1 px-5 py-5 font-mono text-[13px] leading-relaxed sm:text-sm">
          {TERMINAL_LINES.slice(0, visible).map((l, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: -6 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.25 }}
              className="whitespace-pre-wrap"
            >
              {l.kind === "cmd" && (
                <>
                  <span className="text-redline-400">$</span>{" "}
                  <span className="text-zinc-100">{l.text}</span>
                </>
              )}
              {l.kind === "info" && (
                <>
                  <span className="text-zinc-500">→</span>{" "}
                  <span className="text-zinc-400">{l.text}</span>
                </>
              )}
              {l.kind === "vuln" && (
                <div className="flex items-center justify-between gap-4">
                  <span>
                    <span className="text-redline-400">✓</span>{" "}
                    <span className="text-zinc-100">{l.cat}</span>
                  </span>
                  <span className="rounded bg-redline-500/15 px-2 py-0.5 text-[11px] text-redline-300">
                    VULN {l.score}
                  </span>
                </div>
              )}
              {l.kind === "safe" && (
                <div className="flex items-center justify-between gap-4">
                  <span>
                    <span className="text-mint">✓</span>{" "}
                    <span className="text-zinc-400">{l.cat}</span>
                  </span>
                  <span className="rounded bg-mint/10 px-2 py-0.5 text-[11px] text-mint">
                    SAFE {l.score}
                  </span>
                </div>
              )}
              {l.kind === "warn" && (
                <span className="text-redline-400">⚠ {l.text}</span>
              )}
              {l.kind === "done" && (
                <span className="text-zinc-100">■ {l.text}</span>
              )}
            </motion.div>
          ))}

          {/* prompt + cursor */}
          <div className="flex items-center pt-1">
            <span className="text-redline-400">$</span>
            <motion.span
              animate={{ opacity: [1, 0, 1] }}
              transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
              className="ml-2 inline-block h-4 w-2 bg-redline-400"
            />
          </div>
        </div>
      </div>
    </motion.div>
  );
}

/* Dismissible product announcement strip — scrolls away, nav sticks below it. */
function AnnounceBar() {
  const [open, setOpen] = useState(true);
  if (!open) return null;
  return (
    <div className="relative z-20 flex items-center justify-center gap-2 bg-primary px-10 py-2 text-center text-[13px] font-medium text-white">
      <Sparkles className="h-3.5 w-3.5 shrink-0" />
      <span>New: the Fireworks AI judge is live across every scan.</span>
      <Link
        to="/docs"
        className="hidden underline underline-offset-2 hover:text-white/80 sm:inline"
      >
        See what changed
      </Link>
      <button
        type="button"
        onClick={() => setOpen(false)}
        aria-label="Dismiss announcement"
        className="absolute right-3 top-1/2 -translate-y-1/2 text-white/70 transition-colors hover:text-white"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}

const HEADLINE = ["Red-team", "any", "AI", "agent"] as const;

/* Kinetic-type hero — words blur into focus over a deep electric-blue glow. */
function Hero() {
  const reduce = useReducedMotion();
  const ref = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start start", "end start"],
  });
  const y = useTransform(scrollYProgress, [0, 1], [0, -80]);
  const opacity = useTransform(scrollYProgress, [0, 0.7], [1, 0]);
  const fade = reduce ? undefined : { y, opacity };
  return (
    <section
      ref={ref}
      className="relative isolate flex min-h-[calc(100dvh-9rem)] flex-col items-center justify-center overflow-hidden px-6 pb-16 pt-12 text-center"
    >
      {/* full-bleed vertical wash: electric blue at the top → near-black at the
          bottom. Fills the whole hero so there is no dead space, and stays in
          the dark-blue family (no light-mode theme flip). */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 z-0 bg-gradient-to-b from-[#3a3aff] via-[#1a1ab0] to-[#08080f]"
      />
      {/* bright hotspot falling from the top-center */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 z-0 bg-[radial-gradient(90%_55%_at_50%_-8%,#5b5bff_0%,transparent_60%)]"
      />

      <motion.div
        style={fade}
        className="relative z-10 flex flex-col items-center"
      >
      <h1 className="font-display font-extrabold leading-[0.9] tracking-[-0.04em] text-foreground text-[clamp(2.75rem,11vw,9.5rem)]">
        {HEADLINE.map((w, i) => {
          const focal = w === "any" || w === "AI";
          return (
            <motion.span
              key={w}
              initial={reduce ? false : { opacity: 0, filter: "blur(18px)", y: 14 }}
              animate={{ opacity: 1, filter: "blur(0px)", y: 0 }}
              transition={{ duration: 0.9, delay: 0.08 * i, ease: [0.16, 1, 0.3, 1] }}
              className={cn(
                "inline-block",
                i < HEADLINE.length - 1 && "mr-[0.2em]",
                focal &&
                  "bg-gradient-to-b from-redline-200 via-redline-400 to-primary bg-clip-text text-transparent",
              )}
            >
              {w}
            </motion.span>
          );
        })}
      </h1>

      <div className="relative z-10 mt-6 max-w-xl">
        <TextGenerateEffect
          className="text-base text-white/80 sm:text-lg"
          words="Generate adversarial payloads, drive a live agent, and judge every response with an LLM."
        />
      </div>

      <motion.div
        initial={reduce ? false : { opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.55 }}
        className="relative z-10 mt-9 flex flex-wrap items-center justify-center gap-3"
      >
        <Button
          asChild
          size="lg"
          className="bg-white text-black hover:bg-white/90"
        >
          <Link to="/dashboard">
            Open dashboard
            <ArrowRight className="h-4 w-4" />
          </Link>
        </Button>
        <Button
          asChild
          variant="outline"
          size="lg"
          className="border-white/25 bg-zinc-950/40 text-white backdrop-blur hover:bg-zinc-950/60"
        >
          <Link to="/docs">Read the docs</Link>
        </Button>
      </motion.div>
      </motion.div>
    </section>
  );
}

/* The manifesto as a flat token stream so the whole sentence flows as one
   continuous paragraph (highlights live inline, mid-line, and wrap naturally). */
type Token =
  | { kind: "word"; text: string }
  | { kind: "punct"; text: string }
  | { kind: "mark"; text: string; icon: typeof ShieldCheck; tone: "blue" | "invert" };

const STATEMENT_TOKENS: Token[] = [
  ..."Redline is the only scanner where payloads, responses, and verdicts are generated, streamed, and judged live. The result?"
    .split(" ")
    .map((text): Token => ({ kind: "word", text })),
  { kind: "mark", text: "superior coverage", icon: ShieldCheck, tone: "blue" },
  { kind: "punct", text: "," },
  { kind: "mark", text: "real adversarial pressure", icon: Crosshair, tone: "invert" },
  { kind: "word", text: "and" },
  { kind: "mark", text: "reports teams read", icon: FileText, tone: "invert" },
  { kind: "punct", text: "." },
];

/* Inline highlight that flows continuously with the prose. box-decoration-clone
   keeps the rounded fill intact when a phrase wraps across two lines. */
function MarkInline({
  icon: Icon,
  tone,
  text,
}: {
  icon: typeof ShieldCheck;
  tone: "blue" | "invert";
  text: string;
}) {
  return (
    <span
      className={cn(
        "whitespace-nowrap rounded-[0.32em] px-[0.34em] py-[0.04em]",
        tone === "blue" ? "bg-primary text-white" : "bg-foreground text-background",
      )}
    >
      <span className="mr-[0.3em] inline-grid h-[0.92em] w-[0.92em] translate-y-[0.1em] place-items-center rounded-[0.24em] bg-white/20">
        <Icon className="h-[0.58em] w-[0.58em]" strokeWidth={2.4} />
      </span>
      {text}
    </span>
  );
}

/* One token of the manifesto. Opacity is driven by scroll position, so the
   sentence brightens word-by-word as it passes through the viewport — a single
   motivated read-along that guides the eye, then never repeats. Opacity only,
   so it stays on the GPU; degrades to fully-lit under reduced motion. */
function StatementToken({
  token,
  index,
  count,
  progress,
  reduce,
}: {
  token: Token;
  index: number;
  count: number;
  progress: MotionValue<number>;
  reduce: boolean;
}) {
  const start = (index / count) * 0.8;
  const opacity = useTransform(progress, [start, start + 0.18], [0.14, 1]);
  const lead = index > 0 && token.kind !== "punct" ? " " : "";
  const body =
    token.kind === "mark" ? (
      <MarkInline icon={token.icon} tone={token.tone} text={token.text} />
    ) : (
      token.text
    );
  if (reduce)
    return (
      <span>
        {lead}
        {body}
      </span>
    );
  return (
    <motion.span style={{ opacity }}>
      {lead}
      {body}
    </motion.span>
  );
}

/* Editorial manifesto — one continuous sentence, key claims marked inline,
   revealed as a scroll-linked read-along. */
function Statement() {
  const reduce = useReducedMotion() ?? false;
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start 0.82", "end 0.55"],
  });
  return (
    <section
      id="statement"
      className="relative scroll-mt-24 border-t border-border/60 bg-background"
    >
      <div ref={ref} className="mx-auto max-w-5xl px-6 py-28 sm:py-36">
        <h2 className="font-display text-3xl font-bold leading-[1.4] tracking-[-0.02em] text-foreground sm:text-5xl sm:leading-[1.36]">
          {STATEMENT_TOKENS.map((token, i) => (
            <StatementToken
              key={i}
              token={token}
              index={i}
              count={STATEMENT_TOKENS.length}
              progress={scrollYProgress}
              reduce={reduce}
            />
          ))}
        </h2>
      </div>
    </section>
  );
}

/* ---------------- 3-up feature row ---------------- */

const FEATURES_3 = [
  {
    icon: TerminalSquare,
    title: "Point at any agent",
    body: "One URL is all we need. HTTP, OpenAI, or Anthropic — Redline drives it like a real user.",
  },
  {
    icon: Layers,
    title: "Aggregate every payload",
    body: "Static library plus live feeds from MITRE ATLAS, OWASP LLM Top 10, Garak, AdvBench, and NVD.",
  },
  {
    icon: Sparkles,
    title: "Group findings by intent",
    body: "Verdicts roll up into categories so you can ship a report your security team will actually read.",
  },
];

function FeatureRow3() {
  return (
    <section className="border-t border-border/60">
      <div className="mx-auto max-w-6xl px-6 py-20">
        <div className="grid gap-10 md:grid-cols-3">
          {FEATURES_3.map((f, i) => {
            const Icon = f.icon;
            return (
              <motion.div
                key={f.title}
                initial={{ opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-80px" }}
                transition={{ duration: 0.5, delay: i * 0.08 }}
              >
                <div className="mb-3 inline-flex h-9 w-9 items-center justify-center rounded-lg bg-redline-500/10 text-redline-400">
                  <Icon className="h-4 w-4" />
                </div>
                <h3 className="text-base font-semibold">{f.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                  {f.body}
                </p>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

/* ---------------- two big cards ---------------- */

function BigCards() {
  return (
    <section>
      <div className="mx-auto grid max-w-6xl gap-6 px-6 pb-16 md:grid-cols-2">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.5 }}
          className="group relative overflow-hidden rounded-2xl border border-border bg-card p-8"
        >
          <div className="absolute -right-20 -top-20 h-64 w-64 rounded-full bg-redline-500/10 blur-3xl transition-opacity group-hover:opacity-100" />
          <h3 className="text-2xl font-semibold tracking-tight">
            Ten attack categories
          </h3>
          <p className="mt-2 max-w-md text-sm text-muted-foreground">
            From prompt injection to chain manipulation. Every test is mapped to
            MITRE ATLAS so you can defend against the techniques real
            adversaries use.
          </p>
          <div className="mt-6 flex flex-wrap gap-2 text-xs">
            {CATEGORIES.map((c) => (
              <span
                key={c.key}
                className="rounded-full border border-border bg-background/60 px-2.5 py-1 font-mono text-muted-foreground"
              >
                {c.key}
              </span>
            ))}
          </div>
          <Link
            to="/dashboard"
            className="mt-6 inline-flex items-center gap-1 text-sm text-redline-400 hover:text-redline-300"
          >
            Run a scan <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="group relative overflow-hidden rounded-2xl border border-border bg-card p-8"
        >
          <div className="absolute -left-20 -bottom-20 h-64 w-64 rounded-full bg-redline-500/10 blur-3xl" />
          <h3 className="text-2xl font-semibold tracking-tight">
            LLM-as-judge scoring
          </h3>
          <p className="mt-2 max-w-md text-sm text-muted-foreground">
            Every response is scored by a fast Fireworks-hosted judge with a regex
            fallback. Verdicts are cached by payload+response so re-runs are
            instant.
          </p>
          <div className="mt-6 grid gap-2 text-xs">
            {[
              { label: "Judge model", value: "kimi-k2p5 · Fireworks" },
              { label: "Fallback", value: "regex + keyword (offline)" },
              { label: "Cache key", value: "sha256(payload + response)" },
              { label: "Confidence", value: "low · medium · high" },
            ].map((row) => (
              <div
                key={row.label}
                className="flex items-center justify-between rounded-md border border-border bg-background/50 px-3 py-2"
              >
                <span className="text-muted-foreground">{row.label}</span>
                <span className="font-mono">{row.value}</span>
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    </section>
  );
}

/* ---------------- AI-search section ---------------- */

const SUGGESTIONS = [
  "Find me the worst jailbreaks on my customer-support bot",
  "Show prompts that exfiltrate the system message",
  "Generate payloads for boundary-violation in finance agents",
  "Which categories have I never tested against staging?",
  "Cross-reference my findings with MITRE ATLAS AML.T0051",
  "Compare prompt-injection scores week-over-week",
  "Surface payloads that beat my content-safety classifier",
  "Replay failed jailbreaks against the new model version",
  "Show me social-engineering tests I haven't run on prod",
  "Generate a report grouped by OWASP LLM Top 10",
];

function MagicSearch() {
  // Discrete-step carousel. Each suggestion dwells for STEP_MS and both the
  // bar text and the surrounding list advance on the same tick.
  const STEP_MS = 1800;
  const ITEM_H = 44; // px per row (text + gap)
  const N = SUGGESTIONS.length;

  const [current, setCurrent] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setCurrent((c) => (c + 1) % N), STEP_MS);
    return () => clearInterval(id);
  }, [N]);

  return (
    <section className="relative overflow-hidden border-t border-border/60">
      <div className="absolute inset-0 -z-10 red-wash opacity-70" />
      <div className="mx-auto max-w-4xl px-6 py-24 text-center">
        <SectionTitle
          align="center"
          eyebrow="New"
          title="Magic Payload Search"
          sub="Describe what you want to test and Redline composes the payloads, picks the categories, and queues the scan."
        />

        <Button
          asChild
          size="lg"
          className="mt-7 bg-redline-600 text-white hover:bg-redline-500"
        >
          <Link to="/dashboard">Try it</Link>
        </Button>

        {/* Scrolling suggestions with a static highlighted bar pinned in the middle */}
        <div className="relative mx-auto mt-12 h-[420px] max-w-xl">
          {/* top + bottom fade masks */}
          <div className="pointer-events-none absolute inset-x-0 top-0 z-10 h-24 bg-gradient-to-b from-background to-transparent" />
          <div className="pointer-events-none absolute inset-x-0 bottom-0 z-10 h-24 bg-gradient-to-t from-background to-transparent" />

          {/* discrete-step carousel — every suggestion is absolutely placed
              relative to `current`, snapping into position on each tick */}
          <div className="absolute inset-0 overflow-hidden">
            {SUGGESTIONS.map((s, i) => {
              let offset = i - current;
              if (offset > N / 2) offset -= N;
              if (offset < -N / 2) offset += N;
              const dist = Math.abs(offset);
              const opacity =
                offset === 0 ? 0 : Math.max(0.08, 0.55 - dist * 0.1);
              return (
                <motion.div
                  key={s}
                  animate={{ y: offset * ITEM_H, opacity }}
                  transition={{ duration: 0.4, ease: [0.32, 0.72, 0, 1] }}
                  className="absolute inset-x-0 top-1/2 -mt-3 truncate px-4 text-center text-sm text-muted-foreground"
                >
                  {s}
                </motion.div>
              );
            })}
          </div>

          {/* pinned highlighted input — same max width + horizontal center as the list */}
          <motion.div
            initial={{ opacity: 0, scale: 0.96 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="absolute inset-x-0 top-1/2 z-20 -translate-y-1/2 px-4"
          >
            <div className="relative mx-auto">
              <span className="absolute -inset-4 -z-10 rounded-full bg-redline-500/25 blur-2xl" />
              <div className="flex items-center gap-3 rounded-full border border-redline-500/50 bg-zinc-950/95 px-3 py-2.5 text-left shadow-[0_0_60px_-10px_hsl(var(--red-500)/0.8)] backdrop-blur">
                <button className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-white/5 text-zinc-300">
                  <Plus className="h-4 w-4" />
                </button>
                <span className="relative h-5 flex-1 overflow-hidden">
                  <AnimatePresence mode="popLayout" initial={false}>
                    <motion.span
                      key={current}
                      initial={{ y: 18, opacity: 0 }}
                      animate={{ y: 0, opacity: 1 }}
                      exit={{ y: -18, opacity: 0 }}
                      transition={{ duration: 0.22, ease: [0.32, 0.72, 0, 1] }}
                      className="absolute inset-0 truncate text-left text-sm text-redline-300"
                    >
                      {SUGGESTIONS[current]}
                      <motion.span
                        aria-hidden
                        animate={{ opacity: [1, 0, 1] }}
                        transition={{
                          duration: 1,
                          repeat: Infinity,
                          ease: "linear",
                        }}
                        className="ml-0.5 inline-block h-4 w-px translate-y-0.5 bg-redline-400 align-middle"
                      />
                    </motion.span>
                  </AnimatePresence>
                </span>
                <button className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-redline-600 text-white shadow-[0_0_30px_-6px_hsl(var(--red-500)/0.9)] hover:bg-redline-500">
                  <ArrowUp className="h-4 w-4" />
                </button>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}

/* ---------------- perks grid ---------------- */

const PERKS = [
  {
    icon: Zap,
    title: "Hands-free in CI",
    body: "Drop the GitHub Action into your repo and every PR gets a SARIF scan with comment summary.",
  },
  {
    icon: CheckCircle2,
    title: "Save engineering time",
    body: "Skip writing test harnesses. Redline ships 10 categories of payloads on day one.",
  },
  {
    icon: ShieldAlert,
    title: "One critical finding pays for it",
    body: "Catch a single prompt-injection in staging and you've covered the cost of the tool ten times over.",
  },
  {
    icon: FileSearch,
    title: "MITRE ATLAS mapped",
    body: "Every category maps to MITRE ATLAS tactics so your AppSec team can act on findings immediately.",
  },
  {
    icon: CircleAlert,
    title: "Real-time alerts",
    body: "Critical verdicts stream over SSE so you can intervene mid-scan instead of waiting for the report.",
  },
  {
    icon: TerminalSquare,
    title: "Local CLI",
    body: "Run a full scan offline against a mock target — no API keys required, regex fallback kicks in.",
  },
];

function Perks() {
  return (
    <section className="border-t border-border/60">
      <div className="mx-auto max-w-6xl px-6 py-24">
        <SectionTitle
          eyebrow="Perks"
          title="Perks of Redline"
          sub="Built by engineers who got tired of writing one-off red-team scripts. Made to drop into the stack you already ship with."
        />
        <div className="mt-12 grid gap-4 md:grid-cols-3">
          {PERKS.map((p, i) => {
            const Icon = p.icon;
            return (
              <motion.div
                key={p.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-80px" }}
                transition={{ duration: 0.45, delay: (i % 3) * 0.08 }}
                className="group relative overflow-hidden rounded-2xl border border-border bg-card p-6"
              >
                <div className="mb-4 inline-flex items-center gap-2 text-redline-400">
                  <Icon className="h-4 w-4" />
                  <span className="text-sm font-semibold text-foreground">
                    {p.title}
                  </span>
                </div>
                <p className="text-sm leading-relaxed text-muted-foreground">
                  {p.body}
                </p>
                <span className="pointer-events-none absolute -right-12 -bottom-12 h-32 w-32 rounded-full bg-redline-500/0 blur-2xl transition-colors group-hover:bg-redline-500/15" />
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

/* ---------------- flow diagram ---------------- */

/* Source repo (left) → Code Scanning destination (right). Dashed lines flow
   with red marker dots travelling along them — gives the impression of
   findings being piped from a PR into GitHub Code Scanning. */
function RedlineFlow() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.6 }}
      className="relative mx-auto mt-16 grid w-full max-w-xl grid-cols-[1fr_auto_1fr] items-center gap-0"
    >
      {/* LEFT — source repo card */}
      <div className="relative">
        <span className="absolute inset-0 -z-10 rounded-2xl bg-redline-500/20 blur-3xl" />
        <div className="ml-auto w-[180px] rounded-2xl border border-white/10 bg-zinc-900/90 p-4 shadow-[0_15px_40px_-10px_rgba(0,0,0,0.6)]">
          <div className="mb-3 flex items-center gap-2">
            <Github className="h-4 w-4 text-zinc-200" />
            <span className="font-mono text-[11px] text-zinc-400">
              owner/repo
            </span>
          </div>
          {[
            "agent/handler.py",
            "agent/prompt.md",
            "tests/red_team.py",
          ].map((f) => (
            <div
              key={f}
              className="mb-1.5 flex items-center gap-2 rounded-md border border-white/5 bg-white/[0.02] px-2 py-1.5 text-[11px]"
            >
              <Code2 className="h-3 w-3 text-redline-400" />
              <span className="truncate font-mono text-zinc-300">{f}</span>
            </div>
          ))}
          <div className="mt-3 flex items-center justify-between text-[10px] text-zinc-400">
            <span className="font-mono">PR #42</span>
            <span className="inline-flex items-center gap-1 rounded-full bg-redline-500/15 px-2 py-0.5 font-mono text-redline-300">
              <span className="h-1 w-1 animate-pulse rounded-full bg-redline-500" />
              scanning
            </span>
          </div>
        </div>
      </div>

      {/* MIDDLE — dashed connecting lines */}
      <FlowLines />

      {/* RIGHT — destination findings card */}
      <div className="relative">
        <span className="absolute inset-0 -z-10 rounded-2xl bg-redline-500/20 blur-3xl" />
        <div className="mr-auto w-[180px] rounded-2xl border border-white/10 bg-zinc-900/90 p-4 shadow-[0_15px_40px_-10px_rgba(0,0,0,0.6)]">
          <div className="mb-3 flex items-center justify-between">
            <span className="font-mono text-[11px] text-zinc-400">
              code scanning
            </span>
            <span className="font-mono text-[10px] text-redline-300">3</span>
          </div>
          {[
            { sev: "critical", label: "prompt_injection" },
            { sev: "high", label: "jailbreak" },
            { sev: "high", label: "data_exfil" },
          ].map((f) => (
            <div
              key={f.label}
              className="mb-1.5 flex items-center justify-between rounded-md border border-white/5 bg-white/[0.02] px-2 py-1.5 text-[11px]"
            >
              <span className="truncate font-mono text-zinc-300">
                {f.label}
              </span>
              <span
                className={cn(
                  "rounded-full px-1.5 py-0.5 font-mono text-[9px]",
                  f.sev === "critical"
                    ? "bg-redline-500/20 text-redline-300"
                    : "bg-redline-500/10 text-redline-400",
                )}
              >
                {f.sev}
              </span>
            </div>
          ))}
          <div className="mt-3 inline-flex items-center gap-1 rounded-full bg-redline-500/15 px-2 py-0.5 font-mono text-[10px] text-redline-300">
            <ShieldAlert className="h-3 w-3" />
            SARIF uploaded
          </div>
        </div>
      </div>
    </motion.div>
  );
}

function FlowLines() {
  /* Three dashed paths whose dashes themselves flow left→right by
     animating stroke-dashoffset on each line. */
  const rows = [
    { y: 26, delay: 0 },
    { y: 60, delay: 0.4 },
    { y: 94, delay: 0.8 },
  ];

  return (
    <div className="relative h-[140px] w-[120px]">
      <svg
        viewBox="0 0 120 140"
        className="absolute inset-0 h-full w-full"
        aria-hidden
      >
        <defs>
          <linearGradient id="flowFade" x1="0" x2="1">
            <stop offset="0%" stopColor="hsl(var(--red-500))" stopOpacity="0.1" />
            <stop offset="50%" stopColor="hsl(var(--red-500))" stopOpacity="0.7" />
            <stop offset="100%" stopColor="hsl(var(--red-500))" stopOpacity="0.1" />
          </linearGradient>
        </defs>

        {rows.map((r) => (
          <motion.line
            key={r.y}
            x1="0"
            x2="120"
            y1={r.y}
            y2={r.y}
            stroke="url(#flowFade)"
            strokeWidth="1.5"
            strokeDasharray="6 6"
            animate={{ strokeDashoffset: [12, 0] }}
            transition={{
              duration: 0.9,
              ease: "linear",
              repeat: Infinity,
              delay: r.delay,
            }}
          />
        ))}
      </svg>
    </div>
  );
}

/* ---------------- connect any repo ---------------- */

type ConnectPath = {
  tag: string;
  title: string;
  body: string;
  icon: typeof TerminalSquare;
  code: string;
  language: "bash" | "yaml";
  ctaHref?: string;
  ctaLabel?: string;
};

const CONNECT_PATHS: ConnectPath[] = [
  {
    tag: "One-off · 30 sec",
    title: "CLI",
    icon: TerminalSquare,
    body: "Shallow-clones the repo, runs the scanner, exits 1 on any CRITICAL finding. Add --token for private repos.",
    language: "bash",
    code:
      "python cli.py scan-repo \\\n  https://github.com/owner/repo \\\n  --sarif out.sarif --json",
  },
  {
    tag: "Scripted · HTTP",
    title: "API",
    icon: Code2,
    body: "Same scan engine behind a POST endpoint. Works from any script, CI runner, or app. JSON or SARIF response.",
    language: "bash",
    code:
      "curl -X POST :8000/api/scan-repo \\\n  -d '{\"repo_url\":\"https://github.com/o/r\"}' \\\n  -H 'content-type: application/json'",
  },
  {
    tag: "Per-PR · no server",
    title: "GitHub Action",
    icon: Workflow,
    body: "Drop one workflow file into the target repo. SARIF uploads to Code Scanning, PR comment is posted, job fails on CRITICAL.",
    language: "yaml",
    code:
      "- uses: actions/checkout@v4\n- uses: your-org/redline-action@v1\n  with: { fail-on: critical }",
    ctaHref: "https://github.com/",
    ctaLabel: "Install action",
  },
  {
    tag: "Multi-repo · central",
    title: "GitHub App",
    icon: Github,
    body: "Install once on an org. Every PR fires a webhook to your Redline instance; verified by HMAC, comment posted back automatically.",
    language: "bash",
    code:
      "GITHUB_TOKEN=...\nGITHUB_WEBHOOK_SECRET=...\n# point webhook → /api/github/webhook",
    ctaLabel: "Setup guide",
  },
];

function ConnectAnyRepo() {
  return (
    <section className="relative overflow-hidden border-t border-border/60">
      <div className="absolute inset-x-0 top-0 -z-10 h-64 bg-gradient-to-b from-redline-500/5 to-transparent" />
      <div className="mx-auto max-w-6xl px-6 py-24">
        <SectionTitle
          align="center"
          eyebrow="Start"
          title="Connect any repo"
          sub="Four supported paths, pick by how often you want a scan and whether you have a server. All four hit the same scan engine and ship the same SARIF."
        />

        <div className="mt-12 grid gap-4 md:grid-cols-2">
          {CONNECT_PATHS.map((p, i) => {
            const Icon = p.icon;
            return (
              <motion.div
                key={p.title}
                initial={{ opacity: 0, y: 24 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-80px" }}
                transition={{ duration: 0.45, delay: (i % 2) * 0.08 }}
                className="group relative flex flex-col overflow-hidden rounded-2xl border border-border bg-card/80 p-6 backdrop-blur"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <span className="flex h-10 w-10 items-center justify-center rounded-xl border border-redline-500/30 bg-redline-500/10 text-redline-300">
                      <Icon className="h-5 w-5" />
                    </span>
                    <div>
                      <h3 className="text-lg font-semibold tracking-tight">{p.title}</h3>
                      <span className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
                        {p.tag}
                      </span>
                    </div>
                  </div>
                  <span className="rounded-full border border-border bg-background/40 px-2 py-0.5 text-[10px] font-mono text-muted-foreground">
                    {p.language}
                  </span>
                </div>

                <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
                  {p.body}
                </p>

                <pre className="mt-4 overflow-x-auto rounded-xl border border-white/5 bg-zinc-950/80 px-4 py-3 text-[12px] leading-relaxed text-zinc-200">
                  <code className="font-mono whitespace-pre">{p.code}</code>
                </pre>

                {p.ctaLabel && (
                  <div className="mt-4">
                    {p.ctaHref ? (
                      <a
                        href={p.ctaHref}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 text-sm font-medium text-redline-300 hover:text-redline-200"
                      >
                        {p.ctaLabel}
                        <ArrowRight className="h-3.5 w-3.5" />
                      </a>
                    ) : (
                      <Link
                        to="/dashboard"
                        className="inline-flex items-center gap-1 text-sm font-medium text-redline-300 hover:text-redline-200"
                      >
                        {p.ctaLabel}
                        <ArrowRight className="h-3.5 w-3.5" />
                      </Link>
                    )}
                  </div>
                )}

                <span className="pointer-events-none absolute -right-16 -bottom-16 h-40 w-40 rounded-full bg-redline-500/0 blur-3xl transition-colors group-hover:bg-redline-500/15" />
              </motion.div>
            );
          })}
        </div>

        <p className="mt-10 text-center text-xs text-muted-foreground">
          Detailed setup &amp; auth notes in the{" "}
          <a
            href="https://github.com/"
            target="_blank"
            rel="noreferrer"
            className="underline decoration-redline-500/40 underline-offset-4 hover:text-foreground"
          >
            README
          </a>
          .
        </p>
      </div>
    </section>
  );
}

/* ---------------- bottom CTA with funnel beam ---------------- */

function ExtensionCTA() {
  return (
    <section className="relative overflow-hidden border-t border-border/60">
      <svg
        viewBox="0 0 1440 700"
        className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-full w-full"
        preserveAspectRatio="xMidYMid slice"
        aria-hidden
      >
        <defs>
          <linearGradient id="beam" x1="50%" y1="0%" x2="50%" y2="100%">
            <stop offset="0%" stopColor="hsl(240, 100%, 62%)" stopOpacity="0.45" />
            <stop offset="100%" stopColor="hsl(240, 100%, 62%)" stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d="M720 0 L1100 700 L340 700 Z" fill="url(#beam)" />
        <path
          d="M720 0 L920 700 L520 700 Z"
          fill="url(#beam)"
          opacity="0.6"
        />
      </svg>

      <div className="mx-auto max-w-4xl px-6 py-24 text-center">
        <Reveal>
          <span className="inline-flex items-center gap-2 rounded-full border border-border bg-card/80 px-3 py-1 text-xs font-medium text-muted-foreground backdrop-blur">
            1.2k stars · MIT licensed
          </span>
          <h2 className="mt-6 text-4xl font-semibold tracking-tight sm:text-5xl">
            Redline GitHub Action
          </h2>
          <p className="mx-auto mt-3 max-w-xl text-sm text-muted-foreground sm:text-base">
            Drop the action into{" "}
            <span className="font-mono">.github/workflows</span> and every PR
            ships through the static scanner with SARIF uploaded to Code
            Scanning.
          </p>
          <div className="mt-7 flex flex-wrap items-center justify-center gap-3">
            <Button asChild size="lg" className="bg-redline-600 text-white hover:bg-redline-500">
              <a href="https://github.com/" target="_blank" rel="noreferrer">
                Install action
                <Download className="h-4 w-4" />
              </a>
            </Button>
            <Button asChild variant="outline" size="lg">
              <Link to="/dashboard">Open dashboard</Link>
            </Button>
          </div>
        </Reveal>

        <RedlineFlow />
      </div>
    </section>
  );
}

/* ---------------- footer ---------------- */

function Footer() {
  return (
    <footer className="border-t border-border/60">
      <Reveal className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-3 px-6 py-8 text-xs text-muted-foreground sm:flex-row">
        <div className="flex items-center gap-2 font-mono tracking-[0.3em]">
          <span className="h-1.5 w-1.5 rounded-full bg-redline-500" />
          REDLINE · v0.1
        </div>
        <div className="flex items-center gap-4">
          <Link to="/docs" className="hover:text-foreground">Docs</Link>
          <a href="#" className="hover:text-foreground">GitHub</a>
          <a
            href="https://owasp.org/www-project-top-10-for-large-language-model-applications/"
            target="_blank"
            rel="noreferrer"
            className="hover:text-foreground"
          >
            OWASP
          </a>
        </div>
      </Reveal>
    </footer>
  );
}

export default function Landing() {
  return (
    <div className="dot-grid relative min-h-screen overflow-hidden bg-background">
      <ScrollProgress />
      <AnnounceBar />
      <Navbar />
      <Hero />
      <Statement />
      <section className="border-t border-border/60 px-6 pb-12">
        <Terminal />
      </section>
      <FeatureRow3 />
      <BigCards />
      <MagicSearch />
      <Perks />
      <ConnectAnyRepo />
      <ExtensionCTA />
      <Footer />
    </div>
  );
}
