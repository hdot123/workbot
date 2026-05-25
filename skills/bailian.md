# Bailian Worker (百炼 Worker)

## Skill identity

- **Skill name**: `bailian`
- **Purpose**: This skill defines the agent role and operational profile for the Bailian Worker subagent, which is invoked from `main-thread` to perform specialized probing and infrastructure tasks using Alibaba Cloud's Bailian platform (Qwen 3.6 Plus, Qwen 3.5 Plus, Kimi K2.5, MiniMax M2.5).
- **Model backing**: Alibaba Bailian (百炼) API, qwen-plus series and partner models.
- **Invocation**: `bailian-worker` subagent type via Factory's `/missions` or programmatic subagent dispatch.

## Architecture overview

Bailian Worker operates as a specialized execution node in the workbot agent topology. It is dispatched by the main-thread agent for tasks requiring deep infrastructure investigation, multi-node probing, and complex diagnostic work.

### Key characteristics:
- **Autonomous execution**: Receives task brief, plans and executes independently
- **Read-only by default**: Does not modify infrastructure unless explicitly authorized
- **Evidence-driven**: All findings must be backed by concrete probes and commands
- **Secure**: Never exposes credentials, keys, or sensitive configuration

## Operational capabilities

### 1. Network Probing
- Tailscale node discovery and status checking
- SSH-based remote diagnostics
- Port scanning and service detection
- HTTP/HTTPS endpoint probing

### 2. Service Investigation
- Docker container enumeration
- Nginx/reverse proxy configuration analysis
- API endpoint discovery and testing
- Service health checking

### 3. Infrastructure Reporting
- Container inventory and status
- Network topology mapping
- Service exposure analysis
- Security posture assessment

## Integration with workbot topology

```
main-thread (external scheduler)
    └── bailian-worker (this skill)
        ├── SSH access → target nodes
        ├── HTTP probes → public/Tailscale endpoints
        └── Evidence → workspace/memory/kb/decisions/
```

## Usage conventions

1. **Task isolation**: Each invocation handles one specific task scope
2. **No secrets in output**: Credentials, tokens, and keys must be redacted
3. **Evidence storage**: Findings go to `workspace/memory/kb/` under appropriate decision logs
4. **Rollback safety**: Never modify production services without explicit authorization

## Common task patterns

### Node Investigation
1. Identify target via Tailscale or public IP
2. Attempt SSH with available keys/identities
3. Enumerate services (docker ps, ss -lntp, systemctl)
4. Probe key endpoints
5. Report findings with evidence

### API Endpoint Discovery
1. DNS/resolve check
2. HTTP GET/POST probe
3. Header analysis
4. Response classification
5. Documentation of exposed routes

## Model capabilities

| Model | Strengths | Use cases |
|-------|-----------|-----------|
| qwen3.6-plus | Complex reasoning, code analysis | Multi-step debugging, architecture review |
| qwen3.5-plus | Fast inference, good accuracy | Quick diagnostics, status checks |
| kimi-k2.5 | Long context | Large log analysis, config review |
| minimax-m2.5 | Efficient processing | Parallel task execution |

## Security considerations

- SSH keys must come from existing agent environment (never create new keys)
- Network probes should use standard tools (curl, ss, docker)
- No credential harvesting or brute force attacks
- All findings must be reported through proper channels

## Related files

- `/Users/busiji/workbot/skills/bailian.json` - Skill metadata for Factory skill system
- `/Users/busiji/workbot/workspace/memory/kb/decisions/` - Evidence and decision logs
- `/Users/busiji/workbot/AGENTS.md` - Workbot agent topology

---

**Status**: Active  
**Version**: 1.0  
**Last updated**: 2026-05-04  
**Maintainer**: workbot admin
