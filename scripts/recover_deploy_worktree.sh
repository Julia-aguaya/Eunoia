#!/usr/bin/env bash
set -euo pipefail
umask 077

project_dir="$HOME/eunoia"
venv_python="$project_dir/.venv/bin/python"

readonly allowed_paths=(
  'scripts/configure_resend_smtp.sh'
  'scripts/configure_resend_api.sh'
  'deploy-eunoia.sh'
)

fail() {
  printf '%s\n' "$1" >&2
  exit 1
}

is_allowed_path() {
  local path="$1"
  local allowed_path

  for allowed_path in "${allowed_paths[@]}"; do
    [[ "$path" == "$allowed_path" ]] && return 0
  done

  return 1
}

worktree_is_clean() {
  local entry
  ! IFS= read -r -d '' entry < <(git status --porcelain=v1 -z)
}

secure_backup() {
  local destination="$1"

  chmod 600 "$destination"
  [[ -f "$destination" && "$(stat -c '%a' "$destination")" == '600' ]] || fail 'Recovery failed: backup was not created securely.'
}

cd "$project_dir"
[[ "$(git branch --show-current)" == 'main' ]] || fail 'Recovery precondition failed: expected main branch.'

declare -a changed_paths=()
declare -a changed_statuses=()
declare -a unexpected_paths=()
unsupported_status=false

while IFS= read -r -d '' entry; do
  status="${entry:0:2}"
  path="${entry:3}"

  if [[ "${status:0:1}" == [RC] || "${status:1:1}" == [RC] ]]; then
    IFS= read -r -d '' original_path || fail 'Recovery precondition failed: malformed Git status output.'
    unexpected_paths+=("$path" "$original_path")
    unsupported_status=true
    continue
  fi

  if ! is_allowed_path "$path"; then
    unexpected_paths+=("$path")
    continue
  fi

  case "$status" in
    ' M'|'M '|'MM'|'A '|'AM'|'??')
      changed_paths+=("$path")
      changed_statuses+=("$status")
      ;;
    *)
      unexpected_paths+=("$path")
      unsupported_status=true
      ;;
  esac
done < <(git status --porcelain=v1 -z)

if ((${#unexpected_paths[@]})); then
  printf '%s\n' 'Recovery precondition failed: unexpected worktree paths.' >&2
  printf '%s\n' "${unexpected_paths[@]}" >&2
  exit 1
fi

[[ "$unsupported_status" == false ]] || fail 'Recovery precondition failed: unsupported worktree status.'
(( ${#changed_paths[@]} > 0 )) || fail 'Recovery precondition failed: no permitted worktree changes found.'

backup_dir="$(mktemp -d "$HOME/eunoia-recovery-backups.XXXXXXXX")"
chmod 700 "$backup_dir"
[[ "$(stat -c '%a' "$backup_dir")" == '700' ]] || fail 'Recovery failed: backup directory permissions.'

for index in "${!changed_paths[@]}"; do
  path="${changed_paths[$index]}"
  status="${changed_statuses[$index]}"
  backup_name="${path//\//_}"

  if [[ "$status" != '??' && "${status:0:1}" != ' ' ]]; then
    git show ":$path" > "$backup_dir/$backup_name.index"
    secure_backup "$backup_dir/$backup_name.index"
  fi

  if [[ -e "$path" ]]; then
    if git cat-file -e "HEAD:$path" 2>/dev/null; then
      cp --preserve=mode,timestamps -- "$path" "$backup_dir/$backup_name.worktree"
      secure_backup "$backup_dir/$backup_name.worktree"
    else
      mv -- "$path" "$backup_dir/$backup_name.worktree"
      secure_backup "$backup_dir/$backup_name.worktree"
    fi
  fi

  if git cat-file -e "HEAD:$path" 2>/dev/null; then
    git restore --source=HEAD --staged --worktree -- "$path"
  else
    git rm --cached --ignore-unmatch -- "$path"
    rm -f -- "$path"
  fi
done

worktree_is_clean || fail 'Recovery failed: worktree is not clean after targeted recovery.'

temporary_dir="$(mktemp -d)"
trap 'rm -rf "$temporary_dir"' EXIT
git fetch origin main
target_commit="$(git rev-parse origin/main)"
git show "$target_commit:deploy-eunoia.sh" > "$temporary_dir/deploy-eunoia.sh"
chmod 700 "$temporary_dir/deploy-eunoia.sh"
"$temporary_dir/deploy-eunoia.sh"

deployed_commit="$(git rev-parse HEAD)"
[[ "$deployed_commit" == "$(git rev-parse origin/main)" ]] || fail 'Recovery failed: deployed commit does not match origin/main.'
printf 'deployed_commit=%s\n' "$deployed_commit"
worktree_is_clean || fail 'Recovery failed: worktree is not clean after deploy.'
printf '%s\n' 'git_status=clean'
"$venv_python" -c 'from anymail.backends.resend import EmailBackend'
"$venv_python" -m pip check
"$venv_python" manage.py check
sudo -n systemctl is-active --quiet eunoia
printf '%s\n' 'service=eunoia active'
