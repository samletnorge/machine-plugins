// Typed client for the Studio control-plane JSON API (mounted at /_studio/api).
import { API_ROOT } from "$lib/auth";

export { API_ROOT };

export class ApiError extends Error {
	status: number;

	constructor(status: number, message: string) {
		super(message);
		this.name = "ApiError";
		this.status = status;
	}
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
	const response = await fetch(`${API_ROOT}${path}`, {
		credentials: "include",
		headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
		...init,
	});
	if (!response.ok) {
		throw new ApiError(response.status, `${init?.method ?? "GET"} ${path} → ${response.status}`);
	}
	if (response.status === 204) return undefined as T;
	return (await response.json()) as T;
}

export interface RuntimeItem {
	name: string;
	description: string;
	owner: string;
	operations: string[];
}

export interface PluginManifest {
	name: string;
	description?: string;
	version?: string;
	path?: string;
	[key: string]: unknown;
}

export interface ContextRecord {
	tenant_slug: string;
	tenant_name: string;
	project_slug: string;
	project_name: string;
	environment_name: string;
	environment_status: string;
	environment_connection_kind: string | null;
	environment_connection_ref: string | null;
}

export interface AttachmentRecord {
	status: string;
	error?: string | null;
	machine_name?: string | null;
}

export interface ContextResponse {
	context: ContextRecord;
	attachment: AttachmentRecord;
}

export interface Tenant {
	id: string;
	slug: string;
	name: string;
}

export interface Project {
	id: string;
	tenant_id: string;
	slug: string;
	name: string;
	entry?: string | null;
}

export interface Environment {
	id: string;
	project_id: string;
	name: string;
	status: string;
	connection_kind?: string | null;
	connection_ref?: string | null;
}

export interface Overview {
	machine_name: string;
	tenant_slug: string | null;
	tenant_name: string;
	project_slug: string | null;
	project_name: string;
	environment: string;
	environment_status: string | null;
	environment_display_status: string | null;
	attachment_status: string;
	attachment_error: string | null;
	entry: string;
	project_root: string | null;
	target_count: number;
	project_count: number;
	environment_count: number;
	categories: string[];
	category_counts: Record<string, number>;
	manifests: PluginManifest[];
	loaded_plugins: string[];
	plugins_declared: string[];
	runtime_agents: RuntimeItem[];
	runtime_tools: RuntimeItem[];
	runtime_workflows: RuntimeItem[];
}

export interface DomainPayload {
	domain: string;
	installed: boolean;
	implemented: boolean;
	categories: Record<string, RuntimeItem[]>;
	items: RuntimeItem[];
}

export interface ServicesStatus {
	studio_mount: string;
	runtime_api: string;
	health_endpoint: string;
	docs_endpoint: string;
	notes: string[];
}

export function getOverview() {
	return api<Overview>("/api/overview");
}

export function getContext() {
	return api<ContextResponse>("/api/context");
}

export function getTenants() {
	return api<Tenant[]>("/api/tenants");
}

export function getProjects(tenantSlug: string) {
	return api<Project[]>(`/api/tenants/${tenantSlug}/projects`);
}

export function getEnvironments(projectSlug: string) {
	return api<Environment[]>(`/api/projects/${projectSlug}/environments`);
}

export function switchContext(payload: {
	tenant_slug: string;
	project_slug: string;
	environment_name: string;
}) {
	return api<ContextResponse>("/api/context", {
		method: "PUT",
		body: JSON.stringify(payload),
	});
}

export function getPlugins() {
	return api<PluginManifest[]>("/api/registry/plugins");
}

export function getServicesStatus() {
	return api<ServicesStatus>("/api/services/status");
}

export function getDomain(endpoint: string) {
	return api<DomainPayload>(endpoint);
}
