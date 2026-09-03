> For the complete documentation index, see [llms.txt](https://doc.engenius.ai/llms.txt). Markdown versions of documentation pages are available by appending `.md` to page URLs; this page is available as [Markdown](https://doc.engenius.ai/home-epc-config-guide/migrate-vfitcon-to-epc/migration-scenarios.md).

# Migration Scenarios

EnGenius devices can automatically discover and associate with controllers.

* If no specific controller IP is configured locally, devices will search for a new controller.
* To ensure a **smooth transition**, the migration process depends on whether EPC and devices are in the **same subnet** or **different subnets**.

Both EPC and vFitCon support managing devices located in different subnets (or even over the Internet). This relies on the FitRegister service to bind devices with their controller. However, the controller’s IP address may be altered by Network Address Translation (NAT) across subnets. Therefore, an additional authentication mechanism is required to prevent devices from being hijacked by unauthorized controllers.

vFitCon **v1.3.18** introduces EPC serial number authentication. To migrate a vFitCon that manages devices across different subnets, it is necessary to upgrade to this version in advance.


---

# Agent Instructions
This documentation is published with GitBook. GitBook is the documentation platform designed so that both humans and AI agents can read, navigate, and reason over technical content effectively. Learn more at gitbook.com.

## Querying This Documentation
If you need additional information that is not directly available in this page, you can query the documentation dynamically by asking a question.

Perform an HTTP GET request on the current page URL with the `ask` query parameter, and the optional `goal` query parameter:

```
GET https://doc.engenius.ai/home-epc-config-guide/migrate-vfitcon-to-epc/migration-scenarios.md?ask=<question>&goal=<endgoal>
```

`ask` is the immediate question: it should be specific, self-contained, and written in natural language.
`goal` is optional and describes the broader end goal you are ultimately trying to accomplish on behalf of the user. GitBook uses it to tailor the answer towards what is most useful for that goal.

The response will contain a direct answer to the question and relevant excerpts and sources from the documentation.

Use this mechanism when the answer is not explicitly present in the current page, you need clarification or additional context, or you want to retrieve related documentation sections.
