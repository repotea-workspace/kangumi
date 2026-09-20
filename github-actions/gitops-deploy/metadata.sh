gitops_metadata_dir() {
  if [ -d "${GITHUB_WORKSPACE}/__origin__/.github" ]; then
    printf '%s\n' "${GITHUB_WORKSPACE}/__origin__/.github"
  else
    printf '%s\n' "${GITHUB_WORKSPACE}/.github"
  fi
}
