# Python startup investigation

2026-11-09, Asia/Kolkata. The investigation and startup validation are complete; no new inference was launched during the investigation.

## Finding

The 13:54:32 Python abort was caused by the project-created Seatbelt policy denying dyld/libignition read access to the root directory. This is established by the kernel denial logs, the exact print-only launcher, and a controlled policy comparison. It is not an established memory or MLX failure.

At 13:54:32.670 the kernel records `Python(5022) deny(1) file-read-data /`; at 13:54:32.681 it records the same denial for PID 5023. The two crash reports name parent PID 5020 and have namespace `<0x23>`, code 2, SIGABRT, with `ignition_halt`, `ignite`, `CacheFinder`, `ProcessConfig::DyldCache` and `start` frames. Only Python and dyld are listed as loaded images.

## Reconstructed launch

The Codex transcript records `work/debug_seatbelt5.py` executing at 13:54:32. That script has a fixed three-case loop: system, framework, root. It is not an automatic retry loop. The system and framework cases failed once each; the root case succeeded. PID 5023 corresponds to the second failing case by sequence and timestamps; its policy file is `work/seatbelt-debug/framework.sb`. The crash report itself does not contain argv or the full historical environment, so that case mapping is a reconstruction, not process-memory recovery.

Command arguments:

```text
/usr/bin/sandbox-exec
-f
/Users/macbramesha/Documents/Codex/2026-11-09/https-github-com-samarthramesha-trustdesc-reproduction-2/work/seatbelt-debug/framework.sb
/opt/homebrew/Cellar/python@3.11/3.11.14_1/Frameworks/Python.framework/Versions/3.11/Resources/Python.app/Contents/MacOS/Python
-I
-S
-c
print(42)
```

Working directory: the project's `work/seatbelt-debug` directory. The script used `subprocess.run(..., cwd=root, capture_output=True, text=True, timeout=5)` with no `env=` argument, so it inherited its controller environment. No model library was imported by the child. Other earlier diagnostics explicitly tested `DYLD_PRINT_LIBRARIES=1`; this particular script did not set it. The historical full inherited environment was not saved and cannot be recovered after PID 5020 exited. Current inherited-environment tests contain no DYLD or Python home/path overrides. Both current inherited and explicitly clean launches pass, and changing only the root-directory rule fixed the historical print-only comparison.

The Codex session transcript and desktop logs were inspected around 08:24:32 UTC (13:54:32 IST). The transcript contains the diagnostic command and both `-6` results; the desktop log supplies no additional loader error. A four-second unified-log query supplies the exact root-directory denials above. Original crash reports and historical experiment records remain unchanged.

## Namespace and limits of interpretation

Apple's [XNU reason.h at xnu-12377.1.9](https://github.com/apple-oss-distributions/xnu/blob/xnu-12377.1.9/bsd/sys/reason.h) defines `OS_REASON_LIBIGNITION` as 35 (hexadecimal 0x23); it separately defines `OS_REASON_DYLD` as 6 and `OS_REASON_SANDBOX` as 25. The inspected [dyld CacheFinder source](https://github.com/apple-oss-distributions/dyld/blob/main/dyld/DyldProcessConfig.cpp) calls `ignite()` during shared-cache discovery. This matches the crash path. Neither inspected public source establishes the meaning of LIBIGNITION code 2 for this installed macOS 26.6 build; it is not relabeled as errno 2, a missing library, or an out-of-memory code. The local kernel denial is the evidence identifying the denied resource.

## Smallest safe fix

The project policy now contains:

```scheme
(allow file-read-data (literal "/"))
```

`literal` permits the root directory itself, not recursive access beneath it. The policy does not grant `(subpath "/")`. The runner also invokes the canonical `Resources/Python.app/Contents/MacOS/Python` binary directly, avoiding the Homebrew `bin/python3.11` launcher's extra spawn. A clean launch environment excludes DYLD, PYTHONHOME, PYTHONPATH and library-path overrides. Absolute executable paths remove PATH ambiguity.

Both sandbox and model-worker launch paths now run Python-only startup checks first. A startup failure stops after the first failed attempt and blocks worker launch; it does not retry a crashing executable. No Homebrew reinstall, system-cache modification, SIP change or Python deletion was performed. Homebrew's opt/bin links resolve to the installed 3.11.14_1 framework, and `codesign --verify` succeeds. No evidence supports changing that installation.

## Validation performed

- 10/10 direct Python startups through Codex with inherited environment pass.
- 10/10 with an explicitly clean environment pass.
- 3/3 under the corrected Seatbelt policy pass.
- Project-created canaries confirm outside reads, outside writes, loopback network connections and child process execution are denied.
- 149 unit/integration tests pass, including four new startup regression tests.
- PID 5020, PID 5023 and project qualification/debug/model-worker processes are no longer running. There is no respawn loop.

Native Terminal results subsequently arrived in `terminal_startup.json`: TERM_PROGRAM is Apple_Terminal and the controller parent is zsh. The same canonical Python executable passes 10/10 inherited-environment startups, 10/10 clean startups, 3/3 Seatbelt startups and all four isolation canaries. Thus the recorded comparison is 23/23 startup checks through Codex and 23/23 through native Terminal (46/46 total), with no startup failures. Terminal has no DYLD/PYTHONHOME/PYTHONPATH overrides in the recorded environment. The computer-use tool refused Terminal access, so no UI inspection is claimed; completion is verified from the test-generated result file. The supplied script imports no MLX or model.

## Evidence preserved in the repository checkout

`reports/apple_recovery/startup_investigation/` contains the kernel denial excerpt, crash summary, exact Codex launch excerpt, desktop log excerpt, Codex smoke results and regression output. No raw credential files or unrelated logs were copied into the project. All previous research outputs and checkpoints are preserved.
