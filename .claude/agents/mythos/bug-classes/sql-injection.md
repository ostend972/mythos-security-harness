---
class_id: sql-injection
name: SQL Injection
applicable_languages: [python, javascript, typescript, java, ruby, php, go, csharp]
applicable_frameworks: [django, flask, fastapi, express, koa, nestjs, rails, spring, laravel, gin]
severity_default: high
fp_rate_expected: 0.15
skill: exploiting-sql-injection-vulnerabilities
---

## Indicators

- Raw SQL string concatenation with user input
- `f"SELECT ... {var}"` or `"... " + var + " ..."` patterns
- Use of `execute(query)` instead of `execute(query, params)`
- ORM methods that take raw SQL (`.raw()`, `.execute()`)
- Lack of parameterized queries near HTTP handlers

## Hunting hints

- Grep for `cursor.execute(.+%`, `cursor.execute(.+\+`, `cursor.execute(f"`
- Check Django `QuerySet.extra()`, `RawSQL`, `objects.raw()`
- Check Rails ActiveRecord `where("col = '#{val}'")` patterns

## PoC strategy

1. Identify the entry point (HTTP handler accepting user-controlled input)
2. Trace to the vulnerable query construction
3. Craft a minimal payload (e.g., `' OR 1=1--`)
4. Execute against a local DB instance via the sandbox
5. Confirm extraction of unintended data
