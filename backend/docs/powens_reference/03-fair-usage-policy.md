# Fair usage policy

### **What is the fair usage policy?**

The Fair Usage Policy (FUP) is designed to ensure a smooth, reliable, and efficient experience for all users of the Powens API. By setting reasonable usage limits, we help maintain optimal performance, security, and stability, while preventing unintentional system overload.

Rather than being a restriction, this policy guarantees fair access for all users and ensures that our API remains high-performing and scalable as open finance evolves.

### **Why have we implemented a Fair usage policy?**

As open finance expands and new use cases emerge, API traffic has naturally increased due to larger data volumes and more frequent updates. Anticipating this, we designed **robust solutions such as** [**Webhooks**](https://docs.powens.com/documentation/integration-guides/webhooks) **and Background Refresh** to handle data synchronization efficiently.

To keep our API **fast and available for everyone**, we strongly recommend using [**Webhooks**](https://docs.powens.com/documentation/integration-guides/webhooks) **first** rather than repeatedly polling the API. Webhooks allow us to push real-time updates directly to you, ensuring a **smoother and more efficient integration**.

When Webhooks are not an option, excessive requests in a short timeframe can put unnecessary strain on the system, potentially affecting performance for all users. To prevent this, we have introduced rate limiting, ensuring fair resource allocation and protecting both sandbox and production environments.

### **What are the valid cases for forced synchronization?**

There are legitimate scenarios where a **manual refresh** is required, for example:

* When an end user actively requests a data update (e.g., opening the app or starting a credit application).
* When the refresh is for a single user, not a bulk operation on multiple users.

{% hint style="info" %}
We understand that **some specific needs may require adjustments**, and we remain open to discussing tailored solutions. Feel free to reach out to your **KAM (Key Account Manager)** if you believe your plan needs fine-tuning.
{% endhint %}

### **What does this mean for your integration?**

#### [**Webhooks First**](https://docs.powens.com/documentation/integration-guides/webhooks)

To maintain **high performance and reliability**, we strongly encourage you to adopt [**Webhooks**](https://docs.powens.com/documentation/integration-guides/webhooks) whenever possible. They eliminate unnecessary API polling, improve efficiency, and ensure seamless real-time updates.

Our Webhooks system is **robust, reliable, and designed for scalability**—helping you optimize your integration while keeping the Powens API **stable for all users**.

#### **Rate Limiting in the Sandbox Environment**

Before diving into rate limits, let’s clarify the role of our **Sandbox environment**:

<table><thead><tr><th>✅ Designed for</th><th>❌ Not intended for</th><th data-hidden></th></tr></thead><tbody><tr><td>Developing and testing your integration.</td><td>Load testing or simulating high API traffic.</td><td></td></tr><tr><td>Validating new features before going live.</td><td>Production-like scenarios (it does not contain real user data).</td><td></td></tr></tbody></table>

Since the Sandbox is meant for **functional testing**, rate limits ensure that it remains available and efficient for all developers.

| Client type | Rate limiting | Allowed call per day |
| ----------- | ------------- | -------------------- |
| Default     | 30 call/min   | 86400                |

\ <br>


---

# Agent Instructions: Querying This Documentation

If you need additional information that is not directly available in this page, you can query the documentation dynamically by asking a question.

Perform an HTTP GET request on the current page URL with the `ask` query parameter:

```
GET https://docs.powens.com/api-reference/overview/fair-usage-policy.md?ask=<question>
```

The question should be specific, self-contained, and written in natural language.
The response will contain a direct answer to the question and relevant excerpts and sources from the documentation.

Use this mechanism when the answer is not explicitly present in the current page, you need clarification or additional context, or you want to retrieve related documentation sections.
