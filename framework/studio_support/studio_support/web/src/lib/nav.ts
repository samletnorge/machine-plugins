import AdjustmentsIcon from "@tabler/icons-svelte/icons/adjustments";
import BrainIcon from "@tabler/icons-svelte/icons/brain";
import BrowserIcon from "@tabler/icons-svelte/icons/browser";
import ChartBarIcon from "@tabler/icons-svelte/icons/chart-bar";
import DashboardIcon from "@tabler/icons-svelte/icons/dashboard";
import DatabaseIcon from "@tabler/icons-svelte/icons/database";
import EyeIcon from "@tabler/icons-svelte/icons/eye";
import FolderIcon from "@tabler/icons-svelte/icons/folder";
import MicrophoneIcon from "@tabler/icons-svelte/icons/microphone";
import PuzzleIcon from "@tabler/icons-svelte/icons/puzzle";
import RocketIcon from "@tabler/icons-svelte/icons/rocket";
import SearchIcon from "@tabler/icons-svelte/icons/search";
import SettingsIcon from "@tabler/icons-svelte/icons/settings";
import ShieldIcon from "@tabler/icons-svelte/icons/shield";
import SparklesIcon from "@tabler/icons-svelte/icons/sparkles";
import StackIcon from "@tabler/icons-svelte/icons/stack";
import WaveSineIcon from "@tabler/icons-svelte/icons/wave-sine";

export type IconComponent = typeof DashboardIcon;

export interface NavItem {
	key: string;
	label: string;
	href: string;
	icon: IconComponent;
	/** Control-plane JSON endpoint for generic domain pages. */
	endpoint?: string;
}

export interface NavSection {
	section: string;
	items: NavItem[];
}

export const NAV_SECTIONS: NavSection[] = [
	{
		section: "Core",
		items: [
			{ key: "dashboard", label: "Dashboard", href: "/", icon: DashboardIcon },
			{ key: "registry", label: "Registry", href: "/registry", icon: PuzzleIcon },
			{ key: "services", label: "Services", href: "/services", icon: StackIcon },
		],
	},
	{
		section: "Runtime",
		items: [
			{ key: "runtime", label: "Agents & Tools", href: "/runtime", icon: SparklesIcon },
		],
	},
	{
		section: "Data",
		items: [
			{
				key: "memory",
				label: "Memory",
				href: "/domain/memory",
				icon: BrainIcon,
				endpoint: "/api/memory/threads",
			},
			{
				key: "rag",
				label: "RAG",
				href: "/domain/rag",
				icon: SearchIcon,
				endpoint: "/api/rag/pipelines",
			},
			{
				key: "evals",
				label: "Evals",
				href: "/domain/evals",
				icon: ChartBarIcon,
				endpoint: "/api/evals/runs",
			},
			{
				key: "storage",
				label: "Storage",
				href: "/domain/storage",
				icon: DatabaseIcon,
				endpoint: "/api/storage/files",
			},
		],
	},
	{
		section: "Infra",
		items: [
			{
				key: "deploy",
				label: "Deploy",
				href: "/domain/deploy",
				icon: RocketIcon,
				endpoint: "/api/deploy/targets",
			},
			{
				key: "observe",
				label: "Observability",
				href: "/domain/observe",
				icon: EyeIcon,
				endpoint: "/api/observe/traces",
			},
			{
				key: "pubsub",
				label: "Events",
				href: "/domain/pubsub",
				icon: WaveSineIcon,
				endpoint: "/api/pubsub/events",
			},
			{
				key: "workspace",
				label: "Workspace",
				href: "/domain/workspace",
				icon: FolderIcon,
				endpoint: "/api/workspace/files",
			},
			{
				key: "browser",
				label: "Browser",
				href: "/domain/browser",
				icon: BrowserIcon,
				endpoint: "/api/browser/sessions",
			},
			{
				key: "voice",
				label: "Voice",
				href: "/domain/voice",
				icon: MicrophoneIcon,
				endpoint: "/api/voice/voices",
			},
		],
	},
	{
		section: "Settings",
		items: [
			{ key: "context", label: "Context", href: "/context", icon: AdjustmentsIcon },
			{ key: "config", label: "Config", href: "/config", icon: SettingsIcon },
			{
				key: "auth",
				label: "Auth",
				href: "/domain/auth",
				icon: ShieldIcon,
				endpoint: "/api/auth/keys",
			},
		],
	},
];

export function findDomain(key: string): NavItem | undefined {
	for (const section of NAV_SECTIONS) {
		const match = section.items.find((item) => item.key === key);
		if (match) return match;
	}
	return undefined;
}
