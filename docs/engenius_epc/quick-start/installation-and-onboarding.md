> For the complete documentation index, see [llms.txt](https://doc.engenius.ai/llms.txt). Markdown versions of documentation pages are available by appending `.md` to page URLs; this page is available as [Markdown](https://doc.engenius.ai/home-epc-quick-start-guide/installation-and-onboarding.md).

# Installation & Onboarding

This section will help you set up and start using EPC.

If you are installing EPC on a **Windows system**, follow the following link:

{% embed url="<https://doc.engenius.ai/home-epc-quick-start-guide/installation-and-onboarding/installation-guide-windows>" %}

If you prefer to install EPC on a **Linux environment**,  follow the following link:&#x20;

{% embed url="<https://doc.engenius.ai/home-epc-quick-start-guide/installation-and-onboarding/installation-guide-linux>" %}

Once installation is complete, continue with **onboarding guide** to learn how to access and configure your EPC for the first time.

{% embed url="<https://doc.engenius.ai/home-epc-quick-start-guide/installation-and-onboarding/onboarding>" %}


---

# Agent Instructions
This documentation is published with GitBook. GitBook is the documentation platform designed so that both humans and AI agents can read, navigate, and reason over technical content effectively. Learn more at gitbook.com.

## Querying This Documentation
If you need additional information that is not directly available in this page, you can query the documentation dynamically by asking a question.

Perform an HTTP GET request on the current page URL with the `ask` query parameter, and the optional `goal` query parameter:

```
GET https://doc.engenius.ai/home-epc-quick-start-guide/installation-and-onboarding.md?ask=<question>&goal=<endgoal>
```

`ask` is the immediate question: it should be specific, self-contained, and written in natural language.
`goal` is optional and describes the broader end goal you are ultimately trying to accomplish on behalf of the user. GitBook uses it to tailor the answer towards what is most useful for that goal.

The response will contain a direct answer to the question and relevant excerpts and sources from the documentation.

Use this mechanism when the answer is not explicitly present in the current page, you need clarification or additional context, or you want to retrieve related documentation sections.
