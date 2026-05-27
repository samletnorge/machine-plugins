export interface StubResource {
  name: string;
  description?: string;
  owner?: string | null;
  operations?: string[];
}

export interface ChatMessage {
  role: string;
  content: string;
}

export interface ChatThread {
  thread_id: string;
  agent: string;
  messages: ChatMessage[];
}

export interface ChatThreadsPayload {
  catalog: {
    agents: string[];
    runtimes: string[];
  };
  threads: ChatThread[];
}

export interface ToolDetail {
  name: string;
  description: string;
  owner: string | null;
  operations: string[];
  input_schema: {
    properties?: Record<string, { type?: string; title?: string }>;
  };
}

export interface WorkflowGraphPayload {
  name: string;
  graph: {
    nodes: Array<{ id: string; label: string; kind: string }>;
    edges: Array<{ source: string; target: string }>;
  };
}

export interface WorkflowRunsPayload {
  runs: Array<{ run_id: string; status: string }>;
}
