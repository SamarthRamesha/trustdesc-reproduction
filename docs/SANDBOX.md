# Execution isolation assessment

At inspection Docker, Podman and Colima were absent from PATH. macOS `sandbox-exec` exists, but mere availability does not validate an isolation profile. No third-party server/setup script was executed. No VM/container was installed, image pulled, or security setting changed.

`DisabledRunner` is the default for unknown implementations. `ControlledAgent` invokes only fixed, bounded, project-authored functions that validate text or normalize strings. A synthetic source marker is not permission to import code; the runner cannot import source or accept arbitrary callables. This controlled path is **not a sandbox** and cannot support a claim about untrusted runtime isolation.

## Options considered

| Option | What boundary it offers | Assessment |
|---|---|---|
| Python venv, subprocess, timeout, mock | Dependency/process/testing separation | Not a security boundary against hostile code |
| macOS sandbox-exec | Profile-dependent OS restrictions | Not adopted or validated; availability is insufficient |
| Hardened container inside a disposable Linux VM | OS namespaces/cgroups plus VM host separation | Candidate for future source execution; requires deliberate installation/probing |
| Separate disposable cloud VM | Separate kernel/machine from Mac | Candidate with cost/access approval, no personal accounts/credentials inside tool runtime |
| Google Colab alone | Hosted runtime with notebook permissions/network | Not assumed suitable for hostile tools; no unknown MCP execution in handover |

The Docker plan function returns a **review-only argument list**: pinned image, no network, read-only root, no added capabilities, no new privileges, unprivileged UID, process/memory/CPU limits and temporary filesystem. It deliberately has no execution call, source mounts, Docker socket or secrets. Container flags are a configuration proposal, not a successful isolation test. Docker has its own daemon/kernel attack surface: [official security documentation](https://docs.docker.com/engine/security/), [run options](https://docs.docker.com/reference/cli/docker/container/run/).

## Before enabling a real backend

Use reviewed pinned images and server dependency snapshots inside a disposable VM. Keep model credentials in the trusted orchestrator. Bind source hashes to the code actually invoked. Probe that outbound DNS/HTTP, host-directory reads, host writes, privileged actions, process/memory exhaustion, daemon socket access and metadata-service access are denied. Probes use harmless canary data only. Verify task timeout kills and removes all child/container processes, capped logs cannot exhaust host disk, and each task has fresh state. Verify required filesystem/API simulations still work under those restrictions. Record platform, commands, probe observations and residual kernel/container risks. Negative probe results must block evaluation rather than disabling controls to make a server run.

No such boundary/probes were validated in this session. Real network-dependent tools may need constrained mock services or an explicitly approved policy; changing their dependencies changes experimental fidelity and must be documented. Even a validated boundary would contain execution, not prove that a tool's behavior is benign or its finite tests are complete.
