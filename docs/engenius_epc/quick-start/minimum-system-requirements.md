> For the complete documentation index, see [llms.txt](https://doc.engenius.ai/llms.txt). Markdown versions of documentation pages are available by appending `.md` to page URLs; this page is available as [Markdown](https://doc.engenius.ai/home-epc-quick-start-guide/minimum-system-requirements.md).

# Minimum System Requirements

## <mark style="color:blue;">1. Hardware Requirements</mark>

The more devices managed by the EPC, the greater the required hardware capacity. Please refer to the following guidelines to select a suitable hardware for your EPC&#x20;

**PC/server with Minimum Specs:**

Platform: X86-based PC, Server, or Cloud Instance

{% hint style="info" %}
Support for EPC in ARM-based platform is still under survey.
{% endhint %}

| Device Quantity | 100                                                                                          | 3,000                                                                                         |
| --------------- | -------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| Requirements    | <ul><li>1 core CPU (Intel i3, AMD R3 or above) </li><li>2GB ram </li><li>20GB HDD </li></ul> | <ul><li>8 core CPU (Intel i3, AMD R3 or above) </li><li>32GB ram </li><li>30GB HDD </li></ul> |

**Software needed**

1. EPC is packaged as a docker container which can be run in most of standard Linux distributions.
2. VM with Linux installed should be able to install EPC with simple commands.
3. Windows 11 64bit 22H2 or later with WSL2 enabled can also install docker desktop to run EPC.

{% hint style="info" %}
Follow [WSL installation guide](https://learn.microsoft.com/en-us/windows/wsl/install) to prepare operation environment.
{% endhint %}

## <mark style="color:blue;">2. Operating System Requirements</mark>

EPC is packaged as a docker container which can be run in most of standard Linux distributions.&#x20;

**Suggested OS environment:**&#x20;

* Ubuntu: 20.04.3 LTS(Server) or above&#x20;
* Debian: 10.6 or above&#x20;

{% hint style="info" %}
Note 1: `sudo` is required before EPC installation.

Note 2: System time change is not allowed after EPC was installed.
{% endhint %}

## <mark style="color:blue;">3. Device firmware version requirement</mark>&#x20;

To be managed by EPC, device firmware must be greater than following versions:&#x20;

| Type         | Model            | Minimum firmware version |
| ------------ | ---------------- | ------------------------ |
| Cloud AP     | ECW-Lite         | v1.x.0                   |
| Cloud AP     | ECW120/160       | v1.3.75                  |
| Cloud AP     | All other models | v1.x.56                  |
| Fit AP       | EWS-Fit          | v1.x.65                  |
| Cloud Switch | ECS-Lite         | v1.1.0                   |
| Cloud Switch | ECS              | v1.2.60                  |
| Fit Switch   | EWS-Fit          | v2.0.10                  |

## <mark style="color:blue;">4. Internet Connection</mark>

Although EPC supports on-premises operating, but internet is required for following operations:&#x20;

* EPC installation.&#x20;
* Use FitRegister function to manage internet devices.&#x20;
* Enable Cloud registration for license assignment and data backup.&#x20;


---

# Agent Instructions
This documentation is published with GitBook. GitBook is the documentation platform designed so that both humans and AI agents can read, navigate, and reason over technical content effectively. Learn more at gitbook.com.

## Querying This Documentation
If you need additional information that is not directly available in this page, you can query the documentation dynamically by asking a question.

Perform an HTTP GET request on the current page URL with the `ask` query parameter, and the optional `goal` query parameter:

```
GET https://doc.engenius.ai/home-epc-quick-start-guide/minimum-system-requirements.md?ask=<question>&goal=<endgoal>
```

`ask` is the immediate question: it should be specific, self-contained, and written in natural language.
`goal` is optional and describes the broader end goal you are ultimately trying to accomplish on behalf of the user. GitBook uses it to tailor the answer towards what is most useful for that goal.

The response will contain a direct answer to the question and relevant excerpts and sources from the documentation.

Use this mechanism when the answer is not explicitly present in the current page, you need clarification or additional context, or you want to retrieve related documentation sections.
