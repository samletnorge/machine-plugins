// Studio ships as a static SPA served by the FastAPI studio_support host app.
// All data comes from /_studio/api/* and /api/*, so there is no SSR/prerender.
export const ssr = false;
export const prerender = false;
