import { getOverview, type Overview } from "./api";
import { getUser, type StudioUser } from "./auth";

export interface StudioState {
	user: StudioUser | null;
	overview: Overview | null;
	loading: boolean;
	error: string | null;
	loaded: boolean;
}

export const studio = $state<StudioState>({
	user: null,
	overview: null,
	loading: false,
	error: null,
	loaded: false,
});

export async function loadStudio(force = false): Promise<void> {
	if (studio.loaded && !force) return;
	studio.loading = true;
	studio.error = null;
	try {
		const [user, overview] = await Promise.all([getUser(), getOverview()]);
		studio.user = user;
		studio.overview = overview;
		studio.loaded = true;
	} catch (error) {
		studio.error = error instanceof Error ? error.message : String(error);
	} finally {
		studio.loading = false;
	}
}

export function initials(name?: string | null, email?: string | null): string {
	const source = name?.trim() || email?.trim() || "?";
	const parts = source.split(/[\s@.]+/).filter(Boolean);
	if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
	return source.slice(0, 2).toUpperCase();
}
