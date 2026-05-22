import { Link, useLocation } from "react-router-dom";
import { ThemeToggle } from "@/components/theme-toggle";
import { cn } from "@/lib/utils";

export function Navbar() {
  const { pathname } = useLocation();
  return (
    <header className="sticky top-0 z-20 border-b border-border bg-background/70 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-6">
        <Link
          to="/"
          className="font-mono text-sm font-semibold tracking-[0.3em]"
        >
          REDLINE
        </Link>
        <nav className="flex items-center gap-6">
          <Link
            to="/dashboard"
            className={cn(
              "text-sm transition-colors hover:text-foreground",
              pathname === "/dashboard"
                ? "text-foreground"
                : "text-muted-foreground",
            )}
          >
            Dashboard
          </Link>
          <ThemeToggle />
        </nav>
      </div>
    </header>
  );
}
