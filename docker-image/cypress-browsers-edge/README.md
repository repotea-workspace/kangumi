# cypress-browsers-edge

A complete image with all operating system dependencies for Cypress and [Microsoft Edge browser](https://www.microsoftedgeinsider.com/en-us/download/?platform=linux-deb).

[Dockerfile](Dockerfile)

```text
node version:    v14.15.4
npm version:     6.14.11
yarn version:    1.22.10
Debian version:  10.7
Edge version:    Microsoft Edge 96.0.1047.2 dev
git version:     git version 2.20.1
whoami:          root
```

**Note:** this image uses the `root` user. You might want to switch to non-root
user like `node` when running this container for security.
