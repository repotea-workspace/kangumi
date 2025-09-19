smart-vercel
===


## Deploy staging environment

```
- uses: ./.github/actions/smart-vercel
  name: Deploy to Vercel
  id: smart-vercel
  with:
    vercel_token: ${{ secrets.VERCEL_TOKEN }}
    vercel_group: ${{ env.VERCEL_GROUP }}
    preview_output: true
```


## Deploy production environment

```
- uses: ./.github/actions/smart-vercel
  name: Deploy to Vercel
  id: smart-vercel
  with:
    vercel_token: ${{ secrets.VERCEL_TOKEN }}
    vercel_group: ${{ env.VERCEL_GROUP }}
    preview_output: true
    prod_mode: true
```

## Deploy use custom build command

```
- uses: ./.github/actions/smart-vercel
  name: Deploy to Vercel
  id: smart-vercel
  with:
    vercel_token: ${{ secrets.VERCEL_TOKEN }}
    vercel_group: ${{ env.VERCEL_GROUP }}
    preview_output: true
    script_build: yarn build:dev
```

## Deploy use custom script

```
- uses: actions/setup-ruby@v1
  with:
    ruby-version: '2.6'

- uses: actions/setup-node@v2
  with:
    node-version: '14'

- name: Build
  run: |
    gem install bundler
    bundle install
    bundle exec middleman build --clean --verbose

- uses: ./.github/actions/smart-vercel
  name: Deploy to Vercel
  id: smart-vercel
  with:
    vercel_token: ${{ secrets.VERCEL_TOKEN }}
    vercel_group: ${{ env.VERCEL_GROUP }}
    preview_output: true
    script_run: false
    prod_mode: true
```

## Use Vercel deploy (Not build in Github Actions)

```
- uses: ./.github/actions/smart-vercel
  name: Deploy to Vercel
  id: smart-vercel
  with:
    vercel_token: ${{ secrets.VERCEL_TOKEN }}
    vercel_group: ${{ env.VERCEL_GROUP }}
    preview_output: true
    script_run: false
    dist_path: .
```


## Special dist path

```
- uses: ./.github/actions/smart-vercel
  name: Deploy to Vercel
  id: smart-vercel
  with:
    vercel_token: ${{ secrets.VERCEL_TOKEN }}
    vercel_group: ${{ env.VERCEL_GROUP }}
    preview_output: true
    dist_path: build
```

## Special project name

```
- uses: ./.github/actions/smart-vercel
  name: Deploy to Vercel
  id: smart-vercel
  with:
    vercel_token: ${{ secrets.VERCEL_TOKEN }}
    vercel_group: ${{ env.VERCEL_GROUP }}
    preview_output: true
    project_name: your-project-name
```

## Set alias domain

```
- uses: ./.github/actions/smart-vercel
  name: Deploy to Vercel
  id: smart-vercel
  with:
    vercel_token: ${{ secrets.VERCEL_TOKEN }}
    vercel_group: ${{ env.VERCEL_GROUP }}
    preview_output: true
    alias_domain: domain-prefix # this will be bind domain-prefix.vercel.app to your deployment
```

```
- uses: ./.github/actions/smart-vercel
  name: Deploy to Vercel
  id: smart-vercel
  with:
    vercel_token: ${{ secrets.VERCEL_TOKEN }}
    vercel_group: ${{ env.VERCEL_GROUP }}
    preview_output: true
    alias_domain: |
      domain-prefix       # domain-prefix.vercel.app
      prefix-b.vercel.app # prefix-b.vercel.app
      your.custom.com     # your.custom.com
```

```
- uses: ./.github/actions/smart-vercel
  name: Deploy to Vercel
  id: smart-vercel
  with:
    vercel_token: ${{ secrets.VERCEL_TOKEN }}
    vercel_group: ${{ env.VERCEL_GROUP }}
    preview_output: true
    alias_domain: |
      domain-prefix,prefix-b.vercel.app,your.custom.com
```

## Use cache

> The cache feature only work when `script_run: true` this value default is true

enable cache. cache yarn

```
- uses: ./.github/actions/smart-vercel
  name: Deploy to Vercel
  id: smart-vercel
  with:
    vercel_token: ${{ secrets.VERCEL_TOKEN }}
    vercel_group: ${{ env.VERCEL_GROUP }}
    preview_output: true
    enable_cache: true
```

use npm, cache

```
- uses: ./.github/actions/smart-vercel
  name: Deploy to Vercel
  id: smart-vercel
  with:
    vercel_token: ${{ secrets.VERCEL_TOKEN }}
    vercel_group: ${{ env.VERCEL_GROUP }}
    preview_output: true
    enable_cache: true
    cache_type: npm
```

custom cache key and cache path

```
- uses: ./.github/actions/smart-vercel
  name: Deploy to Vercel
  id: smart-vercel
  with:
    vercel_token: ${{ secrets.VERCEL_TOKEN }}
    vercel_group: ${{ env.VERCEL_GROUP }}
    preview_output: true
    enable_cache: true
    cache_key: ${{ runner.os }}-${{ hashFiles('**/package-lock.json') }}
    cache_path: '**/node_modules'
```

## Notify with pr comment

> Please you known, this will be post a comment to pull request, so this only works when trigger by pull request.

```
on:
  pull_request:
```

```
- uses: ./.github/actions/smart-vercel
  name: Deploy to Vercel
  id: smart-vercel
  with:
    vercel_token: ${{ secrets.VERCEL_TOKEN }}
    vercel_group: ${{ env.VERCEL_GROUP }}
    preview_output: true
    enable_notify_comment: true
```

## Notify with slach channel


```
- uses: ./.github/actions/smart-vercel
  name: Deploy to Vercel
  id: smart-vercel
  with:
    vercel_token: ${{ secrets.VERCEL_TOKEN }}
    vercel_group: ${{ env.VERCEL_GROUP }}
    preview_output: true
    enable_notify_slack: true
    slack_channel: your-channel-name
    slack_webhook: ${{ secrets.SLACK_INCOMING_WEBHOOK_URL }}
```
