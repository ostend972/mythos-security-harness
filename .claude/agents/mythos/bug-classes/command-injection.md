---
class_id: command-injection
name: OS Command Injection
applicable_languages: [python, javascript, typescript, java, ruby, php, go, csharp]
applicable_frameworks: []
severity_default: critical
fp_rate_expected: 0.10
skill: exploiting-api-injection-vulnerabilities
---

## Indicators

- `os.system(user_input)`, `subprocess.run(shell=True, ...)` with concatenation
- Node `child_process.exec(...)` with template strings
- Use of shell glob expansion (`*`, `?`) near user input
- Sink functions: `Runtime.exec`, `eval`, backtick subprocess

## Hunting hints

- Grep for `subprocess.run.+shell=True`, `os.system\(`, `exec\(`
- Node: `exec\(.+\$\{`, `execSync\(.+\$\{`
- Check for unsanitized `;`, `|`, `&&`, `$(...)` in command strings

## PoC strategy

1. Inject `; id` or `&& whoami` payloads
2. Use OOB callback (DNS to attacker-controlled domain) if blind
3. Confirm arbitrary command execution
