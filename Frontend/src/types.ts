import type { CrisisResource } from './safety.ts'

export type Mood = 1 | 2 | 3 | 4 | 5
export type RiskLevel = 'low' | 'high'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  text: string
  timestamp: Date
  visible: boolean
  riskLevel?: RiskLevel
  intent?: string
  confidence?: number
  source?: string
  resources?: CrisisResource[]
  error?: boolean
  retryText?: string
  offline?: boolean
}

export interface BotReply {
  text: string
  intent?: string
  confidence?: number
  source?: string
  riskLevel?: RiskLevel
  resources?: CrisisResource[]
  offline?: boolean
}

export interface SupportResource {
  title: string
  desc: string
  icon: string
  tag: string
  tagColor: string
  href?: string
}
