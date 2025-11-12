#!/bin/bash

# Set up Python virtual environment with direnv

# Exit on any error
set -e

# Step 1: Create virtual environment
echo "[+] Creating virtual environment in ./venv"
python3 -m venv venv

# Step 2: Check if direnv is installed, install if not
if ! command -v direnv >/dev/null 2>&1; then
    echo "[!] direnv not found. Attempting to install direnv..."
    if command -v brew >/dev/null 2>&1; then
        brew install direnv
    elif command -v apt-get >/dev/null 2>&1; then
        sudo apt-get update && sudo apt-get install -y direnv
    elif command -v dnf >/dev/null 2>&1; then
        sudo dnf install -y direnv
    else
        echo "Please install direnv manually from https://direnv.net/docs/installation.html"
        exit 1
    fi
else
    echo "[+] direnv is already installed."
fi

# Step 3: Create .envrc to auto-activate venv with direnv
echo "[+] Creating .envrc with activation script"
echo 'source venv/bin/activate' > .envrc

# Step 4: Allow direnv to load .envrc
echo "[+] Allowing direnv to load .envrc"
direnv allow

# Step 5: Prompt user to configure direnv in their shell if not already done
SHELL_NAME=$(basename "$SHELL")
echo ""
echo "[!] To enable direnv in your shell, add the following to your shell configuration file if you haven't already:"
if [ "$SHELL_NAME" = "zsh" ]; then
    echo '  eval "$(direnv hook zsh)"'
elif [ "$SHELL_NAME" = "bash" ]; then
    echo '  eval "$(direnv hook bash)"'
elif [ "$SHELL_NAME" = "fish" ]; then
    echo '  eval (direnv hook fish)'
else
    echo "  eval \"\$(direnv hook $SHELL_NAME)\""
fi
echo "Then restart your shell or source the config file."

echo "[✓] Setup complete. direnv should now auto-activate your venv in this directory."
