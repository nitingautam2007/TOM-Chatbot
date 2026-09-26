import { useEffect } from "react";
import { Outlet, useLocation } from "react-router-dom";
import Navbar from "./Navbar.jsx";
import Footer from "./Footer.jsx";

const TITLES = {
  "/": "TOM — Mental Health Support",
  "/chat": "Chat — TOM",
  "/exercises": "Exercises — TOM",
  "/screening": "Check-In — TOM",
  "/dashboard": "Dashboard — TOM",
};

export default function Layout() {
  const { pathname } = useLocation();

  useEffect(() => {
    document.title = TITLES[pathname] ?? "TOM — Mental Health Support";
    document.getElementById("main-content")?.focus();
  }, [pathname]);

  return (
    <div className="flex min-h-dvh flex-col">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:border focus:border-border focus:bg-primary focus:px-4 focus:py-2 focus:text-sm focus:font-semibold focus:text-white"
      >
        Skip to content
      </a>
      <Navbar />
      <main id="main-content" tabIndex={-1} className="flex w-full flex-1 flex-col outline-none">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}
