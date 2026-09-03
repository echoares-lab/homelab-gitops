> For the complete documentation index, see [llms.txt](https://doc.engenius.ai/llms.txt). Markdown versions of documentation pages are available by appending `.md` to page URLs; this page is available as [Markdown](https://doc.engenius.ai/home-epc-config-guide/migrate-vfitcon-to-epc/migration-scenarios/case-1-epc-deployed-in-same-subnet-with-devices.md).

# Case 1: EPC deployed in SAME subnet with devices

1. Refer to[ EPC quick start guide](https://docs.engenius.ai/epc-quick-start-guide/installation-and-onboarding) to install EPC
2. Login to **vFitCon** and go to **System > Backup & Restore > System Backup**\
   Click **Backup** button to backup vFitCon system configurations.<br>

<figure><img src="/files/3ESEBfB56HdFiPZD7e5j" alt=""><figcaption></figcaption></figure>

3. Shut down the vFitCon server to prevent vFitCon & EPC claim device manageability at the same time.
4. Login to **EPC** and go to **System > Backup & Restore > System Backup**\
   Click **Import** System config file and choose file downloaded from vFitCon then click **Restore**.

{% hint style="info" %}
**Note:** Refer to[ EPC quick start guide](https://docs.engenius.ai/epc-quick-start-guide/installation-and-onboarding) to install & start a new EPC.
{% endhint %}

5. Devices will automatically detect and switch to the EPC after few minutes.

<figure><img src="/files/HntDWoJmyy36upTBbSMY" alt=""><figcaption></figcaption></figure>


---

# Agent Instructions
This documentation is published with GitBook. GitBook is the documentation platform designed so that both humans and AI agents can read, navigate, and reason over technical content effectively. Learn more at gitbook.com.

## Querying This Documentation
If you need additional information that is not directly available in this page, you can query the documentation dynamically by asking a question.

Perform an HTTP GET request on the current page URL with the `ask` query parameter, and the optional `goal` query parameter:

```
GET https://doc.engenius.ai/home-epc-config-guide/migrate-vfitcon-to-epc/migration-scenarios/case-1-epc-deployed-in-same-subnet-with-devices.md?ask=<question>&goal=<endgoal>
```

`ask` is the immediate question: it should be specific, self-contained, and written in natural language.
`goal` is optional and describes the broader end goal you are ultimately trying to accomplish on behalf of the user. GitBook uses it to tailor the answer towards what is most useful for that goal.

The response will contain a direct answer to the question and relevant excerpts and sources from the documentation.

Use this mechanism when the answer is not explicitly present in the current page, you need clarification or additional context, or you want to retrieve related documentation sections.
