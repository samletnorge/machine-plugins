# deployer_support

Deployment abstraction and deployer implementations for Machine projects.

## Provides

- the `deployer` category
- built-in deployers for Docker, Vercel, and Cloudflare
- a Dokploy deployer class in source
- shared deployment request and result contracts

## Key Files

- `manifest.json`
- `__init__.py`
- `base.py`
- `docker.py`
- `vercel.py`
- `cloudflare.py`
- `dokploy.py`

## Role

This plugin provides a registry-driven deployment layer so Machine projects can target multiple deployment backends through a shared contract.
