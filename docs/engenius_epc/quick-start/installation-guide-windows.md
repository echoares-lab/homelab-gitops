> For the complete documentation index, see [llms.txt](https://doc.engenius.ai/llms.txt). Markdown versions of documentation pages are available by appending `.md` to page URLs; this page is available as [Markdown](https://doc.engenius.ai/home-epc-quick-start-guide/installation-and-onboarding/installation-guide-windows.md).

# Installation Guide - Windows

This guide will walk you through installing **EPC** on a Windows system.

Please make sure you have **Administrator privileges** before starting.

## <mark style="color:blue;">1. Preparation</mark>

1.1 - Download the latest EPC installer from the official link:

<table data-header-hidden><thead><tr><th width="128"></th><th></th></tr></thead><tbody><tr><td>EPC version </td><td>Download link</td></tr><tr><td>V1.8.7</td><td><a href="https://virtualbox-epc.s3.us-west-2.amazonaws.com/1.8.7/EPC_Installer.exe">https://virtualbox-epc.s3.us-west-2.amazonaws.com/1.8.7/EPC_Installer.exe</a></td></tr><tr><td>V1.8.8</td><td><a href="https://virtualbox-epc.s3.us-west-2.amazonaws.com/1.8.8/EPC_Installer.exe">https://virtualbox-epc.s3.us-west-2.amazonaws.com/1.8.8/EPC_Installer.exe</a></td></tr><tr><td>V1.9.0</td><td><a href="https://virtualbox-epc.s3.us-west-2.amazonaws.com/1.9.0/EPC_Installer.exe">https://virtualbox-epc.s3.us-west-2.amazonaws.com/1.9.0/EPC_Installer.exe</a></td></tr></tbody></table>

1.2 - Locate the downloaded file (e.g., `EPC_Installer.exe`) in your **Downloads** folder.

1.3 - **Right-click** the installer and select **Run as administrator**.

{% hint style="info" %}
Windows Defender SmartScreen: \
**Case A – Warning Message**

Sometimes, Windows Defender SmartScreen may recognize the EPC installer as suspicious software.\
This happens because EPC requires [**Windows Subsystem for Linux (WSL)**](https://learn.microsoft.com/en-us/windows/wsl/install), and the installer needs to configure WSL using system commands.

1. Click **More info**.
2. Click **Run anyway** to continue with the installation.

![](/files/2adwEFb6Zp7H2Wkrz8z0)![](/files/iYYYjMWWNs4yXPPr8i0q)
{% endhint %}

{% hint style="info" %}
Windows Defender SmartScreen: \
**Case B – Installer Blocked**

There is another case. Occasionally, Windows Defender SmartScreen would block the installer.

1. Allow app

   1. Select **Allow app**.
   2. Or follow Microsoft’s official instructions to bypass SmartScreen for blocked applications.

      > Reference: *Windows Defender SmartScreen guide* from [Microsoft Support](https://support.microsoft.com/en-us/windows/protection-history-f1e5fd95-09b4-46d1-b8c7-1059a1e09708).

   ⚠️ Note: EPC runs on top of Linux (via WSL). The installer must enable and configure WSL for EPC to work.
2. Use alternative method: [Installation Guide - Linux](https://docs.engenius.ai/epc-quick-start-guide/installation-and-onboarding/installation-guide-linux)
   {% endhint %}

## <mark style="color:blue;">2. Installation</mark>

### 2.1 WSL Check and Installation

1. The installer will check if **Windows Subsystem for Linux (WSL)** is installed.
2. If WSL is not installed, the installer will enable it.
3. You must **restart your computer** when prompted. Select **Yes** to restart.
4. After your system restarts, you must **run the EPC installer again (Run as administrator)** to continue.
5. Once the installer verifies that the environment is ready, it will proceed to the next step.

### 2.2 Continue EPC Installation

1. After confirming the environment in Step 2.1, the installer will automatically proceed with the EPC setup.
2. Enter a name for the virtual machine (default: `EPC`).
3. Choose the **storage location** for virtual machine files (e.g., `D:\ProgramFiles`).
4. Click **Next** to continue.

{% hint style="info" %}
![](/files/r3TvzGsXubr6rOWOYBWG)![](/files/OdBs6zo82bb1QbxAHbum)
{% endhint %}

### 2.3 Installation Complete

1. The installer will copy necessary files and set up the EPC virtual machine.
2. Once installation is complete, you will see a confirmation message:
   * **Virtual Machine Name**: EPC
   * **Storage Location**: your selected folder
3. Click **OK** → **Finish** to exit the setup.\
   Click **Manage EPC in browser** to open the EPC management portal manually.

{% hint style="info" %}
![](/files/B6G71mo9QfEc25sxcnjy)![](/files/ZS5rZurXNqlqnVVEGo9V)
{% endhint %}

## <mark style="color:blue;">3. Open EPC</mark>

Open the following URL in your browser:

```
http://localhost:8080 
```


---

# Agent Instructions
This documentation is published with GitBook. GitBook is the documentation platform designed so that both humans and AI agents can read, navigate, and reason over technical content effectively. Learn more at gitbook.com.

## Querying This Documentation
If you need additional information that is not directly available in this page, you can query the documentation dynamically by asking a question.

Perform an HTTP GET request on the current page URL with the `ask` query parameter, and the optional `goal` query parameter:

```
GET https://doc.engenius.ai/home-epc-quick-start-guide/installation-and-onboarding/installation-guide-windows.md?ask=<question>&goal=<endgoal>
```

`ask` is the immediate question: it should be specific, self-contained, and written in natural language.
`goal` is optional and describes the broader end goal you are ultimately trying to accomplish on behalf of the user. GitBook uses it to tailor the answer towards what is most useful for that goal.

The response will contain a direct answer to the question and relevant excerpts and sources from the documentation.

Use this mechanism when the answer is not explicitly present in the current page, you need clarification or additional context, or you want to retrieve related documentation sections.
