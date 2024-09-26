<picture>
  <source media="(prefers-color-scheme: dark)" srcset="../assets/01_Logo/Project-Logo.png">
  <source media="(prefers-color-scheme: light)" srcset="../assets/01_Logo/Project-Logo.png">
  <img src="../assets/01_Logo/Project-Logo.png" alt="Logo of OnTheSpot" width="200">
</picture>

<br>

# Installation

- [Installation](#installation)
  - [1. Install via GitHub Releases (Recommended)](#1-install-via-github-releases-recommended)
  - [2. Build the Package Locally via Script](#2-build-the-package-locally-via-script)

<br>

## 1. Install via GitHub Releases (Recommended)

This is the easiest way to get started.


1. **Download the Latest Release**

   - Visit our [GitHub Releases Page](https://github.com/justin025/onthespot/releases).
   - Look for the latest version suitable for your operating system:
     - **Windows Users**: Download the `.exe` file.
     - **MacOS Users**: Download the `.dmg` or `.zip` file.
     - **Linux Users**: Download the `.AppImage` or `tar.gz` file.

2. **Install OnTheSpot**

   - **Windows**: Run the downloaded `.exe`.
   - **macOS**: Open the `.dmg` and drag `OnTheSpot.app` into your `Applications` folder. 
   - **Linux**: Make the `.AppImage` executable and run it, alternatively extract the tar.gz and execute the binary.

> [!TIP]
> For macOS, if you encounter security warnings, right-click the app and select "Open" from the context menu to bypass the gatekeeper.

3. **Launch OnTheSpot**

   - Open the application from your Downloads folder or Applications menu.

## 2. Build the Package Locally via Script

If you prefer to build OnTheSpot yourself, follow these steps.

1. **Download the Source Code**

   - The source code can be downloaded through github or through the commands below:

     ```bash
     git clone https://github.com/justin025/onthespot
     cd onthespot
     ```

2. **Run the Build Script for Your Operating System**

   - **Windows**: Double-click [`Windows-Build.bat`](scripts/Windows-Build.bat) or run it in Command Prompt.
   - **MacOS**: Run [`Mac-Build.sh`](scripts/Mac-Build.sh) in Terminal with `./scripts/Mac-Build.sh`.
   - **Linux**: Run [`Linux-Build.sh`](scripts/Linux-Build.sh) in Terminal with `./scripts/Linux-Build.sh`.
   - **Linux AppImage**: Run [`AppImage-Build.sh`](scripts/AppImage-Build.sh) in Terminal with `./scripts/AppImage-Build.sh`.

   > [!WARNING]
   > Make sure to run the correct script for your platform to avoid any build failures.

3. **Install and Launch OnTheSpot**

   > [!TIP]
   > After building, the application will be located in the `dist` folder. Be sure to follow installation steps based on your operating system.

[GIF Image how to Download]

<br>

---

> [⮝ **Go to the Basic Usage** ⮝](Basic-Usage.md)

---

> [⮝ **Go back to the ReadMe** ⮝](../)

---
