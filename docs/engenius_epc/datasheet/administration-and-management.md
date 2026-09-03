> For the complete documentation index, see [llms.txt](https://doc.engenius.ai/llms.txt). Markdown versions of documentation pages are available by appending `.md` to page URLs; this page is available as [Markdown](https://doc.engenius.ai/home-epc-datasheet/administration-and-management.md).

# Administration and Management

## <mark style="color:blue;">Multi-Tenancy Support</mark>

Manage multiple sites, stores, or business units from a single EPC interface while keeping each organization’s settings completely independent. Departments or clients can be isolated through separate policies and resource pools, making EPC ideal for service providers or enterprises with distinct internal divisions.

<div align="left"><figure><img src="/files/oBLig9yBhfwrEv4EDfoE" alt="" width="375"><figcaption></figcaption></figure></div>

## <mark style="color:blue;">Scalable Management — Up to 3,000 Devices per EPC</mark>

EPC delivers a scalable architecture that grows with your organization. This scalability extends across distributed networks, enabling consistent management practices and unified policies across diverse environments—whether across regions or between business units.<br>

## <mark style="color:blue;">Integration with EnGenius Cloud</mark>

The EPC platform’s integration with EnGenius Cloud provides real-time synchronization of settings and centralized control across all network environments. This hybrid approach provides flexibility in network design and management, accommodating various network architectures within a single management framework.

* EnGenius Cloud users can access EPC from the EnGenius Cloud Interface.
* Connects with EnGenius Cloud for pro-features and license management.
* Enables backup and redundancy options through cloud integration.

## <mark style="color:blue;">Remote Management</mark>

Administrators can monitor, configure, and troubleshoot devices from anywhere through EPC’s secure web interface, minimizing the need for on-site visits and accelerating issue resolution.

## <mark style="color:blue;">Failover Protection</mark>

EPC ensures business continuity through EnGenius Cloud (EC) and FitRegister integration for essential backups. This built-in failover capability secures license keys and device registrations, providing a safeguard that enables rapid recovery and uninterrupted operations in the event of a disruption.


---

# Agent Instructions
This documentation is published with GitBook. GitBook is the documentation platform designed so that both humans and AI agents can read, navigate, and reason over technical content effectively. Learn more at gitbook.com.

## Querying This Documentation
If you need additional information that is not directly available in this page, you can query the documentation dynamically by asking a question.

Perform an HTTP GET request on the current page URL with the `ask` query parameter, and the optional `goal` query parameter:

```
GET https://doc.engenius.ai/home-epc-datasheet/administration-and-management.md?ask=<question>&goal=<endgoal>
```

`ask` is the immediate question: it should be specific, self-contained, and written in natural language.
`goal` is optional and describes the broader end goal you are ultimately trying to accomplish on behalf of the user. GitBook uses it to tailor the answer towards what is most useful for that goal.

The response will contain a direct answer to the question and relevant excerpts and sources from the documentation.

Use this mechanism when the answer is not explicitly present in the current page, you need clarification or additional context, or you want to retrieve related documentation sections.
