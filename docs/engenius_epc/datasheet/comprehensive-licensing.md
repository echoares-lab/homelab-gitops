> For the complete documentation index, see [llms.txt](https://doc.engenius.ai/llms.txt). Markdown versions of documentation pages are available by appending `.md` to page URLs; this page is available as [Markdown](https://doc.engenius.ai/home-epc-datasheet/comprehensive-licensing.md).

# Comprehensive Licensing

EPC features a flexible licensing model that balances essential functionality with advanced capabilities to fit organizations of all sizes.

## <mark style="color:blue;">Basic Features - Free for All Users</mark>

EPC provides core network management tools—such as device monitoring, network configuration, and basic security—completely free of charge.\
These essential capabilities allow small businesses and startups to manage and secure their networks effectively without additional costs.<br>

## <mark style="color:blue;">Advanced Features — Pro Licenses</mark>

As network environments become more complex, EPC offers a range of **Pro licenses** that unlock enhanced performance, advanced security, and greater scalability.<br>

### 1. Connect License

The **Connect License** enables advanced cloud-linked functionality:

* **Cloud synchronization** – EPC connects to the EnGenius Cloud through the FitRegister service to retrieve the latest firmware and maintain a local firmware database.
* **Automatic firmware upgrade** – When enabled, EPC synchronizes with the Cloud and schedules automatic upgrades for managed devices. This feature is only available with an active Connect License.
* **Scheduled firmware sync** – EPC can automatically synchronize with the Cloud database (for example, daily at 02:00) to download the latest firmware files.
* **Remote management & analytics** – Access EPC remotely through EnGenius Cloud for centralized management and deeper network insights.

### 2. Device Pro License

The **Device Pro License** adds advanced per-device capabilities.\
The **Basic plan** requires no license, but devices under the **Pro plan** must be licensed individually to unlock premium features designed for enhanced control, security, and analytics.


---

# Agent Instructions
This documentation is published with GitBook. GitBook is the documentation platform designed so that both humans and AI agents can read, navigate, and reason over technical content effectively. Learn more at gitbook.com.

## Querying This Documentation
If you need additional information that is not directly available in this page, you can query the documentation dynamically by asking a question.

Perform an HTTP GET request on the current page URL with the `ask` query parameter, and the optional `goal` query parameter:

```
GET https://doc.engenius.ai/home-epc-datasheet/comprehensive-licensing.md?ask=<question>&goal=<endgoal>
```

`ask` is the immediate question: it should be specific, self-contained, and written in natural language.
`goal` is optional and describes the broader end goal you are ultimately trying to accomplish on behalf of the user. GitBook uses it to tailor the answer towards what is most useful for that goal.

The response will contain a direct answer to the question and relevant excerpts and sources from the documentation.

Use this mechanism when the answer is not explicitly present in the current page, you need clarification or additional context, or you want to retrieve related documentation sections.
