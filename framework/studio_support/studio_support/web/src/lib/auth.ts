// Studio auth helpers. The SvelteKit app is served at /_studio/app while the
// FastAPI backend owns the Zitadel OIDC flow under /_studio/auth/*.

const API_ROOT = '/_studio';

export interface StudioUser {
	sub: string;
	email?: string | null;
	name?: string | null;
	roles: string[];
}

export async function getUser(): Promise<StudioUser | null> {
	try {
		const response = await fetch(`${API_ROOT}/auth/me`, { credentials: 'include' });
		if (!response.ok) return null;
		const data = await response.json();
		return data.user as StudioUser;
	} catch {
		return null;
	}
}

export function login(next?: string): void {
	const target = next ?? `${API_ROOT}/app/`;
	window.location.href = `${API_ROOT}/auth/login?next=${encodeURIComponent(target)}`;
}

export function logout(): void {
	window.location.href = `${API_ROOT}/auth/logout`;
}

export function hasRole(user: StudioUser | null, role: string): boolean {
	return Boolean(user?.roles?.includes(role));
}
