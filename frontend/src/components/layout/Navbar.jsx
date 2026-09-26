import { useRef, useState } from "react";
import { NavLink, Link } from "react-router-dom";
import { Menu, X } from "lucide-react";
import StatusBadge from "../common/StatusBadge.jsx";
import Button from "../common/Button.jsx";

const LINKS = [
  { to: "/", label: "Home" },
  { to: "/chat", label: "Chat" },
  { to: "/exercises", label: "Exercises" },
  { to: "/screening", label: "Check-In" },
  { to: "/dashboard", label: "Dashboard" },
];

function Logo() {
  return (
    <Link to="/" className="flex items-center gap-2.5" aria-label="TOM home">
      <span
        className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-lg font-bold text-white"
        aria-hidden="true"
      >
        T
      </span>
      <span className="flex flex-col leading-none">
        <span className="display text-lg text-ink">TOM</span>
        <span className="meta mt-0.5">Mental Health Support</span>
      </span>
    </Link>
  );
}

export default function Navbar() {
  const [open, setOpen] = useState(false);
  const toggleRef = useRef(null);

  function closeMenu(refocus = false) {
    setOpen(false);
    if (refocus) toggleRef.current?.focus();
  }

  return (
    <header
      className="sticky top-0 z-40 border-b border-border bg-surface"
      onKeyDown={(e) => {
        if (e.key === "Escape" && open) closeMenu(true);
      }}
    >
      <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between px-4 sm:px-6">
        <Logo />

        <div className="hidden items-center gap-3 sm:flex">
          <nav className="flex items-center gap-1" aria-label="Primary">
            {LINKS.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                end={link.to === "/"}
                className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
              >
                {link.label}
              </NavLink>
            ))}
          </nav>
          <StatusBadge tone="success">Local</StatusBadge>
        </div>

        <Button
          ref={toggleRef}
          variant="secondary"
          size="sm"
          className="h-11 w-11 px-0! sm:hidden"
          onClick={() => (open ? closeMenu(true) : setOpen(true))}
          aria-expanded={open}
          aria-controls={open ? "mobile-nav" : undefined}
          aria-label={open ? "Close menu" : "Open menu"}
        >
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </Button>
      </div>

      {open ? (
        <nav
          id="mobile-nav"
          className="border-t border-border bg-surface px-4 py-3 sm:hidden"
          aria-label="Mobile"
        >
          <div className="mb-3">
            <StatusBadge tone="success">Local</StatusBadge>
          </div>
          <ul className="flex flex-col gap-1">
            {LINKS.map((link) => (
              <li key={link.to}>
                <NavLink
                  to={link.to}
                  end={link.to === "/"}
                  onClick={() => {
                    setOpen(false);
                    toggleRef.current?.focus();
                  }}
                  className={({ isActive }) =>
                    `nav-link block py-3.5 ${isActive ? "active" : ""}`
                  }
                >
                  {link.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
      ) : null}
    </header>
  );
}
