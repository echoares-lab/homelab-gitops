> For the complete documentation index, see [llms.txt](https://doc.engenius.ai/llms.txt). Markdown versions of documentation pages are available by appending `.md` to page URLs; this page is available as [Markdown](https://doc.engenius.ai/home-epc-quick-start-guide/installation-and-onboarding/installation-guide-linux.md).

# Installation Guide - Linux

## <mark style="color:blue;">1. Installation</mark>

1.1 - Use the following command to download installation scripts in the Linux command shell:

<table data-header-hidden><thead><tr><th width="116"></th><th></th></tr></thead><tbody><tr><td>EPC version </td><td>Command </td></tr><tr><td>V1.7.2 <br>(beta) </td><td>wget https://engenius-epc.s3.us-west-2.amazonaws.com/dev/1.7.2/epc.sh; chmod +x epc.sh </td></tr><tr><td>V1.8.7</td><td>wget https://engenius-epc.s3.us-west-2.amazonaws.com/release/1.8.7/epc.sh; chmod +x epc.sh </td></tr><tr><td>V1.8.8</td><td>wget https://engenius-epc.s3.us-west-2.amazonaws.com/release/1.8.8/epc.sh; chmod +x epc.sh </td></tr><tr><td>V1.9.0</td><td>wget https://engenius-epc.s3.us-west-2.amazonaws.com/release/1.9.0/epc.sh; chmod +x epc.sh</td></tr></tbody></table>

1.2 - Run the script with the following command:

```
sudo ./epc.sh install
```

{% hint style="info" %}
The script will help install EPC port mapping and database into your local system. The location of the database will be in `/srv/docker/mongodb/data/db`
{% endhint %}

{% hint style="info" %}
If your Linux has pre-installed Docker that does not have enough system permissions. Please remove the Docker by command:&#x20;

```
sudo snap remove docker 
```

and run below command again.

```
sudo ./epc.sh install
```

![Docker permissions insufficient ](/files/ulAFljxEp7Zc5mpeEeOn)
{% endhint %}

## <mark style="color:blue;">2. Open EPC</mark>

Open the following URL in your browser:

```
http://{ip_address_of_EPC}:8080 
```

or

```
https://{ip_address_of_EPC} 
```


---

# Agent Instructions
This documentation is published with GitBook. GitBook is the documentation platform designed so that both humans and AI agents can read, navigate, and reason over technical content effectively. Learn more at gitbook.com.

## Querying This Documentation
If you need additional information that is not directly available in this page, you can query the documentation dynamically by asking a question.

Perform an HTTP GET request on the current page URL with the `ask` query parameter, and the optional `goal` query parameter:

```
GET https://doc.engenius.ai/home-epc-quick-start-guide/installation-and-onboarding/installation-guide-linux.md?ask=<question>&goal=<endgoal>
```

`ask` is the immediate question: it should be specific, self-contained, and written in natural language.
`goal` is optional and describes the broader end goal you are ultimately trying to accomplish on behalf of the user. GitBook uses it to tailor the answer towards what is most useful for that goal.

The response will contain a direct answer to the question and relevant excerpts and sources from the documentation.

Use this mechanism when the answer is not explicitly present in the current page, you need clarification or additional context, or you want to retrieve related documentation sections.
