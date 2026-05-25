---
class_id: deserialization
name: Insecure Deserialization
applicable_languages: [python, java, ruby, php, csharp]
applicable_frameworks: [pickle, marshal, yaml.load, jackson, fastjson, gson, serializeFromString]
severity_default: critical
fp_rate_expected: 0.15
skill: exploiting-insecure-deserialization
---

## Indicators

- Use of `pickle.loads(user_input)` in Python
- Java `ObjectInputStream.readObject` from network
- PHP `unserialize($user_input)`
- YAML loading with default loader (Python `yaml.load(...)` without `SafeLoader`)

## Hunting hints

- Grep for `pickle.loads`, `pickle.load`, `cPickle`, `marshal.loads`
- Java: `ObjectInputStream`, `XStream.fromXML`
- PHP: `unserialize\(`
- Check loader argument; `Loader=SafeLoader` is safe

## PoC strategy

1. Craft a gadget chain payload (pickle/Java)
2. Send as the input expected by the deserializer
3. Confirm code execution via classpath gadget
