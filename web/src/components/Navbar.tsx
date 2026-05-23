import { Link, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const links = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/dashboard?tab=static", label: "Code scan" },
  { to: "/dashboard?tab=history", label: "History" },
];

export function Navbar() {
  const { pathname } = useLocation();
  return (
    <motion.header
      initial={{ y: -16, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className="sticky top-0 z-30 border-b border-border/60 bg-background/60 backdrop-blur-xl"
    >
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
        <Link to="/" className="flex items-center gap-2">
          <span className="relative inline-block h-2.5 w-2.5">
            <span className="absolute inset-0 rounded-full bg-redline-500" />
            <span className="absolute inset-0 rounded-full bg-redline-500 redline-pulse blur-[3px]" />
          </span>
          <span className="font-mono text-sm font-semibold tracking-[0.3em]">
            REDLINE
          </span>
        </Link>
        <nav className="hidden items-center gap-7 md:flex">
          {links.map((l) => (
            <Link
              key={l.to}
              to={l.to}
              className={cn(
                "text-sm transition-colors hover:text-foreground",
                pathname === l.to
                  ? "text-foreground"
                  : "text-muted-foreground",
              )}
            >
              {l.label}
            </Link>
          ))}
          <a
            href="https://github.com/anthropics/claude-code"
            target="_blank"
            rel="noreferrer"
            className="text-sm text-muted-foreground transition-colors hover:text-foreground"
          >
            Docs
          </a>
        </nav>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <Button asChild variant="outline" size="sm" className="hidden sm:inline-flex">
            <Link to="/dashboard">Sign in</Link>
          </Button>
          <Button
            asChild
            size="sm"
            className="bg-redline-600 text-white hover:bg-redline-500"
          >
            <Link to="/dashboard">Launch scan</Link>
          </Button>
        </div>
      </div>
    </motion.header>
  );
}
