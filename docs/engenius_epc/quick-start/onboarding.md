> For the complete documentation index, see [llms.txt](https://doc.engenius.ai/llms.txt). Markdown versions of documentation pages are available by appending `.md` to page URLs; this page is available as [Markdown](https://doc.engenius.ai/home-epc-quick-start-guide/installation-and-onboarding/onboarding.md).

# Onboarding

## <mark style="color:blue;">1. Create User Accounts / SMTP Setting</mark>

1.1 - During the first login, the EPC will prompt you to create the initial user account for EPC management.

<figure><img src="https://lh7-rt.googleusercontent.com/docsz/AD_4nXfcGlsdMmRVvqm2rWFQKgBeOMlhDUByy-2TVJwS7buF8nwKxOjaU8p0gw_wHZ4jw5bkiSQLPJqjo7F96w4E88VZXyRD97RZKPtY-Tb2TX1wGOMV-U21XYMIWF_pJrPJ7vlQKVZ1xTUrtIL9hi1Vai1hivDozYYZhGVWS6b1_uyzWyfn08J19w" alt=""><figcaption></figcaption></figure>

\
1.2 - You may invite other users to share the load of EPC management. Go to **Team Member** page to invite new users with proper authority settings.

<figure><img src="https://lh7-rt.googleusercontent.com/docsz/AD_4nXfnVPSVSLOZ6JmIYFhy1IHla7Gaanu0jq46f_SXUaKkpsoBtE8bnheTHrFzwPwGKvOn4lt7L7joDcILhZ1AN0K7imcL1HYmU68I04McvCoLgAmXRshHGffXx_oLW8xp1d8d0LxBc-ruVnCPXW3R_HFPAM7-gZDA-NcDyp2ok66mb--GYwrYvA" alt=""><figcaption></figcaption></figure>

1.3 - If you want new users to receive mail invitations, go to the **System > Email Alerts** page to identify a mail server for email delivery.

<figure><img src="https://lh7-rt.googleusercontent.com/docsz/AD_4nXdGePvTbu3EfNGvbYU3OwgPs38NMPOrWvOjNp4vnig_nqx_XZ8KA0U3VsDFOOQjsU8ol4SZ6dKTX24mV0VjIhabPcxJJ1tc4tiGdFhtBXVJfHq8kiR90_0wIxVnGKuoc4aLxtfA02e3zJiNiedV7Z_I8PRNhn4iP9qyTAh14j19b63ZHfyFP4Y" alt=""><figcaption></figcaption></figure>

## <mark style="color:blue;">2. Firewall Setting</mark>

Following firewall rules are required for EPC services.

| **Service**                            | **Port**             | **Protocol** | **Direction**    |
| -------------------------------------- | -------------------- | ------------ | ---------------- |
| FitRegister / Device remote management | 443                  | TCP          | Inbound/Outbound |
| Cloud Registration                     | 443                  | TCP          | Outbound         |
| Auto firmware upgrade                  | 443                  | TCP          | Outbound         |
| RADIUS                                 | 1812, 1813 (default) | TCP          | Inbound          |
| Log server                             | 514 (default)        | TCP          | Outbound         |

{% hint style="info" %}
Note: If you have multiple EPCs in your environment, please assign a different public port to each one to ensure services are delivered correctly..
{% endhint %}


---

# Agent Instructions
This documentation is published with GitBook. GitBook is the documentation platform designed so that both humans and AI agents can read, navigate, and reason over technical content effectively. Learn more at gitbook.com.

## Querying This Documentation
If you need additional information that is not directly available in this page, you can query the documentation dynamically by asking a question.

Perform an HTTP GET request on the current page URL with the `ask` query parameter, and the optional `goal` query parameter:

```
GET https://doc.engenius.ai/home-epc-quick-start-guide/installation-and-onboarding/onboarding.md?ask=<question>&goal=<endgoal>
```

`ask` is the immediate question: it should be specific, self-contained, and written in natural language.
`goal` is optional and describes the broader end goal you are ultimately trying to accomplish on behalf of the user. GitBook uses it to tailor the answer towards what is most useful for that goal.

The response will contain a direct answer to the question and relevant excerpts and sources from the documentation.

Use this mechanism when the answer is not explicitly present in the current page, you need clarification or additional context, or you want to retrieve related documentation sections.
