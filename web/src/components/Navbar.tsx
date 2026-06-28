import { useEffect, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import { Github, LogOut } from "lucide-react";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { loginWithGitHub, useAuth } from "@/lib/auth";

const links = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/dashboard?tab=static", label: "Code scan" },
  { to: "/dashboard?tab=history", label: "History" },
];

function UserMenu() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  if (!user) return null;
  const initials = (user.name || user.github_login || "?")
    .split(/\s+/)
    .map((s) => s[0])
    .filter(Boolean)
    .slice(0, 2)
    .join("")
    .toUpperCase();

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 rounded-full border border-border bg-card/60 px-2 py-1 text-sm transition-colors hover:bg-card"
        aria-haspopup="menu"
        aria-expanded={open}
      >
        {user.avatar_url ? (
          <img
            src={user.avatar_url}
            alt=""
            className="h-6 w-6 rounded-full"
          />
        ) : (
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-redline-500/20 text-[10px] font-semibold text-redline-300">
            {initials || "?"}
          </span>
        )}
        <span className="hidden font-mono text-xs text-muted-foreground sm:inline">
          {user.github_login}
        </span>
      </button>
      {open && (
        <div
          role="menu"
          className="absolute right-0 mt-2 w-56 overflow-hidden rounded-xl border border-border bg-card shadow-xl"
        >
          <div className="border-b border-border px-3 py-2 text-xs">
            <div className="font-medium text-foreground">
              {user.name || user.github_login}
            </div>
            {user.email && (
              <div className="truncate text-muted-foreground">{user.email}</div>
            )}
          </div>
          <button
            type="button"
            onClick={() => void logout()}
            className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-foreground hover:bg-redline-500/10"
            role="menuitem"
          >
            <LogOut className="h-4 w-4" />
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}

export function Navbar() {
  const { pathname } = useLocation();
  const { user, loading, authEnabled } = useAuth();

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
          <Link
            to="/docs"
            className={cn(
              "text-sm transition-colors hover:text-foreground",
              pathname === "/docs" ? "text-foreground" : "text-muted-foreground",
            )}
          >
            Docs
          </Link>
        </nav>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          {loading ? (
            <span className="hidden h-8 w-20 animate-pulse rounded-md bg-card/60 sm:inline-block" />
          ) : user ? (
            <UserMenu />
          ) : authEnabled ? (
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => loginWithGitHub()}
              className="hidden gap-2 sm:inline-flex"
            >
              <Github className="h-4 w-4" />
              Sign in with GitHub
            </Button>
          ) : (
            <Button
              asChild
              variant="outline"
              size="sm"
              className="hidden sm:inline-flex"
            >
              <Link to="/dashboard">Open dashboard</Link>
            </Button>
          )}
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
