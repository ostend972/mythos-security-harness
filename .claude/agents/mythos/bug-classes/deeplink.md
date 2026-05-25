---
class_id: deeplink
name: Mobile Deep Link Hijacking
applicable_languages: [kotlin, swift, dart, java, objc]
applicable_frameworks: [android, ios, flutter, react-native]
severity_default: high
fp_rate_expected: 0.20
skill: exploiting-deeplink-vulnerabilities
---

## Indicators

- Custom URL scheme registered without verification
- WebView loads `intent:` URLs without filtering
- Missing App Links / Universal Links verification
- Receiving activities exposed (Android: `exported="true"`)

## Hunting hints

- Inspect AndroidManifest.xml for `<intent-filter>` on receivers
- Check iOS `Info.plist` `CFBundleURLSchemes`
- Look for WebView `shouldOverrideUrlLoading` allowing arbitrary schemes

## PoC strategy

1. From a third-party app or web, craft a deeplink with malicious params
2. Confirm victim app accepts the deeplink and processes the params unsafely
3. Demonstrate auth bypass, account takeover, or data leak
