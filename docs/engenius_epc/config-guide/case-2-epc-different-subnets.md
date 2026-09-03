> For the complete documentation index, see [llms.txt](https://doc.engenius.ai/llms.txt). Markdown versions of documentation pages are available by appending `.md` to page URLs; this page is available as [Markdown](https://doc.engenius.ai/home-epc-config-guide/migrate-vfitcon-to-epc/migration-scenarios/case-2-epc-deployed-in-different-subnets-with-devices.md).

# Case 2: EPC deployed in DIFFERENT subnets with devices

1. Log in **vFitCon** and go to **System > System Information > Usage**. Ensure vFitCon version has been upgraded to 1.3.18.

{% hint style="info" %}
**Note:** If vFitCon has not been updated, refer guide to [update guide](https://docs.engenius.ai/fitcontroller-user-manual/fitcontroller-vm/update-fitcontroller-vm) to update.&#x20;
{% endhint %}

<figure><img src="/files/TZZxZXIAKMFEzYPhr1IU" alt=""><figcaption></figcaption></figure>

2. Login to EPC and go to **System > System Information > Summary**.\
   Copy EPC Serial Number.

{% hint style="info" %}
**Note:** Refer to[ EPC quick start guide](https://docs.engenius.ai/epc-quick-start-guide/installation-and-onboarding) to install & start a new EPC.
{% endhint %}

<figure><img src="/files/fseUDuKs0dtrz7nX7n4M" alt=""><figcaption></figcaption></figure>

3. Login to vFitCon and go to **System > Inventory > FitRegister > Global Settings** to ensure **FitRegister** is enabled.

<figure><img src="/files/GZn8DQPR0jbsvKeSDxyu" alt=""><figcaption></figcaption></figure>

4. Go to **System > Backup & Restore > System Backup**. Click **Backup** button to backup vFitCon system configurations.
5. Input the **EPC serial number** copied from the EPC, then click **Apply** to upload it to FitRegister and ensure the corresponding EPC correctly hands over devices.

<figure><img src="/files/tkClM8Q0mYFrAiFDSXIX" alt=""><figcaption></figcaption></figure>

6. Shut down the vFitCon server to prevent vFitCon & EPC cliam device manageability at the same time.
7. Login to EPC and go to **System > Backup & Restore > System Backup**\
   Click **Import System config file** and choose file downloaded from vFitCon, then click **Restore**.
8. Devices will automatically detect and switch to the EPC after few minutes.

<figure><img src="/files/t6Z4vW7Vz0DgB5eWPVsS" alt=""><figcaption></figcaption></figure>


---

# Agent Instructions
This documentation is published with GitBook. GitBook is the documentation platform designed so that both humans and AI agents can read, navigate, and reason over technical content effectively. Learn more at gitbook.com.

## Querying This Documentation
If you need additional information that is not directly available in this page, you can query the documentation dynamically by asking a question.

Perform an HTTP GET request on the current page URL with the `ask` query parameter, and the optional `goal` query parameter:

```
GET https://doc.engenius.ai/home-epc-config-guide/migrate-vfitcon-to-epc/migration-scenarios/case-2-epc-deployed-in-different-subnets-with-devices.md?ask=<question>&goal=<endgoal>
```

`ask` is the immediate question: it should be specific, self-contained, and written in natural language.
`goal` is optional and describes the broader end goal you are ultimately trying to accomplish on behalf of the user. GitBook uses it to tailor the answer towards what is most useful for that goal.

The response will contain a direct answer to the question and relevant excerpts and sources from the documentation.

Use this mechanism when the answer is not explicitly present in the current page, you need clarification or additional context, or you want to retrieve related documentation sections.
