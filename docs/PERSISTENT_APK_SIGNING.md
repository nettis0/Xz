# Persistent APK updates

The workflow can sign every build with one stable Android signing key. Without this key, GitHub-hosted runners generate a new debug key on each run, so Android rejects an APK update because its certificate changed.

Create one private keystore once:

```sh
keytool -genkeypair -v -keystore smarttube-signing.jks -alias smarttube -keyalg RSA -keysize 2048 -validity 10000
base64 -w0 smarttube-signing.jks
```

In the GitHub repository, open **Settings → Secrets and variables → Actions** and add these repository secrets:

- `ANDROID_KEYSTORE_BASE64`: the complete base64 output from the second command
- `ANDROID_KEYSTORE_PASSWORD`: the keystore password
- `ANDROID_KEY_ALIAS`: `smarttube` (or the alias chosen above)
- `ANDROID_KEY_PASSWORD`: the key password

Keep the keystore and passwords private. Do not commit them to the repository or send them in chat.

**One-time migration:** APKs installed from earlier workflow runs were signed with temporary runner keys. Android cannot update those with the new persistent key. Uninstall the old fork once, install the first APK built after configuring these secrets, and subsequent builds using the same secrets can install as updates. Your saved VLESS profile may be lost when uninstalling; keep a private copy of the VLESS link before doing this.
