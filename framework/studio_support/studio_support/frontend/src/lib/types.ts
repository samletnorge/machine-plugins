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

export interface StudioContextSummary {
  tenant_slug: string;
  tenant_name: string;
  project_slug: string;
  project_name: string;
  environment_name: string;
  environment_status: string;
}

export interface RuntimeAttachmentSummary {
  context: {
    tenant_id: string;
    project_id: string;
    environment_id: string;
  };
  status: 'attached' | 'attaching' | 'failed' | 'detached';
  machine_name: string | null;
  attached_at: string | null;
  error: string | null;
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
