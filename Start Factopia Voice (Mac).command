#!/bin/bash
# Starts Factopia Voice. The first run sets up Python and downloads the voice model.
cd "$(dirname "$0")" || exit 1
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
if ! command -v uv >/dev/null 2>&1; then
  echo "First run: installing a small helper (uv) that sets up Python for this app..."
  if ! curl -LsSf https://astral.sh/uv/install.sh | sh; then
    echo "Could not install the helper. Check the internet connection and try again."
    read -r -p "Press Enter to close."
    exit 1
  fi
fi
echo "Starting Factopia Voice (the first start can take a few minutes)..."
uv run --python 3.12 --no-project --with-requirements requirements.txt python -m factopia_voice
status=$?
if [ $status -ne 0 ]; then
  echo
  echo "Factopia Voice stopped with an error (code $status). Copy the text above if you need help."
  read -r -p "Press Enter to close."
fi
