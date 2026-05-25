---
class_id: ssti
name: Server-Side Template Injection
applicable_languages: [python, javascript, typescript, java, ruby, php]
applicable_frameworks: [jinja2, twig, pug, nunjucks, handlebars, freemarker, velocity, smarty, erb, mustache]
severity_default: critical
fp_rate_expected: 0.20
skill: exploiting-template-injection-vulnerabilities
---

## Indicators

- User input concatenated into a template string before render
- `render_template_string(user_input)` (Jinja2 anti-pattern)
- Handlebars `{{{...}}}` triple-stash with user data
- Twig `{{ ... }}` evaluation of user-provided data

## Hunting hints

- Grep for `render_template_string\(`, `Template\(.*\+`
- Look for template engines exposed without sandbox mode
- Check for `{{ 7*7 }}` returning `49` (classic detection probe)

## PoC strategy

1. Submit `{{ 7*7 }}` and look for `49` in response
2. Escalate to RCE via `{{ ''.__class__.__mro__[1].__subclasses__() }}` (Python)
3. Confirm command execution via the chain
