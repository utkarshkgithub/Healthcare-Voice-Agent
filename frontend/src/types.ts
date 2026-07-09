export interface Message {
  id: number;
  type: 'user' | 'agent';
  text: string;
  timestamp: Date;
}

export type AgentStatus = 'idle' | 'listening' | 'thinking' | 'speaking';
