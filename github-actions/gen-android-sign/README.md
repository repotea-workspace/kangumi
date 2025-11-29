# Generate android sign file actions

Generate android sign file, like `key.properties`

## Inputs

### `path`

**Required:** The relative directory path you want to write

### `signingKeyBase64`

**Required:** The base64 encoded signing key used to sign your app

This action will directly decode this input to a file to sign your release with. You can prepare your key by running this command on *nix systems.

```bash
openssl base64 < some_signing_key.jks | tr -d '\n' | tee some_signing_key.jks.base64.txt
```
Then copy the contents of the `.txt` file to your GH secrets

### `alias`

**Required:** The alias of your signing key

### `keyStorePassword`

**Required:** The password to your signing keystore

### `keyPassword`

**Optional:** The private key password for your signing keystore

## Outputs

Output variables are set both locally and in environment variables.

### `path`/ ENV: `ANDROID_KEY_PROPERTIES`

The path of sign key file

## Example usage

### Generate sign config file

```yaml
steps:
  - uses: actions/checkout@v6
    with:
      repository: repotea-workspace/kangumi
      path: .github/actions

  - uses: ./.github/actions/github-actions/gen-android-sign
    name: Generate sign file
    # ID used to access action output
    id: gen-sign
    with:
      path: android/key.properties
      signingKeyBase64: ${{ secrets.SIGNING_KEY }}
      alias: ${{ secrets.ALIAS }}
      keyStorePassword: ${{ secrets.KEY_STORE_PASSWORD }}
      keyPassword: ${{ secrets.KEY_PASSWORD }}
```
