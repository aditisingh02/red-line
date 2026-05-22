import { useMemo } from "react";
import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { Threads } from "@/components/reactbits/Threads";
import { TextGenerateEffect } from "@/components/aceternity/text-generate-effect";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import { useTheme } from "@/components/theme-provider";

export default function Landing() {
  const { theme } = useTheme();
  const threadColor = useMemo<[number, number, number]>(
    () => (theme === "dark" ? [1, 1, 1] : [0, 0, 0]),
    [theme],
  );

  return (
    <div className="relative h-screen w-screen overflow-hidden">
      <Threads color={threadColor} amplitude={1} distance={0.012} />
      <div className="pointer-events-none absolute inset-0 bg-background/40" />

      <div className="absolute left-0 right-0 top-0 z-10 flex items-center justify-between px-6 py-5">
        <span className="font-mono text-sm font-semibold tracking-[0.3em]">
          REDLINE
        </span>
        <ThemeToggle />
      </div>

      <main className="relative z-10 flex h-full flex-col items-center justify-center px-6 text-center">
        <p className="mb-6 font-mono text-xs uppercase tracking-[0.4em] text-muted-foreground">
          AI agent red-teaming
        </p>
        <h1 className="text-6xl font-semibold tracking-tight sm:text-8xl">
          Redline
        </h1>
        <div className="mt-6 max-w-xl">
          <TextGenerateEffect
            className="text-base sm:text-lg"
            words="Generate adversarial payloads, run them against any agent, judge the responses, and ship a structured security report."
          />
        </div>
        <div className="mt-10 flex items-center gap-3">
          <Button asChild size="lg">
            <Link to="/dashboard">
              Open dashboard
              <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
          <Button asChild variant="outline" size="lg">
            <a
              href="https://owasp.org/www-project-top-10-for-large-language-model-applications/"
              target="_blank"
              rel="noreferrer"
            >
              OWASP LLM Top 10
            </a>
          </Button>
        </div>
        <p className="mt-16 font-mono text-[11px] text-muted-foreground">
          10 attack categories · MITRE ATLAS mapped · LLM-as-judge
        </p>
      </main>
    </div>
  );
}
