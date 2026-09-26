import { useEffect, useState } from "react";
import { CalendarCheck2 } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { getPhq9State, listConversations } from "../services/api.js";
import { SCREENING_KEY } from "./Screening.jsx";
import Card from "../components/common/Card.jsx";
import EmptyState from "../components/common/EmptyState.jsx";
import SectionLabel from "../components/common/SectionLabel.jsx";
import StatusBadge from "../components/common/StatusBadge.jsx";
import Button from "../components/common/Button.jsx";

async function loadScreening() {
  const stored = localStorage.getItem(SCREENING_KEY);
  if (!stored) return null;
  try {
    return await getPhq9State(stored);
  } catch (err) {
    if (err.status === 404) {
      localStorage.removeItem(SCREENING_KEY);
      return null;
    }
    throw err;
  }
}

function formatDate(iso) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export default function Dashboard() {
  const navigate = useNavigate();
  // null = loading; sub-fields undefined = that fetch failed.
  const [data, setData] = useState(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const [convos, screening] = await Promise.allSettled([
        listConversations(),
        loadScreening(),
      ]);
      if (cancelled) return;
      setData({
        conversations: convos.status === "fulfilled" ? convos.value : undefined,
        screening: screening.status === "fulfilled" ? screening.value : undefined,
      });
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const loading = data === null;
  const convos = data?.conversations; // undefined = failed, [] = none
  const phq9 = data?.screening; // undefined = failed, null = none
  const failed = !loading && (convos === undefined || phq9 === undefined);
  const screeningCta =
    phq9 === undefined || phq9 === null
      ? "Go to check-in"
      : phq9.status === "completed"
        ? "View result"
        : "Resume check-in";

  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-10 sm:px-6 sm:py-14">
      <header className="section-head mb-8">
        <div className="flex flex-wrap items-center gap-2">
          <SectionLabel>Your check-in</SectionLabel>
          <StatusBadge tone="success">Local</StatusBadge>
        </div>
        <h1 className="display mt-2 text-2xl sm:text-3xl">Dashboard</h1>
        <p className="mt-3 max-w-xl text-sm leading-relaxed text-secondary">
          Your latest screening result and conversation activity, read from
          this machine&apos;s database. Mood, stress and sleep tracking is not
          available yet — no fake metrics.
        </p>
      </header>

      <div className="grid gap-4 sm:grid-cols-2">
        <Card className="p-5">
          <SectionLabel>Recent screening</SectionLabel>
          {loading ? (
            <p className="mt-2 text-sm text-secondary">Loading…</p>
          ) : phq9 === undefined ? (
            <p className="mt-2 text-sm text-secondary">
              Couldn&apos;t load — is the backend running?
            </p>
          ) : phq9 === null ? (
            <>
              <p className="h-display mt-2 text-lg">None yet</p>
              <p className="mt-2 text-sm text-secondary">
                Complete a PHQ-9 check-in to see your score here.
              </p>
            </>
          ) : phq9.status === "completed" ? (
            <>
              <p className="h-display mt-2 text-3xl">
                {phq9.score}
                <span className="text-lg text-secondary"> / 27</span>
              </p>
              <p className="mt-1 text-sm text-secondary">
                {phq9.severity_label} · {formatDate(phq9.completed_at)}
              </p>
            </>
          ) : (
            <>
              <p className="h-display mt-2 text-lg">In progress</p>
              <p className="mt-2 text-sm text-secondary">
                {phq9.answered_count} of {phq9.total_questions} questions
                answered.
              </p>
            </>
          )}
          <Button
            variant="secondary"
            size="sm"
            className="mt-4"
            onClick={() => navigate("/screening")}
          >
            {screeningCta}
          </Button>
        </Card>

        <Card className="p-5">
          <SectionLabel>Conversation activity</SectionLabel>
          {loading ? (
            <p className="mt-2 text-sm text-secondary">Loading…</p>
          ) : convos === undefined ? (
            <p className="mt-2 text-sm text-secondary">
              Couldn&apos;t load — is the backend running?
            </p>
          ) : convos.length === 0 ? (
            <>
              <p className="h-display mt-2 text-lg">No conversations yet</p>
              <p className="mt-2 text-sm text-secondary">
                Talk through what&apos;s on your mind. Stays on this machine.
              </p>
            </>
          ) : (
            <>
              <p className="h-display mt-2 text-3xl">
                {convos.length}
                <span className="text-lg text-secondary">
                  {" "}
                  {convos.length === 1 ? "conversation" : "conversations"}
                </span>
              </p>
              <p className="mt-1 text-sm text-secondary">
                Last activity {formatDate(convos[0].updated_at)}
                {convos[0].title ? ` · “${convos[0].title}”` : ""}
              </p>
            </>
          )}
          <Button
            variant="secondary"
            size="sm"
            className="mt-4"
            onClick={() => navigate("/chat")}
          >
            {convos && convos.length > 0 ? "Open chat" : "Start talking"}
          </Button>
        </Card>
      </div>

      <Card className="mt-6">
        <EmptyState
          icon={CalendarCheck2}
          title="No tracking yet"
          description="Check-ins and trends will appear here once mood tracking is implemented."
        />
      </Card>
      <span className="sr-only" role="status">
        {failed ? "Dashboard data failed to load" : ""}
      </span>
    </div>
  );
}
