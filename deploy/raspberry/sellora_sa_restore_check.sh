#!/usr/bin/env bash
# Restore the encrypted local copy matched by the last off-host verification.
set -euo pipefail
umask 077

fail() { printf '%s\n' "$1" >&2; exit 1; }

root=/home/btcradar/runtime/sellora/protected-backups
receipt="$root/.last-offhost-verified"
key="$root/db-backup-passphrase.key"
image=postgres:17-alpine
expected_revision=202611120055

[[ $(id -u) == 1000 && -t 0 ]] || fail OWNER_TERMINAL_REQUIRED
[[ -d "$root" && ! -L "$root" && $(stat -c '%u:%a' "$root") == 1000:700 ]] ||
  fail BACKUP_DIRECTORY_INVALID
private_file() {
  [[ -f "$1" && ! -L "$1" && -s "$1" && $(stat -c '%u:%a' "$1") == 1000:600 ]]
}
private_file "$receipt" && private_file "$key" || fail BACKUP_RECEIPT_OR_KEY_INVALID
[[ $(stat -c '%s' "$receipt") -le 1024 ]] || fail BACKUP_RECEIPT_INVALID

mapfile -t fields < "$receipt"
[[ ${#fields[@]} == 5 ]] || fail BACKUP_RECEIPT_INVALID
[[ ${fields[0]} =~ ^verified_at_utc=([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z)$ ]] ||
  fail BACKUP_RECEIPT_TIME_INVALID
verified_at=${BASH_REMATCH[1]}
[[ ${fields[1]} =~ ^filename=(sellora-db-[0-9]{8}-[0-9]{6}\.pgdump\.enc)$ ]] ||
  fail BACKUP_FILENAME_INVALID
filename=${BASH_REMATCH[1]}
[[ ${fields[2]} =~ ^sha256=([a-f0-9]{64})$ ]] || fail BACKUP_RECEIPT_HASH_INVALID
expected_hash=${BASH_REMATCH[1]}
[[ ${fields[3]} =~ ^size=([1-9][0-9]{0,9})$ && ${fields[4]} == remote=nexolab-edge-01 ]] ||
  fail BACKUP_RECEIPT_INVALID
expected_size=${BASH_REMATCH[1]}
(( expected_size <= 1073741824 )) || fail BACKUP_SIZE_INVALID
archive="$root/$filename"
private_file "$archive" || fail BACKUP_ARCHIVE_INVALID
[[ $(stat -c '%s' "$archive") == "$expected_size" ]] || fail BACKUP_SIZE_MISMATCH
age=$(( $(date +%s) - $(stat -c '%Y' "$archive") ))
(( age >= 0 && age < 129600 )) || fail BACKUP_ARCHIVE_STALE
read -r hash _ < <(sha256sum < "$archive")
[[ "$hash" == "$expected_hash" ]] || fail BACKUP_SHA256_MISMATCH

image_id=$(docker image inspect --format '{{.Id}}' "$image") || fail BACKUP_POSTGRES_IMAGE_MISSING
[[ "$image_id" =~ ^sha256:[a-f0-9]{64}$ ]] || fail BACKUP_POSTGRES_IMAGE_INVALID

restore_command='
set -eu
export LC_ALL=C

restore_failure() {
  result=$1
  log=/tmp/restore.stderr
  reason=UNCLASSIFIED
  if [ "$result" -eq 124 ]; then
    reason=TIMEOUT
  elif [ "$result" -eq 143 ]; then
    reason=TERMINATED
  elif [ "$result" -eq 137 ]; then
    reason=KILLED
  elif grep -Fq "No space left on device" "$log"; then
    if grep -Fq "shared memory segment" "$log"; then
      reason=SHARED_MEMORY_FULL
    else
      reason=STORAGE_FULL
    fi
  elif grep -Eq "out of memory|Cannot allocate memory" "$log"; then
    reason=OUT_OF_MEMORY
  elif grep -Eq "unsupported version|invalid archive version" "$log"; then
    reason=ARCHIVE_VERSION_UNSUPPORTED
  elif grep -Eq "could not read from input file|unexpected end of file|input file is too short|does not appear to be a valid archive|could not uncompress data" "$log"; then
    reason=ARCHIVE_READ_FAILED
  elif grep -Eq "unrecognized configuration parameter" "$log"; then
    reason=SERVER_SETTING_UNSUPPORTED
  elif grep -Fq "schema \"public\" already exists" "$log"; then
    reason=PUBLIC_SCHEMA_ALREADY_EXISTS
  elif grep -Eq "ERROR:.*role .*does not exist" "$log"; then
    reason=MISSING_ROLE
  elif grep -Eq "ERROR:.*extension .*is not available" "$log"; then
    reason=MISSING_EXTENSION
  elif grep -Eq "ERROR:.*(function|relation|schema|type|operator) .*does not exist" "$log"; then
    reason=MISSING_DB_OBJECT
  elif grep -Eq "permission denied|Operation not permitted" "$log"; then
    reason=PERMISSION_DENIED
  elif grep -Eq "server closed the connection unexpectedly|connection to server .* failed|could not connect to server" "$log"; then
    reason=DATABASE_CONNECTION_LOST
  elif grep -Fq "could not execute query" "$log"; then
    reason=SQL_EXECUTION_FAILED
  fi
  printf "ARCHIVE_RESTORE_FAILED reason=%s pg_restore_exit=%s\n" "$reason" "$result" >&2
  # Only emit the server error code and a fixed allowlist of SQL command tags.
  # The server log and pg_restore stderr can contain production data.
  diagnostic=$(awk -F ":" "
    \$1 == \"SELLORA_RESTORE\" && \$2 ~ /^[0-9A-Z][0-9A-Z][0-9A-Z][0-9A-Z][0-9A-Z]$/ &&
        \$4 ~ /^[[:space:]]*(ERROR|FATAL|PANIC)$/ {
      state = \$2
      command = \$3
    }
    END {
      if (!state) exit
      if (command !~ /^(ALTER TABLE|ALTER SCHEMA|COMMENT|COPY|CREATE EXTENSION|CREATE FUNCTION|CREATE INDEX|CREATE POLICY|CREATE SCHEMA|CREATE TABLE|CREATE TRIGGER|CREATE TYPE|CREATE VIEW|INSERT|SELECT|SET|DO)$/)
        command = \"OTHER\"
      gsub(/ /, \"_\", command)
      print \"sqlstate=\" state, \"sql_command=\" command
    }
  " /tmp/postgres.log 2>/dev/null || true)
  printf "%s\n" "${diagnostic:-sqlstate=UNAVAILABLE}" >&2
  toc_entry=$(awk "/^pg_restore: from TOC entry [0-9]+;/ {
    id = \$5
    sub(/;$/, \"\", id)
    print \"archive_toc_entry=\" id
    exit
  }" "$log")
  if [ -n "$toc_entry" ]; then printf "%s\n" "$toc_entry" >&2; fi
  df -Pk "$PGDATA" /dev/shm | awk "NR > 1 {print \"available_kib=\" \$4, \"mount=\" \$6}" >&2
  exit 1
}

initdb -D "$PGDATA" --username=postgres --auth-local=trust --auth-host=reject \
  > /dev/null 2>&1 || { echo RESTORE_INIT_FAILED >&2; exit 1; }
pg_ctl -D "$PGDATA" -l /tmp/postgres.log \
  -o "-c listen_addresses= -c unix_socket_directories=/tmp -c shared_buffers=24MB -c max_connections=10 -c log_line_prefix=SELLORA_RESTORE:%e:%i: -c log_error_verbosity=terse -c log_min_messages=error -c log_min_error_statement=panic" \
  -t 30 -w start > /dev/null 2>&1 || { echo RESTORE_START_FAILED >&2; exit 1; }
createdb -h /tmp -U postgres -T template0 sellora_restore_check \
  > /dev/null 2>&1 || { echo RESTORE_CREATE_DB_FAILED >&2; exit 1; }
# template0 includes public, which a schema-filtered archive can recreate.
# Clean only the objects in the archive, inside this disposable database.
timeout 600 pg_restore -h /tmp -U postgres -d sellora_restore_check \
  --clean --if-exists --no-owner --no-privileges --single-transaction --exit-on-error \
  > /dev/null 2>/tmp/restore.stderr || restore_failure "$?"
export PGOPTIONS="-c default_transaction_read_only=on -c statement_timeout=5000"
revision=$(psql -XAtq -h /tmp -U postgres -d sellora_restore_check -v ON_ERROR_STOP=1 \
  -c "SELECT version_num FROM public.alembic_version" 2>/dev/null) || { echo RESTORED_REVISION_UNREADABLE >&2; exit 1; }
[ "$revision" = "$EXPECTED_REVISION" ] || { echo RESTORED_REVISION_MISMATCH >&2; exit 1; }
psql -XAtq -h /tmp -U postgres -d sellora_restore_check -v ON_ERROR_STOP=1 \
  -c "SELECT 1 FROM public.users LIMIT 1; SELECT 1 FROM public.workspaces LIMIT 1;
      SELECT 1 FROM public.orders LIMIT 1; SELECT 1 FROM public.workspace_subscriptions LIMIT 1;" \
  > /dev/null 2>&1 || { echo RESTORED_SCHEMA_SMOKE_FAILED >&2; exit 1; }
printf "restored_revision=%s\nrestored_schema_smoke=PASS\n" "$revision"
'

if ! openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 \
    -pass "file:$key" -in "$archive" |
  docker run --rm -i --pull=never --network none --log-driver=none \
    --user postgres --security-opt no-new-privileges --read-only \
    --memory 768m --memory-swap 768m --cpus 1 \
    --tmpfs /var/lib/postgresql/data:rw,noexec,nosuid,nodev,size=512m,mode=1777 \
    --tmpfs /tmp:rw,noexec,nosuid,nodev,size=16m,mode=1777 \
    -e PGDATA=/var/lib/postgresql/data/restore -e "EXPECTED_REVISION=$expected_revision" \
    --entrypoint sh "$image_id" -c "$restore_command"
then
  fail RESTORE_CHECK_FAILED
fi

printf 'archive=%s\noffhost_verified_at_utc=%s\nencrypted_sha256_match=PASS\npostgres_image=%s\nrestore_check=PASS\n' \
  "$filename" "$verified_at" "$image_id"
