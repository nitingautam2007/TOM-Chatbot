import { useNavigate } from "react-router-dom";
import { ArrowRight, Lock, ShieldCheck, Languages } from "lucide-react";
import Button from "../components/common/Button.jsx";
import Card from "../components/common/Card.jsx";
import SectionLabel from "../components/common/SectionLabel.jsx";

const FEATURES = [
  {
    code: "01",
    title: "Chat",
    description: "Talk through what's on your mind — private, local, no cloud AI.",
    to: "/chat",
    cta: "Start talking",
  },
  {
    code: "02",
    title: "Check-In",
    description: "9 questions · private self-reflection · structured screening.",
    to: "/screening",
    cta: "Begin check-in",
  },
  {
    code: "03",
    title: "Dashboard",
    description:
      "Your latest check-in result and conversation activity — from this machine only.",
    to: "/dashboard",
    cta: "Open dashboard",
  },
  {
    code: "04",
    title: "Exercises",
    description:
      "Short breathing, grounding and calm practices you can do in a minute.",
    to: "/exercises",
    cta: "Try an exercise",
  },
];

const TRUST = [
  { icon: Lock, label: "No data leaves your machine" },
  { icon: ShieldCheck, label: "Runs locally" },
  { icon: Languages, label: "English · Hindi · Hinglish" },
];

export default function Home() {
  const navigate = useNavigate();

  return (
    <div className="mx-auto w-full max-w-6xl px-4 sm:px-6">
      <section className="border-b border-border py-12 sm:py-16">
        <p className="label">TOM · Mental health support</p>

        <h1 className="display hero-text mt-3 max-w-4xl text-balance text-ink">
          You don&apos;t have to figure it out alone.
        </h1>

        <p className="mt-6 max-w-xl text-base leading-relaxed text-secondary sm:text-lg">
          A private space to talk through stress, mood and everyday struggles.
          Local-first. Multilingual. Calm when you need it.
        </p>

        <div className="mt-9 flex flex-col gap-3 sm:flex-row">
          <Button
            size="lg"
            className="w-full sm:w-auto"
            onClick={() => navigate("/chat")}
          >
            Start a conversation
            <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </Button>
          <Button
            variant="secondary"
            size="lg"
            className="w-full sm:w-auto"
            onClick={() => navigate("/screening")}
          >
            Check in
          </Button>
        </div>

        <ul className="mt-10 flex flex-wrap gap-x-6 gap-y-2">
          {TRUST.map((item) => (
            <li key={item.label} className="meta flex items-center gap-1.5">
              <item.icon className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
              {item.label}
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="features-heading" className="py-12 sm:py-16">
        <div className="section-head flex flex-wrap items-end justify-between gap-4">
          <div>
            <SectionLabel>Index</SectionLabel>
            <h2 id="features-heading" className="h-display mt-1 text-2xl sm:text-3xl">
              What you can do
            </h2>
          </div>
          <span className="meta">{String(FEATURES.length).padStart(2, "0")} modules</span>
        </div>

        <div className="mt-8 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {FEATURES.map((feature) => (
            <Card key={feature.code} className="flex flex-col p-6">
              <div className="mb-4 flex items-start justify-between gap-3">
                <span className="label text-ink">{feature.code}</span>
                <span className="h-2.5 w-2.5 rounded-full bg-accent" aria-hidden="true" />
              </div>
              <h3 className="h-display text-xl">{feature.title}</h3>
              <p className="mt-3 flex-1 text-sm leading-relaxed text-secondary">
                {feature.description}
              </p>
              <Button
                variant="secondary"
                size="sm"
                className="mt-5 w-full"
                onClick={() => navigate(feature.to)}
              >
                {feature.cta}
              </Button>
            </Card>
          ))}
        </div>
      </section>

      <section className="border-t border-border py-8">
        <p className="meta max-w-2xl">
          Not a medical device. Not a diagnosis. Not a substitute for
          professional care. All inference runs locally on this machine.
        </p>
      </section>
    </div>
  );
}
