# Errors

We use a common JSON error format across all our service endpoints.

### *Error* object <a href="#error-response" id="error-response"></a>

<table><thead><tr><th width="171.33333333333331">Property</th><th width="160">Type</th><th>Description</th></tr></thead><tbody><tr><td><code>code</code></td><td><a href="#error-codes"><em>ErrorCode</em></a> string</td><td>A code to describe the error.</td></tr><tr><td><code>description</code></td><td>String</td><td>Technical description of the error (not intended for end-user display).</td></tr><tr><td><code>message</code></td><td>String or null</td><td>For relevant errors, an optional message from the institution website or API that can be presented to an end-user. These messages usually bring details or instructions that complement the error code, but they are not translated.</td></tr><tr><td><code>request_id</code></td><td>Integer or null</td><td>Unique ID of the request (which could be used for audit).</td></tr></tbody></table>

### ErrorCode values <a href="#error-codes" id="error-codes"></a>

#### Common error codes <a href="#common-error-codes" id="common-error-codes"></a>

<table><thead><tr><th width="230">Code</th><th>Description</th></tr></thead><tbody><tr><td><code>connectionLocked</code></td><td>For all services in relation with a sub-connection resource, this error indicates that the connection is in a readonly state.</td></tr><tr><td><code>missingParameter</code></td><td>A required parameter was omitted in the request.</td></tr><tr><td><code>invalidValue</code></td><td>The request is invalid, because of an unacceptable parameter or body property. Details are provided in the description.</td></tr><tr><td><code>methodNotAllowed</code></td><td>An API endpoint was called with an unsupported HTTP method.</td></tr><tr><td><code>bug</code><br>Other codes</td><td>An internal error occurred.</td></tr></tbody></table>

{% hint style="warning" %}
Additional codes may be used or added in the future. When implementing error handling, always fallback to a generic case for unknown codes.
{% endhint %}


---

# Agent Instructions: Querying This Documentation

If you need additional information that is not directly available in this page, you can query the documentation dynamically by asking a question.

Perform an HTTP GET request on the current page URL with the `ask` query parameter:

```
GET https://docs.powens.com/api-reference/overview/errors.md?ask=<question>
```

The question should be specific, self-contained, and written in natural language.
The response will contain a direct answer to the question and relevant excerpts and sources from the documentation.

Use this mechanism when the answer is not explicitly present in the current page, you need clarification or additional context, or you want to retrieve related documentation sections.
