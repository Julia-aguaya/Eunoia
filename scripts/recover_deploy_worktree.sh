#!/usr/bin/env bash
set -euo pipefail
umask 077

project_dir="$HOME/eunoia"
drifted_path='scripts/configure_resend_smtp.sh'
venv_python="$project_dir/.venv/bin/python"

fail() {
  printf '%s\n' "$1" >&2
  exit 1
}

cd "$project_dir"
[[ "$(git branch --show-current)" == 'main' ]] || fail 'Recovery precondition failed: expected main branch.'
[[ "$(git status --porcelain=v1)" == " M $drifted_path" ]] || fail 'Recovery precondition failed: unexpected worktree changes.'

backup_dir="$HOME/eunoia-recovery-backups"
backup_file="$backup_dir/configure_resend_smtp.sh.$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$backup_dir"
chmod 700 "$backup_dir"
[[ "$(stat -c '%a' "$backup_dir")" == '700' ]] || fail 'Recovery failed: backup directory permissions.'
cp --preserve=mode,timestamps "$drifted_path" "$backup_file"
chmod 600 "$backup_file"
[[ -f "$backup_file" && "$(stat -c '%a' "$backup_file")" == '600' ]] || fail 'Recovery failed: backup was not created securely.'

git restore --source=HEAD --staged --worktree -- "$drifted_path"
[[ -z "$(git status --porcelain=v1)" ]] || fail 'Recovery failed: worktree is not clean after targeted restore.'

temporary_dir="$(mktemp -d)"
trap 'rm -rf "$temporary_dir"' EXIT
git fetch origin main
git show origin/main:deploy-eunoia.sh > "$temporary_dir/deploy-eunoia.sh"
chmod 700 "$temporary_dir/deploy-eunoia.sh"
"$temporary_dir/deploy-eunoia.sh"

printf 'deployed_commit=%s\n' "$(git rev-parse HEAD)"
[[ -z "$(git status --porcelain=v1)" ]] || fail 'Recovery failed: worktree is not clean after deploy.'
printf '%s\n' 'git_status=clean'
"$venv_python" -c 'from anymail.backends.resend import EmailBackend'
"$venv_python" -m pip check
"$venv_python" manage.py check
sudo -n systemctl is-active --quiet eunoia
printf '%s\n' 'service=eunoia active'
