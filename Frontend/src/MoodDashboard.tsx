import { useEffect, useState } from 'react'
import { API_BASE_URL } from './api'

interface MoodStatsData {
  total: number
  counts: Record<string, number>
  recent: Array<{ time: string; label: string }>
  top_emotion: string
  streak_days: number
}

const EMOTION_META: Record<
  string,
  { label: string; emoji: string; color: string; bg: string; border: string }
> = {
  anxiety: {
    label: 'Anxiety',
    emoji: '😰',
    color: '#0284c7',
    bg: 'rgba(2, 132, 199, 0.1)',
    border: 'rgba(2, 132, 199, 0.25)',
  },
  sadness: {
    label: 'Sadness & Low',
    emoji: '😔',
    color: '#6366f1',
    bg: 'rgba(99, 102, 241, 0.1)',
    border: 'rgba(99, 102, 241, 0.25)',
  },
  exam_stress: {
    label: 'Exam Stress',
    emoji: '📚',
    color: '#ea580c',
    bg: 'rgba(234, 88, 12, 0.1)',
    border: 'rgba(234, 88, 12, 0.25)',
  },
  family_pressure: {
    label: 'Family Pressure',
    emoji: '🏠',
    color: '#b45309',
    bg: 'rgba(180, 83, 9, 0.1)',
    border: 'rgba(180, 83, 9, 0.25)',
  },
  loneliness: {
    label: 'Loneliness',
    emoji: '😶',
    color: '#0d9488',
    bg: 'rgba(13, 148, 136, 0.1)',
    border: 'rgba(13, 148, 136, 0.25)',
  },
  great: {
    label: 'Great',
    emoji: '😊',
    color: '#16a34a',
    bg: 'rgba(22, 163, 74, 0.1)',
    border: 'rgba(22, 163, 74, 0.25)',
  },
  good: {
    label: 'Good',
    emoji: '🙂',
    color: '#65a30d',
    bg: 'rgba(101, 163, 13, 0.1)',
    border: 'rgba(101, 163, 13, 0.25)',
  },
  okay: {
    label: 'Okay',
    emoji: '😐',
    color: '#0284c7',
    bg: 'rgba(2, 132, 199, 0.1)',
    border: 'rgba(2, 132, 199, 0.25)',
  },
  low: {
    label: 'Low',
    emoji: '😕',
    color: '#d97706',
    bg: 'rgba(217, 119, 6, 0.1)',
    border: 'rgba(217, 119, 6, 0.25)',
  },
  struggling: {
    label: 'Struggling',
    emoji: '😔',
    color: '#dc2626',
    bg: 'rgba(220, 38, 38, 0.1)',
    border: 'rgba(220, 38, 38, 0.25)',
  },
}

