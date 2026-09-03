> For the complete documentation index, see [llms.txt](https://doc.engenius.ai/llms.txt). Markdown versions of documentation pages are available by appending `.md` to page URLs; this page is available as [Markdown](https://doc.engenius.ai/home-epc-quick-start-guide/license-assignment-devices-registration.md).

# License Assignment / Devices Registration

EPC is leveraging EnGenius Cloud license management system to manage its licenses. EPC must be registered on EnGenius Cloud to get those advanced license. To register EPC, EPC Connect License is required.

## &#x20;<mark style="color:blue;">1. Add Connect License to EPC</mark>

**1.1 -** Go to **EPC > System > Inventory & License > License > Connect** page to add an EPC connect license.

<figure><img src="https://lh7-rt.googleusercontent.com/docsz/AD_4nXcA3Ku6czmnthbbZSPxmVLspHa2mNiMh8IWHkjZQTMfNK8NEWp93HzPbQkdmwxmaYPqzKyDMjdQP_x6X0JW3pxSDaT-IM_pd6GwdOqjTzYcVxBkchZLfOXKn9-a2f5bww32nkTYQMMJyDGNTIILtq7vvfN3LhQ2bkWMgd99vOaZgv58upCuOsc" alt=""><figcaption></figcaption></figure>

**1.2 -** After successfully adding an EPC Connect License, a serial number appears in the following pages:

* **Manage > Dashboard**&#x20;

<div align="left"><figure><img src="https://lh7-rt.googleusercontent.com/docsz/AD_4nXeC7kBBhg2ldwTisBNo1YV-CzAC5HamsPMKzJAqE5DnGtMoe7MGrK0cuu7GiNV9t4s6QDVkLqHn2y-v12qAAf-apLCOHzEai9x1gp3AFFa8gA3M0G_zlxqE1Er7Za3uOUQIs3jy_Z0audC0JZjIEvHXVe7_5jfWkZbNFXJTa4121ou4zQcnlQ0" alt=""><figcaption></figcaption></figure></div>

* **System > System Information**<br>

<figure><img src="https://lh7-rt.googleusercontent.com/docsz/AD_4nXedPLBjgZn6QPAMss-akMXAaRQ-CbwBzlgy_BUKLgge5jph0ZzBEkcblTdNcByCVVplpkJnjFcvS6CBiVOnKDTF-GXyVUFmps4mGV_YCYOygISAYEKgqjPXJ24T2ue_koUfj4YyNreAZtiXQMW1fGGD57-gBFduiKEUmHM8L68PH1-8SQajRlg" alt=""><figcaption></figcaption></figure>

## <mark style="color:blue;">2. Managing EnGenius devices</mark>

To manage EnGenius devices, they must be registered to an Org and assign to the network that you’d like to manage.

To register device, please check the S/N number in device label on bottom of the device first.

<figure><img src="/files/RIggXUvKh9G9kAkqi0tC" alt=""><figcaption></figcaption></figure>

**2.1 -** Go to **EPC > System > Inventory & License > Device**, click **+ Register Device** for device registration.

All EnGenius devices support cloud management feature will automatically search for Cloud/controller. If there are unregistered devices in the same subnet with EPC, they will appear in pending approval list. Select the device that you would like manage and click **√ Register** for registration. If device is not in pending approval list, you can also register device by manually input S/N.

<figure><img src="/files/33GKcgL4nEAOPcKujpB6" alt=""><figcaption></figcaption></figure>

**2.2 -** After successfully registering device, select the devices and assign them to the network to start management.

<figure><img src="/files/GHs2qkl5NzIIXoBNE8Lk" alt=""><figcaption></figcaption></figure>

Since multiple EPCs can coexist in a network simultaneously, it is necessary for EPC and device pairing each other to determine which EPC is responsible for managing the device. When device is assigned to a network, EPC will trigger paring process automatically. If the device is unreachable during pairing process, you may need to trigger paring process manually after device get back.

**2.3 -** Go to device list of that network (Manage > Access Point or Switch), select the device you’d like to pair. It may take few minutes for the manual pairing process.

## <mark style="color:blue;">3. Assign other licenses to EPC</mark>

**3.1-** To assign other license to EPC, go to **EnGenius Cloud > Organization > Inventory & License > License** page to add the license and associate it with your EPC.

<figure><img src="/files/KUfDFS3BaCCcrXQII8zn" alt=""><figcaption></figcaption></figure>

EPC must get online to synchronize the license assignments to local. If license is not synchronized, users may be unable to perform further operations on those licenses within the EPC.

<figure><img src="/files/CJy7UOZuR7f3kvzmMYWd" alt=""><figcaption></figcaption></figure>

Refer to [Managing Device Inventory and License](https://docs.engenius.ai/engenius-cloud/managing-organizations/managing-device-inventory) for detailed device & license management instructions.


---

# Agent Instructions
This documentation is published with GitBook. GitBook is the documentation platform designed so that both humans and AI agents can read, navigate, and reason over technical content effectively. Learn more at gitbook.com.

## Querying This Documentation
If you need additional information that is not directly available in this page, you can query the documentation dynamically by asking a question.

Perform an HTTP GET request on the current page URL with the `ask` query parameter, and the optional `goal` query parameter:

```
GET https://doc.engenius.ai/home-epc-quick-start-guide/license-assignment-devices-registration.md?ask=<question>&goal=<endgoal>
```

`ask` is the immediate question: it should be specific, self-contained, and written in natural language.
`goal` is optional and describes the broader end goal you are ultimately trying to accomplish on behalf of the user. GitBook uses it to tailor the answer towards what is most useful for that goal.

The response will contain a direct answer to the question and relevant excerpts and sources from the documentation.

Use this mechanism when the answer is not explicitly present in the current page, you need clarification or additional context, or you want to retrieve related documentation sections.
