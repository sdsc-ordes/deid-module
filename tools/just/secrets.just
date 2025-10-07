# We assume all encrypted secrets follow the naming pattern {{SECRET_DIR}}/*{{ENC_SUFFIX}}
SECRETS_DIR := "./src/secrets"
DEC_PREFIX := "dec."
root_dir := `git rev-parse --show-toplevel`
export SOPS_AGE_KEY_FILE := "./.sops.agekey"
set shell := ["bash", "-cue"]

# Default recipe to list all recipes.
[private]
default:
    just --list secrets

# Edit an encrypted secrets file in place
edit secret_file:
  @cd {{root_dir}} && \
    sops {{secret_file}}

alias keygen := generate-key
# Create key file to use with sops.
generate-key:
  @echo "Generating key..."
  @cd {{root_dir}} && \
  age-keygen -o {{SOPS_AGE_KEY_FILE}}

# Re-encrypt secrets based on .sops.yaml and rotate data encryption key.
update-keys:
  @echo "Updating keys in secret files"
  @cd {{root_dir}} && \
    fd -E '{{DEC_PREFIX}}*' . {{SECRETS_DIR}} --exec sops updatekeys -y {} && \
    fd -E '{{DEC_PREFIX}}*' . {{SECRETS_DIR}} --exec sops rotate -i {}
  

# see here for usage of sops+age: https://github.com/getsops/sops?tab=readme-ov-file#encrypting-using-age
# Decrypts a secrets file.
decrypt secret_file:
  @echo "Decrypting {{secret_file}}..."
  @cd {{root_dir}} && \
    fbase=$(basename {{secret_file}}) && \
    fdir=$(dirname {{secret_file}}) && \
    sops --age $(grep -oP 'public key: \K(.*)' {{SOPS_AGE_KEY_FILE}}) \
      -d {{secret_file}} \
      > ${fdir}/{{DEC_PREFIX}}${fbase}

# Encrypts a secrets file.
encrypt decrypted_file:
  @echo "Encrypting {{decrypted_file}}..."

  @cd {{root_dir}} && \
    (sops filestatus {{decrypted_file}} 2>/dev/null || exit 0) | \
    grep -q 'encrypted: true' && \
    echo "File is already encrypted." && \
    exit 1 || exit 0

  @cd {{root_dir}} && \
    fbase=$(basename {{decrypted_file}}) && \
    fdir=$(dirname {{decrypted_file}}) && \
    sops -e {{decrypted_file}} > "${fdir}/${fbase##{{DEC_PREFIX}}}" && \
    rm {{decrypted_file}}

# Runs input command with secrets in the environment.
exec-env cmd:
  @echo "Running command {{cmd}} with environment secrets..."
  @cd {{root_dir}} && \
    sops \
      --age $(grep -oP 'public key: \K(.*)' {{SOPS_AGE_KEY_FILE}}) \
      exec-env {{SECRETS_DIR}}/secrets.env '{{cmd}}'

alias apply := deploy
# Deploy decrypted secrets to cluster.
deploy:
  @cd "{{root_dir}}" && \
  for enc in {{SECRETS_DIR}}/*yaml; do \
    sops exec-file ${enc} 'kubectl apply -f {}'; \
  done
