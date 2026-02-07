#!/bin/bash

# This script automates the process of setting up and running the Meetily project locally on macOS.
# It checks for prerequisites and installs them if they are missing.

set -e

echo "🚀 Starting Meetily project setup..."

# --- Prerequisite Checks ---

# 1. Check for Homebrew
if ! command -v brew &> /dev/null; then
    echo "❌ Homebrew is not installed. Please install Homebrew first by following the instructions at https://brew.sh/"
    exit 1
fi
echo "✅ Homebrew found."

# 2. Check for pnpm
if ! command -v pnpm &> /dev/null; then
    echo "🟡 pnpm not found. Installing pnpm globally via npm..."
    if ! command -v npm &> /dev/null; then
        echo "❌ npm is not installed. Please install Node.js (which includes npm) first."
        exit 1
    fi
    npm install -g pnpm
    echo "✅ pnpm installed."
else
    echo "✅ pnpm found."
fi

# 3. Check for Rust (cargo)
if ! command -v cargo &> /dev/null; then
    echo "🟡 Rust (cargo) not found. Installing Rust via rustup..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    # Source the cargo environment script to update the PATH for the current session
    source "$HOME/.cargo/env"
    echo "✅ Rust installed."
else
    echo "✅ Rust (cargo) found."
    source "$HOME/.cargo/env" # Ensure PATH is set for the current shell
fi

# 4. Check for CMake
if ! command -v cmake &> /dev/null; then
    echo "🟡 CMake not found. Installing CMake via Homebrew..."
    brew install cmake
    echo "✅ CMake installed."
else
    echo "✅ CMake found."
fi

# --- Important Manual Step ---
echo "---------------------------------------------------------------------"
echo "--- Assuming Xcode is installed, proceeding with the build... ---"
echo "---------------------------------------------------------------------"


# --- Run the Application ---

# Navigate to the frontend directory
echo "📂 Navigating to the 'frontend' directory..."
if [ ! -d "frontend" ]; then
    echo "❌ 'frontend' directory not found. Please run this script from the project's root directory."
    exit 1
fi
cd frontend

# Make the run script executable
chmod +x ./clean_run.sh

echo "🏃‍♀️ Running the application... This will take a while for the first time."
./clean_run.sh

echo "🎉 Setup and launch script finished."
