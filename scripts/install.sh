#!/bin/bash

set -ex

SKIP_PROMPTS=0

help() {
    echo "Usage: install.sh [options...]"
    echo "  -h, --help, help     (-) Show this help message and exit"
    echo "  -y, --yes            (default=false) Skip installation prompt"
}

# parse program args and options
while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help|help)
            help
            exit 0
            ;;
        -y|--yes)
            SKIP_PROMPTS=1
            ;;
        *)
            echo "Unknown option: $1"
            help
            exit 1
            ;;
    esac
    shift
done


### Installation ###
function os_name_match()
{
  local name="$1"
  [[ "$(uname)" == "$name" ]]
}

function os_is_macos()
{
  os_name_match "Darwin"
}

function os_is_linux()
{
  os_name_match "Linux"
}

function update_package_manager()
{
  echo "Updating os package manager..."
  if os_is_macos; then
    brew update
  elif os_is_linux; then
    sudo apt update -y
  fi
}

function install_python3.10()
{
  if os_is_macos; then
    brew install python@3.10

  elif os_is_linux; then
    sudo apt install software-properties-common -y
    sudo add-apt-repository -y ppa:deadsnakes/ppa
    sudo apt update -y
    sudo apt install -y python3.10
  fi
}

function os_is_wsl2()
{
  grep -q "microsoft" /proc/version && grep -q "WSL2" /proc/version
}

function ensure_installed()
{
  local exec_name="$1"
  local install_exec_func="$2"

  if ! which "$exec_name" >/dev/null; then
    echo "$exec_name is either not installed or its parent directory is not in your \$PATH."
    if [[ "$SKIP_PROMPTS" -ne 1 ]]; then
      read -p "Do you want to install it now? [Y/n] " choice
      if [[ "$choice" != "Y" && "$choice" != "y" ]]; then
        echo "Install $exec_name on your own and come over here later, Good Bye..."
        exit 0
      fi
    fi
    echo "Installing $exec_name..."
    "$install_exec_func"
  fi
}

function create_venv() {
    local venv_dir="$1"
    # Remove existing virtual environment if present
    if [ -d "$venv_dir" ]; then
        echo "Removing existing virtual environment..."
        rm -rf "$venv_dir"
    fi

    echo "Creating virtual environment..."
    python3.10 -m venv "$venv_dir"
}

function install_poetry_project() {
    pip install -U pip setuptools
    pip install poetry

    echo "Installing the project with Poetry..."
    poetry install
}

function create_exec_symlink() {
    local prog_name="$1"
    local venv_dir="$2"
    
    # Create a symbolic link to the edenredtools command in /usr/local/bin
    echo "Creating symbolic link to /usr/local/bin/$prog_name..."
    sudo ln -sf "$venv_dir/bin/$prog_name" "/usr/local/bin/$prog_name"
}

function generate_shell_completions() {
    local prog_name="$1"

    # Generate command completions
    if [ -f ~/.bashrc ]; then
        echo "Generating autocompletion script for bash"
        _EDENREDTOOLS_COMPLETE=bash_source $prog_name > ~/.$prog_name-complete.bash
        echo ". ~/.$prog_name-complete.bash" >> ~/.bashrc
    fi

    if [ -f ~/.zshrc ]; then
        echo "Generating autocompletion script for zsh"
        _EDENREDTOOLS_COMPLETE=zsh_source $prog_name > ~/.$prog_name-complete.zsh
        echo ". ~/.$prog_name-complete.zsh" >> ~/.zshrc
    fi

    echo "Installation complete. You can now run '$prog_name' from anywhere."
    echo "You may need to source your current shell again to load autocompletions."%
}


function main() {
    local prog_name="$1"
    local venv_dir="$2"

    update_package_manager
    ensure_installed "python3.10" "install_python3.10"
    create_venv "$venv_dir"
    source "$venv_dir/bin/activate"
    install_poetry_project
    create_exec_symlink "$prog_name" "$venv_dir"
    generate_shell_completions "$prog_name"
}

### Constants ###
PROG_NAME="edenredtools"
SCRIPTS_DIR=$(dirname "$(realpath "${BASH_SOURCE[0]}")")
PROJECT_ROOT=$(dirname "$SCRIPTS_DIR")
VENV_DIR="$PROJECT_ROOT/.venv"

### main ###
main "$PROG_NAME" "$VENV_DIR"

