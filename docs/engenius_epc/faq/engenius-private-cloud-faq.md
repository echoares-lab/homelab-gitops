> For the complete documentation index, see [llms.txt](https://doc.engenius.ai/llms.txt). Markdown versions of documentation pages are available by appending `.md` to page URLs; this page is available as [Markdown](https://doc.engenius.ai/home-epc-faq/engenius-private-cloud-faq.md).

# EnGenius Private Cloud FAQ

### 1. What is EPC?

EnGenius Private Cloud (EPC) is a management platform for EnGenius network solutions. EPC can be installed on an on-premises server or virtual machine, ensuring the security of sensitive data, such as customer profiles and client credentials. With its multi-tenant architecture and flexible features, EPC enables MSPs and ISPs to efficiently manage large-scale networks and expand their services across the internet easily.&#x20;

EPC is a docker container basis application which can be run in most of standard Linux distributions. Following is the suggested OS environment for EPC:&#x20;

* Ubuntu: 20.04.3 LTS(Server)&#x20;
* Debian: 10.6&#x20;

Note: `sudo` is required before EPC installation.&#x20;

### 2. Is EPC free?

EPC is free for local network management with basic functions. However, additional licenses are required to enable advanced features or to manage networks across the internet.

### 3. What’s the hardware requirements of EPC?

Depends on how many devices user would like to manage. Following are some examples for reference:&#x20;

| Device Quantity  | 100                                                                                             | 3,000                                                                                            |
| ---------------- | ----------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| Requirements     | <ul><li>1 core CPU (Intel i3, AMD R3 or above)  </li><li>2GB ram  </li><li>20GB HDD  </li></ul> | <ul><li>8 core CPU (Intel i3, AMD R3 or above)  </li><li>32GB ram  </li><li>30GB HDD  </li></ul> |

EPC can manage up to 3,000 devices, but it currently does not support ARM-based CPUs.&#x20;

### 4. Can EPC install in VM on AWS, Azure, or GCP?

Yes. &#x20;

However, some mail servers may block SMTP messages from public cloud services. Additional rules or settings might be required on the mail server to ensure system emails for EPC are delivered. Alternatively, choosing the mail service provided by your cloud provider could help resolve the issue.&#x20;

### 5. How EPC manage devices across internet?&#x20;

FitRegister is a Cloud based service help to bridge devices deployed anywhere in internet with EPC. To enable FitRegister service, EPC Connect License is required.&#x20;

### 6. How can I enable advanced features on EPC?&#x20;

Advanced features, such as device Pro features, EPC HA/backup requires extra license to enable. And EPC leverages EnGenius Cloud to manage all advanced licenses.&#x20;

To register EPC on EnGenius Cloud and get licenses assigned, EPC Connect License is required.&#x20;

### 7. What will happen when license expired?&#x20;

Device Pro Features&#x20;

Once the license expires, all devices will continue to operate with the functions and configurations that were applied prior to expiration. However, any new configuration changes made after the license expiration will not take effect, and the EPC will stop collecting data and statistics from devices without an active license.&#x20;

To restore the management of those devices, user can either add new license to device or change Org feature plan to basic, which disables the advanced features.&#x20;

For advanced features for EPC platform, function will stop working when license expired.&#x20;

### 8. What EnGenius Device can EPC manage?&#x20;

* EnGenius Cloud Devices
  * Access Points: ECW, ECW-Lite series&#x20;
  * Ethernet Switches: ECS,  ECS-Lite series&#x20;
* Fit Devices&#x20;
  * Access Points/Ethernet Switches: EWS-Fit series&#x20;

### 9. Why EPC requires extra “Pairing” process for devices before managing it?&#x20;

Different from EnGenius Cloud, EPC allows user to create multiple management platforms (Or even legacy EnGenius management platforms) within a network, Pairing function help to make sure which is the correct controller for the device management.&#x20;


---

# Agent Instructions
This documentation is published with GitBook. GitBook is the documentation platform designed so that both humans and AI agents can read, navigate, and reason over technical content effectively. Learn more at gitbook.com.

## Querying This Documentation
If you need additional information that is not directly available in this page, you can query the documentation dynamically by asking a question.

Perform an HTTP GET request on the current page URL with the `ask` query parameter, and the optional `goal` query parameter:

```
GET https://doc.engenius.ai/home-epc-faq/engenius-private-cloud-faq.md?ask=<question>&goal=<endgoal>
```

`ask` is the immediate question: it should be specific, self-contained, and written in natural language.
`goal` is optional and describes the broader end goal you are ultimately trying to accomplish on behalf of the user. GitBook uses it to tailor the answer towards what is most useful for that goal.

The response will contain a direct answer to the question and relevant excerpts and sources from the documentation.

Use this mechanism when the answer is not explicitly present in the current page, you need clarification or additional context, or you want to retrieve related documentation sections.
