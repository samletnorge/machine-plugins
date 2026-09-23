import ActivityIcon from "@lucide/svelte/icons/activity";
import BotIcon from "@lucide/svelte/icons/bot";
import BrainIcon from "@lucide/svelte/icons/brain";
import ChartColumnIcon from "@lucide/svelte/icons/chart-column";
import DatabaseIcon from "@lucide/svelte/icons/database";
import EyeIcon from "@lucide/svelte/icons/eye";
import FolderIcon from "@lucide/svelte/icons/folder";
import GlobeIcon from "@lucide/svelte/icons/globe";
import LayoutDashboardIcon from "@lucide/svelte/icons/layout-dashboard";
import MessagesSquareIcon from "@lucide/svelte/icons/messages-square";
import MicIcon from "@lucide/svelte/icons/mic";
import PackageIcon from "@lucide/svelte/icons/package";
import RadioIcon from "@lucide/svelte/icons/radio";
import RocketIcon from "@lucide/svelte/icons/rocket";
import SearchIcon from "@lucide/svelte/icons/search";
import SettingsIcon from "@lucide/svelte/icons/settings";
import ShieldCheckIcon from "@lucide/svelte/icons/shield-check";
import SlidersHorizontalIcon from "@lucide/svelte/icons/sliders-horizontal";
import type { Component } from "svelte";

export type IconComponent = Component;

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
			{ key: "dashboard", label: "Overview", href: "/", icon: LayoutDashboardIcon },
			{ key: "registry", label: "Registry", href: "/registry", icon: PackageIcon },
			{ key: "services", label: "Services", href: "/services", icon: ActivityIcon },
		],
	},
	{
		section: "Build",
		items: [
			{ key: "runtime", label: "Agents & Tools", href: "/runtime", icon: BotIcon },
			{ key: "chat", label: "Chat", href: "/chat", icon: MessagesSquareIcon },
		],
	},
	{
		section: "Data",
		items: [
			{ key: "memory", label: "Memory", href: "/domain/memory", icon: BrainIcon, endpoint: "/api/memory/threads" },
			{ key: "rag", label: "RAG", href: "/domain/rag", icon: SearchIcon, endpoint: "/api/rag/pipelines" },
			{ key: "evals", label: "Evals", href: "/domain/evals", icon: ChartColumnIcon, endpoint: "/api/evals/runs" },
			{ key: "storage", label: "Storage", href: "/domain/storage", icon: DatabaseIcon, endpoint: "/api/storage/files" },
		],
	},
	{
		section: "Operations",
		items: [
			{ key: "deploy", label: "Deploy", href: "/domain/deploy", icon: RocketIcon, endpoint: "/api/deploy/targets" },
			{ key: "observe", label: "Observability", href: "/domain/observe", icon: EyeIcon, endpoint: "/api/observe/traces" },
			{ key: "pubsub", label: "Events", href: "/domain/pubsub", icon: RadioIcon, endpoint: "/api/pubsub/events" },
			{ key: "workspace", label: "Workspace", href: "/domain/workspace", icon: FolderIcon, endpoint: "/api/workspace/files" },
			{ key: "browser", label: "Browser", href: "/domain/browser", icon: GlobeIcon, endpoint: "/api/browser/sessions" },
			{ key: "voice", label: "Voice", href: "/domain/voice", icon: MicIcon, endpoint: "/api/voice/voices" },
		],
	},
	{
		section: "Workspace",
		items: [
			{ key: "context", label: "Context", href: "/context", icon: SlidersHorizontalIcon },
			{ key: "config", label: "Config", href: "/config", icon: SettingsIcon },
			{ key: "auth", label: "Auth", href: "/domain/auth", icon: ShieldCheckIcon, endpoint: "/api/auth/keys" },
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

export function titleFor(pathname: string, base: string): string {
	if (pathname.includes("/domain/")) return "Control plane";
	const rel = pathname.startsWith(base) ? pathname.slice(base.length) : pathname;
	if (rel === "" || rel === "/") return "Overview";
	for (const section of NAV_SECTIONS) {
		for (const item of section.items) {
			if (item.href !== "/" && (rel === item.href || rel.startsWith(`${item.href}/`))) {
				return item.label;
			}
		}
	}
	return "Studio";
}
