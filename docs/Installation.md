<picture>
  <source media="(prefers-color-scheme: dark)" srcset="../assets/01_Logo/Project-Logo.png">
  <source media="(prefers-color-scheme: light)" srcset="../assets/01_Logo/Project-Logo.png">
  <img src="../assets/01_Logo/Project-Logo.png" alt="Logo of OnTheSpot" width="200">
</picture>

<br>

# Installation

- [Installation](#installation)
  - [1. Install via GitHub Release Packages (Recommended)](#1-install-via-github-release-packages-recommended)
  - [2. Build the Package Locally via Script](#2-build-the-package-locally-via-script)

<br>

## 1. Install via GitHub Release Packages (Recommended)

This is the easiest way to get started.

> [!NOTE]
> Always download the release that matches your operating system to ensure compatibility.

1. **Download the Latest Release**

   - Visit our [GitHub Releases Page](https://github.com/justin025/onthespot/releases).
   - Look for the latest version suitable for your operating system:
     - **Windows Users**: Download the `.exe` file.
     - **MacOS Users**: Download the `.dmg` or `.zip` file.
     - **Linux Users**: Download the `.AppImage` or `.deb` file.

2. **Install OnTheSpot**

   > [!TIP]
   > For macOS, if you encounter security warnings, right-click the app and select "Open" from the context menu to bypass the gatekeeper.

   - **Windows**: Run the downloaded `.exe` file and follow the on-screen instructions.
   - **macOS**: Open the `.dmg` or extract the `.zip`, then drag the `OnTheSpot.app` into your `Applications` folder.
   - **Linux**: Make the `.AppImage` executable and run it, or install the `.deb` package using your package manager.

3. **Launch OnTheSpot**

   - Open the application from your Start Menu, Applications folder, or Applications menu.

> [!CAUTION]
> For Linux users, you may need to install additional dependencies like `ffmpeg` if they are not bundled with your distribution.

[GIF Image how to Download]

## 2. Build the Package Locally via Script

If you prefer to build OnTheSpot yourself, follow these steps.

1. **Download the Source Code**

   > [!IMPORTANT]
   > Ensure you have **Git** installed and properly configured before cloning the repository.

   - Open your command line interface (Terminal or Command Prompt).
   - Run the following commands:

     ```bash
     git clone https://github.com/justin025/onthespot.git
     cd onthespot
     ```

2. **Run the Build Script for Your Operating System**

   - **Windows**: Double-click [`Windows-Build.bat`](scripts/Windows-Build.bat) or run it in Command Prompt.
   - **MacOS**: Run [`Mac-Build.sh`](scripts/Mac-Build.sh) in Terminal with `./Mac-Build.sh`.
   - **Linux**: Run [`Linux-Build.sh`](scripts/Linux-Build.sh) in Terminal with `./Linux-Build.sh`.
   - **Linux AppImage**: Run [`AppImage-Build.sh`](scripts/AppImage-Build.sh) in Terminal with `./AppImage-Build.sh`.

   > [!WARNING]
   > Make sure to run the correct script for your platform to avoid any build failures.

3. **Install and Launch OnTheSpot**

   > [!TIP]
   > After building, the application will be located in the `dist` folder. Be sure to follow installation steps based on your operating system, as mentioned in the first section.

   - After the build is complete, you'll find the application in the `dist` folder.
   - Follow the installation steps similar to **Option 1** for your operating system.

[GIF Image how to Download]

<br>

---

> [⮝ **Go to the Basic Usage** ⮝](Basic-Usage.md)

---

> [⮝ **Go back to the ReadMe** ⮝](../)

---
