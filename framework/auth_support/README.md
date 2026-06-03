# auth_support

Framework plugin for authentication and authorization in Machine runtimes.

## Provides

- the `auth_provider` category
- auth operations such as `authenticate`, `authorize`, `create_token`, `verify_token`, and `revoke_token`
- shared auth models including users, roles, permissions, and tokens
- built-in JWT and API-key auth providers

## Key Files

- `manifest.json`
- `machine_auth/__init__.py`

## Role

This plugin supplies a reusable auth contract and a couple of default providers for projects that want auth behavior in the same registry-driven model as the rest of the system.
