Clone Any
===

## Clone a repository via https

```
- uses: actions/checkout@v4
  with:
    repository: fewensa/actions
    path: .github/actions

- name: Clone repository
  uses: ./.github/actions/clone-any
  with:
    repository: 'https://github.com/org/repo'
```

## Clone a repository via ssh

```
- uses: actions/checkout@v4
  with:
    repository: fewensa/actions
    path: .github/actions

- name: Clone repository
  uses: ./.github/actions/clone-any
  with:
    repository: 'git@github.com:org/repo.git'
    ssh-key: |
      ---PRIVATE KEY---
      ...
      ---END---
```

