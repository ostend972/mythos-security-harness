---
class_id: nosql-injection
name: NoSQL Injection
applicable_languages: [javascript, typescript, python, java]
applicable_frameworks: [mongoose, pymongo, motor, mongodb-driver]
severity_default: high
fp_rate_expected: 0.20
skill: exploiting-nosql-injection-vulnerabilities
---

## Indicators

- MongoDB queries built from req.body without sanitization
- `find({email: req.body.email})` with no schema validation
- `$where` operator with template-string injection
- BSON deserialization of user input

## Hunting hints

- Grep for `find\(.+req\.`, `aggregate\(.+req\.`, `\$where:`
- Check for missing express-mongo-sanitize middleware
- Validate input types: object vs string operator confusion

## PoC strategy

1. Send `{"$ne": null}` instead of expected scalar
2. Confirm authentication bypass or data extraction
3. Use `$regex` for blind extraction if filters apply
