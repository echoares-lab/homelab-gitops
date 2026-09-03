> For the complete documentation index, see [llms.txt](https://doc.engenius.ai/llms.txt). Markdown versions of documentation pages are available by appending `.md` to page URLs; this page is available as [Markdown](https://doc.engenius.ai/epc-release-notes/epc-release-notes.md).

# EPC Release Notes

## v1.9.0

### \[New Feature]

* Support TACACS+ to provide a consistent and seamless login experience across enterprise systems, eliminating the need to remember additional usernames or passwords.
* Support Syslog Server (SIEM) to allow the EPC system to stably and securely forward its internal system logs, and audits to a centralized third-party logging infrastructure.
* Support EPC registration on the EnGenius Cloud Japan site.

## v1.8.8

### \[Issue Fixed]

* [MongoDB Server Security Update](https://doc.engenius.ai/engenius-cloud-esp/~/changes/36/security-advisories/mongodb-server-security-update-december-2025) for CVE-2025-14847

## v1.8.7

### \[New Feature]&#x20;

* Support Fast Handover for access points to improve client roaming performance.
* Support One-click Upgrade (OCU) for smoother EPC system upgrade workflow.
* Support Switch Configuration Template to help users apply standard profiles quickly.
* Support Fit series, Cloud-Lite series models, and some Cloud series models. including ECW510/ECW515/ECW520.
* Support migration from virtual FitCon to EPC.
* Add loader when accessing EPC web page to prevent temporary blank pages.
* Modify left-side function tree to match EnGenius Cloud design for consistent UX.

### \[Issue Fixed]

* Fix Dashboard showing empty Throughput and Traffic data when using month filter.
* Fix some devices thumbnail, port diagram, and VLAN diagram display errors.
* Fix OCU view lock to prevent users from operating pages during system upgrade.
* Fix Frontdesk user unable to display the voucher service page correctly.
* Fix WPA2/WPA3-Enterprise options showing incorrectly for organizations using Basic AP feature plan.

## v1.7.2 (Beta)

### \[New Feature]

* Support WiFi 7 access points and 6GHz radio related configurations.
* Support device auto-upgrade function to latest EnGenius firmware revision.
* Support **Forget Password** function, allowing user reset password when it was missed.

### \[Issue Fixed]

* Fix Inventory list cannot be filtered by model type.

## v1.6.9 (Beta)

First release


---

# Agent Instructions
This documentation is published with GitBook. GitBook is the documentation platform designed so that both humans and AI agents can read, navigate, and reason over technical content effectively. Learn more at gitbook.com.

## Querying This Documentation
If you need additional information that is not directly available in this page, you can query the documentation dynamically by asking a question.

Perform an HTTP GET request on the current page URL with the `ask` query parameter, and the optional `goal` query parameter:

```
GET https://doc.engenius.ai/epc-release-notes/epc-release-notes.md?ask=<question>&goal=<endgoal>
```

`ask` is the immediate question: it should be specific, self-contained, and written in natural language.
`goal` is optional and describes the broader end goal you are ultimately trying to accomplish on behalf of the user. GitBook uses it to tailor the answer towards what is most useful for that goal.

The response will contain a direct answer to the question and relevant excerpts and sources from the documentation.

Use this mechanism when the answer is not explicitly present in the current page, you need clarification or additional context, or you want to retrieve related documentation sections.
