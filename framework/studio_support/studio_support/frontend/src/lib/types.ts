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

export interface JsonSchemaProperty {
  type?: string;
  title?: string;
  description?: string;
  enum?: Array<string | number | boolean>;
  default?: unknown;
  format?: string;
  minimum?: number;
  maximum?: number;
  example?: unknown;
  items?: {
    type?: string;
  };
}

export interface JsonSchema {
  type?: string;
  title?: string;
  description?: string;
  properties?: Record<string, JsonSchemaProperty>;
  required?: string[];
}

export interface ToolDetail {
  name: string;
  description: string;
  owner: string | null;
  operations: string[];
  input_schema: JsonSchema;
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

export interface DomainItem {
  name: string;
  owner?: string | null;
  description?: string;
  operations?: string[];
}

export interface DomainPayload {
  domain: string;
  installed: boolean;
  implemented?: boolean;
  categories: Record<string, DomainItem[]>;
  items: DomainItem[];
}