export default function MoodDashboard({
  onNavigateChat,
}: {
  onNavigateChat: (prompt?: string) => void
}) {
  const [data, setData] = useState<MoodStatsData | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchStats = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE_URL}/api/mood/stats`)
      if (res.ok) {
        const json = await res.json()
        setData(json)
      }
    } catch {
      // Fallback
    } finally {
      setLoading(false)
    }
  }

  const handleResetStats = async () => {
    if (!window.confirm('Clear all recorded mood history?')) return
    setLoading(true)
    try {
      await fetch(`${API_BASE_URL}/api/mood/reset`, { method: 'POST' })
      await fetchStats()
    } catch {
      // Fallback
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void fetchStats()
  }, [])

  const totalLogs = data?.total || 0
  const counts = data?.counts || {}
  const topEmotion = (data?.top_emotion || 'none').toLowerCase()
  const topMeta =
    totalLogs > 0 && EMOTION_META[topEmotion]
      ? EMOTION_META[topEmotion]
      : {
          label: totalLogs > 0 ? topEmotion.replace('_', ' ') : 'None yet',
          emoji: totalLogs > 0 ? '💭' : '🌱',
          color: '#5a7f5a',
          bg: 'rgba(90,127,90,0.1)',
          border: 'rgba(90,127,90,0.2)',
        }

  return (
    <div className="flex-1 overflow-y-auto px-4 md:px-8 py-6">
      <div className="max-w-4xl mx-auto w-full space-y-6">
        
        {/* Dashboard Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-sage-900/10">
          <div>
            <h2
              className="text-sage-800 text-2xl font-normal leading-tight"
              style={{ fontFamily: 'var(--font-display)' }}
            >
              📊 Mood & Wellbeing Dashboard
            </h2>
            <p className="text-xs text-sage-500 mt-1">
              Private, local analytics derived from your check-ins and conversation states.
            </p>
          </div>

          <div className="flex items-center gap-2 self-start sm:self-auto">
            <button
              type="button"
              onClick={() => void fetchStats()}
              disabled={loading}
              className="px-3.5 py-1.5 rounded-xl text-xs font-medium text-sage-700 bg-white border border-sage-900/15 shadow-2xs hover:bg-sage-50 transition-all flex items-center gap-1.5"
            >
              <span className={loading ? 'animate-spin' : ''}>🔄</span>
              {loading ? 'Refreshing...' : 'Refresh Stats'}
            </button>
            {totalLogs > 0 && (
              <button
                type="button"
                onClick={() => void handleResetStats()}
                disabled={loading}
                className="px-3 py-1.5 rounded-xl text-xs font-medium text-red-700 bg-red-50 hover:bg-red-100 border border-red-200 transition-all flex items-center gap-1"
                title="Reset mood tracking history"
              >
                <span>🗑️</span>
                <span>Reset</span>
              </button>
            )}
          </div>
        </div>

        {/* 4 Stat Overview Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="p-4 rounded-2xl bg-white border border-sage-900/10 shadow-xs">
            <span className="text-[11px] font-semibold text-sage-500 uppercase tracking-wider">
              Total Logs
            </span>
            <p className="text-2xl font-bold text-sage-800 mt-1">{totalLogs}</p>
            <span className="text-[10px] text-sage-400">Recorded check-ins</span>
          </div>

          <div className="p-4 rounded-2xl bg-white border border-sage-900/10 shadow-xs">
            <span className="text-[11px] font-semibold text-sage-500 uppercase tracking-wider">
              Frequent State
            </span>
            <div className="flex items-center gap-1.5 mt-1">
              <span className="text-lg">{topMeta.emoji}</span>
              <p className="text-sm font-bold capitalize text-sage-800 truncate">{topMeta.label}</p>
            </div>
            <span className="text-[10px] text-sage-400">Most frequent pattern</span>
          </div>

          <div className="p-4 rounded-2xl bg-white border border-sage-900/10 shadow-xs">
            <span className="text-[11px] font-semibold text-sage-500 uppercase tracking-wider">
              Active Days
            </span>
            <p className="text-2xl font-bold text-sage-800 mt-1">{totalLogs > 0 ? (data?.streak_days ?? 0) : 0}</p>
            <span className="text-[10px] text-sage-400">Days journaling</span>
          </div>

          <div className="p-4 rounded-2xl bg-white border border-sage-900/10 shadow-xs">
            <span className="text-[11px] font-semibold text-sage-500 uppercase tracking-wider">
              Privacy Status
            </span>
            <div className="flex items-center gap-1.5 mt-1">
              <span className="w-2 h-2 rounded-full bg-emerald-500 shadow-xs" />
              <p className="text-sm font-bold text-emerald-700">100% Offline</p>
            </div>
            <span className="text-[10px] text-sage-400">No data transmitted</span>
          </div>
        </div>

        {/* Emotional Distribution Breakdown */}
        <div className="p-5 rounded-3xl bg-white border border-sage-900/10 shadow-xs">
          <h3 className="text-sm font-semibold text-sage-800 mb-1">
            State & Mood Breakdown
          </h3>
          <p className="text-[11px] text-sage-500 mb-4">
            Distribution of emotions identified by your local Theory of Mind classifier and manual check-ins.
          </p>

          {Object.keys(counts).length === 0 ? (
            <p className="text-xs text-sage-400 py-6 text-center">
              No mood check-ins recorded yet. Send a message to start logging!
            </p>
          ) : (
            <div className="space-y-3">
              {Object.entries(counts)
                .sort(([, a], [, b]) => b - a)
                .map(([label, count]) => {
                  const meta = EMOTION_META[label.toLowerCase()] || {
                    label: label.replace('_', ' '),
                    emoji: '💭',
                    color: '#5a7f5a',
                    bg: 'rgba(90,127,90,0.1)',
                    border: 'rgba(90,127,90,0.2)',
                  }
                  const pct = totalLogs > 0 ? Math.round((count / totalLogs) * 100) : 0

                  return (
                    <div key={label} className="space-y-1">
                      <div className="flex items-center justify-between text-xs">
                        <span className="flex items-center gap-1.5 font-medium text-sage-800">
                          <span>{meta.emoji}</span>
                          <span className="capitalize">{meta.label}</span>
                        </span>
                        <span className="text-sage-500 font-medium">
                          {count} ({pct}%)
                        </span>
                      </div>
                      <div className="w-full h-2 rounded-full bg-sage-100 overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all duration-500"
                          style={{
                            width: `${pct}%`,
                            backgroundColor: meta.color,
                          }}
                        />
                      </div>
                    </div>
                  )
                })}
            </div>
          )}
        </div>

        {/* Insights & Recommendations Box */}
        <div
          className="p-5 rounded-3xl"
          style={{
            background: 'linear-gradient(145deg, rgba(90,127,90,0.08) 0%, rgba(61,122,142,0.08) 100%)',
            border: '1px solid rgba(90,127,90,0.18)',
          }}
        >
          <div className="flex items-start gap-3">
            <span className="text-2xl">🌱</span>
            <div className="flex-1">
              <h4 className="text-sm font-semibold text-sage-800">
                Reflection & Coping Insights
              </h4>
              <p className="text-xs text-sage-600 leading-relaxed mt-1">
                {topEmotion.includes('anxiety') || topEmotion.includes('exam')
                  ? 'Your check-ins show stress or anxiety as a frequent theme. Consider scheduling 5-minute breathing pauses between study sessions.'
                  : topEmotion.includes('loneliness')
                    ? 'Feelings of isolation can be heavy. Even small steps, like sharing a moment with a peer or journaling, can bring comfort.'
                    : 'Remember that emotions fluctuate naturally. Taking time to check in with yourself is a powerful step towards wellbeing.'}
              </p>
              
              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => onNavigateChat('Breathing exercise')}
                  className="px-3 py-1.5 rounded-xl text-[11px] font-semibold text-sage-800 bg-white border border-sage-900/15 shadow-2xs hover:bg-sage-50 transition-all"
                >
                  🌬️ Try Box Breathing
                </button>
                <button
                  type="button"
                  onClick={() => onNavigateChat('Grounding technique')}
                  className="px-3 py-1.5 rounded-xl text-[11px] font-semibold text-sage-800 bg-white border border-sage-900/15 shadow-2xs hover:bg-sage-50 transition-all"
                >
                  ✋ 5-4-3-2-1 Grounding
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Recent Activity Timeline Feed */}
        <div className="p-5 rounded-3xl bg-white border border-sage-900/10 shadow-xs">
          <h3 className="text-sm font-semibold text-sage-800 mb-3">
            Recent Activity History (Latest 30)
          </h3>

          {(!data?.recent || data.recent.length === 0) ? (
            <p className="text-xs text-sage-400 py-4 text-center">No recent records found.</p>
          ) : (
            <div className="divide-y divide-sage-100 max-h-80 overflow-y-auto">
              {data.recent.map((item, idx) => {
                const meta = EMOTION_META[item.label.toLowerCase()] || {
                  label: item.label.replace('_', ' '),
                  emoji: '💭',
                  color: '#5a7f5a',
                  bg: 'rgba(90,127,90,0.1)',
                  border: 'rgba(90,127,90,0.2)',
                }

                return (
                  <div key={idx} className="py-2.5 flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <span className="text-base">{meta.emoji}</span>
                      <span className="font-medium text-sage-800 capitalize">
                        {meta.label}
                      </span>
                    </div>
                    <span className="text-[11px] text-sage-400 font-mono">
                      {item.time}
                    </span>
                  </div>
                )
              })}
            </div>
          )}
        </div>

      </div>
    </div>
  )
}
