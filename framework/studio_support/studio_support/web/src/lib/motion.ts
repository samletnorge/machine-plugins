import { gsap } from "gsap";

function reduced(): boolean {
	return (
		typeof window !== "undefined" &&
		window.matchMedia("(prefers-reduced-motion: reduce)").matches
	);
}

/** Stagger-reveal child elements inside the action's node when it mounts. */
export function reveal(
	node: HTMLElement,
	options: { selector?: string; y?: number; stagger?: number; delay?: number } = {}
) {
	let ctx: gsap.Context | undefined;

	const run = (opts = options) => {
		const { selector = "[data-reveal]", y = 22, stagger = 0.06, delay = 0.04 } = opts;
		ctx?.revert();
		if (reduced()) return;
		ctx = gsap.context(() => {
			const targets = gsap.utils.toArray<HTMLElement>(selector, node);
			if (!targets.length) return;
			gsap.from(targets, {
				autoAlpha: 0,
				y,
				duration: 0.55,
				ease: "power3.out",
				stagger,
				delay,
				clearProps: "opacity,visibility,transform",
			});
		}, node);
	};

	run();
	return {
		update: run,
		destroy() {
			ctx?.revert();
		},
	};
}

function format(value: number, decimals = 0): string {
	return value.toLocaleString(undefined, {
		minimumFractionDigits: decimals,
		maximumFractionDigits: decimals,
	});
}

/** Animate a number from 0 to `value` into the element's text. */
export function countUp(node: HTMLElement, options: { value: number; decimals?: number; duration?: number }) {
	let tween: gsap.core.Tween | undefined;

	const run = (opts = options) => {
		tween?.kill();
		const { value, decimals = 0, duration = 0.9 } = opts;
		if (reduced()) {
			node.textContent = format(value, decimals);
			return;
		}
		const state = { v: 0 };
		node.textContent = format(0, decimals);
		tween = gsap.to(state, {
			v: value,
			duration,
			ease: "power2.out",
			onUpdate: () => {
				node.textContent = format(state.v, decimals);
			},
			onComplete: () => {
				node.textContent = format(value, decimals);
			},
		});
	};

	run();
	return {
		update: run,
		destroy() {
			tween?.kill();
		},
	};
}
