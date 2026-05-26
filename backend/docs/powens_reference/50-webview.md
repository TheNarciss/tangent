# Webview

Our webview complements REST API endpoints with web-based services to handle sensitive or complex operations:

* add a connection (to a bank or a provider), or edit/repare access to a connection;
* manage connections (add/remove/edit);
* edit and validate bank transfers.

Usage of the webview is mandatory if you don't hold an Agent status, since you are not allowed to use API endpoints carrying user credentials, and optional otherwise.

{% hint style="info" %}
You can use our [integration demos](https://integrate.budget-insight.com/) to experiment with the different Webview flows described below.
{% endhint %}

## Webview protocol <a href="#implementation-guidelines" id="implementation-guidelines"></a>

Services available as part of the webview are designed as parameterized URLs intended to be opened in a web browser. A callback URI must be specified by callers to be notified at the end of the operation flow, similar to OAuth 2 specification.

### Base URL <a href="#base-url" id="base-url"></a>

The base URL of all services must be customized:\
\
`https://webview.powens.com/{lang}/{flow}?domain={domain}.biapi.pro&{parameters}`

* `{domain}`: substitute with your API domain in the `domain` query parameter
* `{lang}`: optionally specify the language of the webview (possible values: `en`, `fr`, `de`, `nl`, `pt`, `it`, `es`; if not specified, an automatic redirection will be performed following the language of the browser).
* `{flow}`: See [endpoints reference](#endpoints-reference) below for details about each flow
* `{parameters}`: See [endpoints reference](#endpoints-reference) below for details about query parameters

### Callback handling <a href="#callback-handling" id="callback-handling"></a>

Most flows redirect to a callback URI at the end of the process. Query parameters are added to the URI to identify successful or failed operations.

Successful parameters are specific to each flow. In case of an error, the following parameters are added:

<table><thead><tr><th width="228">Parameter</th><th>Description</th></tr></thead><tbody><tr><td><code>error</code></td><td>An lowercase string error code identifying the kind of error that occurred. When the parameter is not present, the response is successful.</td></tr><tr><td><code>error_description</code></td><td>A longer string description of the error (not intended for user display).</td></tr></tbody></table>

Common error codes include:

<table><thead><tr><th width="231">Code</th><th>Description</th></tr></thead><tbody><tr><td><code>access_denied</code></td><td>The user explicitly cancelled the flow.</td></tr><tr><td><code>server_error</code></td><td>Oops, a technical failure occurred during the process.</td></tr></tbody></table>

*Forward compatibility requirement: additional error codes may be added in the future to describe specific cases. When implementing error codes handling, always fallback to a generic case for unknown codes.*

#### Browser compatibility <a href="#browser-compatibility" id="browser-compatibility"></a>

The webview is designed and tested to work with browsers supported by the Angular framework:\
<https://angular.io/guide/browser-support>

#### Privacy / GDPR status <a href="#privacy--gdpr-status" id="privacy--gdpr-status"></a>

The webview itself does not use any kind of long-term data persistence mechanism such as cookies or local storage, but some authentication or authorization steps may delegate to third-party web services that may implement them. Analytics performed on the webview use anonymous data only.

## Integration guidelines <a href="#browser-integration" id="browser-integration"></a>

Presenting the webview URL in a browser requires special care about the technical components involved, in order to optimize UX and conversion rate by allowing app-to-app experiences.

The recommended components vary by platform:

### Web

In a web environment (i.e. when your own app is already running in a browser, as a standard HTML/JS app, PWA, etc.), you should present the webview either using a [full-page redirect](https://developer.mozilla.org/en-US/docs/Web/API/Location/replace) (recommended), or optionally using a [popup window](https://developer.mozilla.org/fr/docs/Web/API/Window/open).

The later requires special care on mobile as popups are usually presented as new tabs, and can be subject to blocking policies. Such integrations also require proper [cross-window communication](https://developer.mozilla.org/en-US/docs/Web/API/Window/postMessage) to [dismiss the extra window](https://developer.mozilla.org/fr/docs/Web/API/Window/close) after the flow has ended.

{% hint style="warning" %}
Integration of our webview in an `<iframe>` tag is discouraged as it can yield to a mixed user experience (our webiew provides its own UI context and navigation).
{% endhint %}

Iframe integration can also prevent app-to-app support for some connectors. When our webview is embedded in an iframe and it needs to present a third-party connection flow (connector webview with potential app-to-app support), it will itself open a popup (or new tab) to maximize the chance of app-to-app support.

When using the redirection technique, make use of the `state` parameter, optionally in conjunction with [session storage](https://developer.mozilla.org/fr/docs/Web/API/Window/sessionStorage), to restore context in your app at the end of the webview flow.

### Android

In a native Android environment (or when your app is compiled to an Android app using a multi-platform framework), you should present our webview using the **Chrome Custom Tabs** library, rather than using a *WebView* component.

{% embed url="<https://developer.chrome.com/docs/android/custom-tabs/>" %}

Chrome Custom Tabs allow good support for app-to-app experiences and let the end-user benefit from a navigation context shared with the browser app (cookies, saved credentials, etc.). Although they represent a slightly less integrated visual experience, the library does support customization and theming.

{% hint style="warning" %}
*WebView* component should be avoided as it can prevent app-to-app support for some connectors.
{% endhint %}

Callback handling with Chrome Custom Tabs usually rely on [declaring an intent filter](https://developer.android.com/training/app-links/deep-linking) (with custom scheme) handled by the calling Activity, which is [brought to foreground](https://developer.android.com/reference/android/content/Intent.html#FLAG_ACTIVITY_CLEAR_TOP) after the flow.<br>

### iOS

{% content-ref url="/spaces/IKL8k8xs9Sfm1SpZ2QE1/pages/RYm5NnOOgRfuB1b9s2bB" %}
[Powens Connect iOS](https://docs.powens.com/documentation/sdk/powens-connect-ios)
{% endcontent-ref %}

### Multi-platform frameworks

When using Flutter, use the [flutter\_custom\_tabs](https://pub.dev/packages/flutter_custom_tabs) package, that implement the above recommended components.

When using React Native, you can rely on some (non official) third-party packages to implement usage of Chrome Custom Tabs and *SFSafariViewController*, or provide your own [native module](https://reactnative.dev/docs/native-modules-intro).

## Endpoints reference <a href="#endpoints-reference" id="endpoints-reference"></a>

### Add connection flow <a href="#add-connection-flow" id="add-connection-flow"></a>

<pre><code><strong>https://webview.powens.com/{lang}/connect?domain={domain}.biapi.pro&#x26;{parameters}
</strong></code></pre>

This flow allows an end-user to add a new connection to the API. The flow handles the following steps:

* selecting a connector;
* authenticating & authorizing with the connector, by collecting credentials or delegating;
* managing consent to aggregate accounts/subscriptions;
* collecting required information for professional accounts.

You can try it out [here](https://integrate.budget-insight.com/demos/connect).

**Query parameters**

<table><thead><tr><th width="201">Parameter</th><th width="104.33333333333331">Required</th><th>Description</th></tr></thead><tbody><tr><td><code>domain</code></td><td>Yes</td><td>Your API domain. For instance: <code>example.biapi.pro</code></td></tr><tr><td><code>client_id</code></td><td>Yes</td><td>The ID of the requesting client application. You can manage client applications of your domain in the admin console.</td></tr><tr><td><code>redirect_uri</code></td><td>Yes</td><td>An absolute callback URI. The webview will redirect to it at the end of the flow.</td></tr><tr><td><code>code</code></td><td>No</td><td>A user-scoped <a href="/pages/QzWAc034jnBgPc1HxOA6#generate-a-temporary-code">temporary code</a> to use with our API.<br>If you don't provide a code, a new anonymous user will be created before the connection is added, and you will be returned an access token code scoped to it with the success callback.</td></tr><tr><td><code>state</code></td><td>No</td><td>An opaque string parameter that you can use to carry state across the flow. The parameter will be set "as is" on the callback URI. Make sure that the <code>state</code> you provide is properly URL-encoded.</td></tr><tr><td><code>connector_ids</code></td><td>No</td><td>A comma-separated list of connector IDs available to pick from.<br>If the parameter is omitted, all active connectors are available.<br>If you pass a single value, the user is not prompted to choose the connector. The parameter is combined with <code>connector_uuids</code>.</td></tr><tr><td><code>connector_uuids</code></td><td>No</td><td>A comma-separated list of connector UUIDs available to pick from.<br>If the parameter is omitted, all active connectors are available.<br>If you pass a single value, the user is not prompted to choose the connector. The parameter is combined with <code>connector_ids</code>.</td></tr><tr><td><code>connector_capabilities</code></td><td>No</td><td>A comma-separated list of capabilities to filter available connectors.<br>If the parameter is omitted, <code>bank</code> is inferred.<br>If multiple values are provided, only connectors that expose all the requested capabilities are available.<br>To request a bank connection, use <code>bank</code>.<br>To request a wealth connection, use <code>bankwealth</code>.<br>To request a provider connection, use <code>document</code>.</td></tr><tr><td><code>account_ibans</code></td><td>No</td><td>A comma-separated list of IBANs to filter accounts available for activation in a bank connection context. Other accounts will be disabled.</td></tr><tr><td><a href="https://docs.powens.com/api-reference/products/data-aggregation/bank-account-types#accounttypename-values"><code>account_types</code></a></td><td>No</td><td>A comma-separated list of account types to filter accounts available for activation in a bank connection context. Other accounts will be disabled. <br>To use the Webview in bank-only mode, specify <code>account_types=checking,card</code> as a URL parameter.</td></tr><tr><td><code>max_connections</code></td><td>No</td><td>A positive number indicating the maximum number of consecutive connections a user is allowed to add within the same connect flow. If this parameter is greater than one, a new screen will appear in the Webview, prompting the user to decide whether to add another institution or not.<br><br>By enabling this multiple addition, you must also handle  a new successful callback parameter <code>connection_ids</code> in your integration.</td></tr><tr><td><p></p><p><code>{connector_uuid}.{field.name}={value}</code></p></td><td>No</td><td>Combine a connector UUID with one of its fields' <code>name</code> to prefill or preselect the value of this field. <br><br>Example: you can use <code>f5c29767-1bc8-5337-9e4e-68a0fbd91c9a.website=pro</code> in order to preselect the <code>website</code> field with <code>pro</code> value for the connector with the specified UUID (Société Générale in this example). </td></tr></tbody></table>

**Successful callback parameters**

<table><thead><tr><th width="206">Parameter</th><th>Description</th></tr></thead><tbody><tr><td><code>connection_id</code></td><td>The ID of the newly created connection. Please note that when redirecting to the callback URI, the accounts and/or subscriptions are available in the API, but bank transactions or documents may still be syncing in background.</td></tr><tr><td><code>code</code></td><td>Optional. If a <code>code</code> was <em>not</em> initially specified, an API code that you must exchange to obtain a permanent access token associated with the newly-created anonymous user holding the connection. The parameter is URL-encoded, make sure to handle it accordingly.</td></tr><tr><td><code>state</code></td><td>Optional. Identical to the <code>state</code> parameter that was initially specified.</td></tr><tr><td><code>connection_ids</code></td><td>The IDs of the newly created connections. Please note that when redirecting to the callback URI, the accounts and/or subscriptions are available in the API, but bank transactions or documents may still be syncing in background.</td></tr></tbody></table>

**Additional error codes**

<table><thead><tr><th width="207">Code</th><th>Description</th></tr></thead><tbody><tr><td><code>tos_declined</code></td><td>The end-user refused to validate the terms of service.</td></tr></tbody></table>

### Re-auth / edit connection credentials flow <a href="#re-auth--edit-connection-credentials-flow" id="re-auth--edit-connection-credentials-flow"></a>

```
https://webview.powens.com/{lang}/reconnect?domain={domain}.biapi.pro&{parameters}
```

This flow allows an end-user to re-authenticate against a bank or a provider in order to recover an existing connection, or to completely reset credentials associated with a connection.

You can try it out [here](https://integrate.budget-insight.com/demos/reconnect).

**Query parameters**

<table><thead><tr><th width="199">Parameter</th><th width="101.33333333333331">Required</th><th>Description</th></tr></thead><tbody><tr><td><code>domain</code></td><td>Yes</td><td>Your API domain. For instance: <code>example.biapi.pro</code></td></tr><tr><td><code>client_id</code></td><td>Yes</td><td>The ID of the requesting client application. You can manage client applications of your domain in the admin console.</td></tr><tr><td><code>redirect_uri</code></td><td>Yes</td><td>An absolute callback URI. The webview will redirect to it at the end of the flow.</td></tr><tr><td><code>code</code></td><td>Yes</td><td>A user-scoped <a href="/pages/QzWAc034jnBgPc1HxOA6#generate-a-temporary-code">temporary code</a> to use with our API.</td></tr><tr><td><code>connection_id</code></td><td>Yes</td><td>The ID of the existing connection.</td></tr><tr><td><code>state</code></td><td>No</td><td>An opaque string parameter that you can use to carry state across the flow. The parameter will be set "as is" on the callback URI. Make sure that the <code>state</code> you provide is properly URL-encoded.</td></tr><tr><td><code>reset_credentials</code></td><td>No</td><td>In the default mode (<code>false</code>), the service will try to recover the connection and prompt the user only with outdated or transient information (new password, OTP...).<br>Set the parameter to <code>true</code> to force resetting all the credentials associated with the connection. This parameter may not apply to all connectors.</td></tr><tr><td><code>connection_sources</code></td><td>No</td><td>A comma-separated list of source names.<br>Coupled to <code>reset_credentials=true</code>, allows to target specific sources to reset.<br>For instance: <code>connection_sources=openapi</code></td></tr></tbody></table>

**Successful callback parameters**

This flow adds no parameter to the callback URI in case of success, except from `state`.

### Manage connections <a href="#manage-connections" id="manage-connections"></a>

```
https://webview.powens.com/{lang}/manage?domain={domain}.biapi.pro&{parameters}
```

This flow allows an end-user to manage the connections associated with his account in the API. The user can add new connections, remove existing ones, fix connection errors, reset credentials or activate/deactivate bank accounts.

Support of `redirect_uri` in this flow is optional, as it can be integrated or presented as a terminal step, without relying on a final redirection.

You can try it out [here](https://integrate.budget-insight.com/demos/manage).

**Query parameters**

<table><thead><tr><th width="234.01953125">Parameter</th><th width="79.20052083333331">Required</th><th>Description</th></tr></thead><tbody><tr><td><code>domain</code></td><td>Yes</td><td>Your API domain. For instance: <code>example.biapi.pro</code></td></tr><tr><td><code>client_id</code></td><td>Yes</td><td>The ID of the requesting client application. You can manage client applications of your domain in the admin console.</td></tr><tr><td><code>code</code></td><td>Yes</td><td>A user-scoped <a href="/pages/QzWAc034jnBgPc1HxOA6#generate-a-temporary-code">temporary code</a> to use with our API.</td></tr><tr><td><code>connection_id</code></td><td>No</td><td>The ID of an existing connection. When provided, the webview will directly navigate to that connection if it is found among the retrieved connections.</td></tr><tr><td><code>redirect_uri</code></td><td>No</td><td>An absolute callback URI. When provided, the webview will display a close button that redirects to it.</td></tr><tr><td><code>state</code></td><td>No</td><td>An opaque string parameter that you can use to carry state across the flow when providing a <code>redirect_uri</code>. The parameter will be set "as is" on the callback URI. Make sure that the <code>state</code> you provide is properly URL-encoded.</td></tr><tr><td><code>connector_capabilities</code></td><td>No</td><td>A comma-separated list of capabilities to filter available connectors when adding a new connection.<br>If the parameter is omitted, <code>bank</code> is inferred.<br>If multiple values are provided, only connectors that expose all the requested capabilities are available.<br>To request a bank connection, use <code>bank</code>.<br>To request a wealth connection, use <code>bankwealth</code>.<br>To request a provider connection, use <code>document</code>.</td></tr><tr><td><code>account_types</code></td><td>No</td><td>A comma-separated list of account types to filter accounts available for activation on adding a new bank connection or updating existing connections. Other accounts will be disabled.</td></tr></tbody></table>

**Callback parameters**

This flow adds no parameter to the callback URI, except from `state`.

### Validate a payment <a href="#validate-a-payment" id="validate-a-payment"></a>

```
https://webview.powens.com/{lang}/payment?domain={domain}.biapi.pro&{parameters}
```

This flow allows an end-user to validate a payment request. The flow handles the following steps:

* present a list of supported emitter banks;
* validate the payment request and redirect the user to the validation webview of the bank.

**Query parameters**

<table><thead><tr><th width="175.33333333333331">Parameter</th><th width="103">Required</th><th>Description</th></tr></thead><tbody><tr><td><code>domain</code></td><td>Yes</td><td>Your API domain. For instance: <code>example.biapi.pro</code></td></tr><tr><td><code>client_id</code></td><td>Yes</td><td>The ID of the requesting client application. You can manage client applications of your domain in the admin console.</td></tr><tr><td><code>redirect_uri</code></td><td>Yes</td><td>An absolute callback URI. The webview will redirect to it <em>only in case of an error or cancellation</em>.</td></tr><tr><td><code>code</code></td><td>Yes</td><td>A payment-scoped <a href="/pages/QzWAc034jnBgPc1HxOA6#generate-a-temporary-code">service token</a> to use with our API. The provided token must have the <code>payments</code> scope.</td></tr><tr><td><code>state</code></td><td>No</td><td>An opaque string parameter that you can use to carry state across the flow. The parameter will be set "as is" on the callback URI. Make sure that the state you provide is properly URL-encoded.</td></tr><tr><td><code>payment_id</code></td><td>Yes</td><td>The ID of the payment request that was prepared with the API.</td></tr></tbody></table>

**Successful behavior**

Unlike other webview endpoints, the user will be redirected to the callback URL provided **at the creation of the payment request** (using `client_redirect_uri`) after the bank webview. The `redirect_uri` provided as a webview parameter is only used for the error or cancellation cases.

### Execute a bank transfer (Deprecated) <a href="#deprecated-execute-a-bank-transfer" id="deprecated-execute-a-bank-transfer"></a>

{% hint style="danger" %}
Since the release of our [Pay product](broken://spaces/IKL8k8xs9Sfm1SpZ2QE1/pages/Xc77IG4DjS9kUvaAdxOW) (handling PSD2-compliant use-cases), the former Transfer product (based on directaccess) has been deprecated. The Transfer product is neither maintained nor offered anymore.
{% endhint %}

```
https://{domain}.biapi.pro/2.0/auth/webview/{lang}/transfer
```

This flow allows an end-user to execute a bank transfer. The flow handles the following steps:

* if the transfer is not already created, all steps to authenticate with a bank, select the recipient, the emitter account, the amount and label;
* executing the transfer, including managing SCAs for recipient registration and/or transfer validation.

**Query parameters**

<table><thead><tr><th width="175">Parameter</th><th width="68.33333333333331">Required</th><th>Description</th></tr></thead><tbody><tr><td><code>client_id</code></td><td>Yes</td><td>The ID of the requesting client application. You can manage client applications of your domain in the admin console.</td></tr><tr><td><code>redirect_uri</code></td><td>Yes</td><td>An absolute callback URI. The webview will redirect to it at the end of the flow.</td></tr><tr><td><code>code</code></td><td>Yes</td><td>A user-scoped <a href="/pages/QzWAc034jnBgPc1HxOA6#generate-a-temporary-code">temporary code</a> to use with our API. If you don't provide a code, a new anonymous user will be created before a connection is added and the transfer is executed, and you will be returned an access token code scoped to it with the success callback.</td></tr><tr><td><code>state</code></td><td>No</td><td>An opaque string parameter that you can use to carry state across the flow. The parameter will be set "as is" on the callback URI. Make sure that the state you provide is properly URL-encoded.</td></tr><tr><td><code>transfer_id</code></td><td>No</td><td>The ID of an prepared transfer to be validated in the webview. The user cannot edit anything on the transfer before validation.</td></tr></tbody></table>

**Successful callback parameters**

<table><thead><tr><th width="174">Parameter</th><th>Description</th></tr></thead><tbody><tr><td><code>transfer_id</code></td><td>The ID of the transfer that was created and executed.</td></tr><tr><td><code>code</code></td><td>If a code was not initially specified, an API code that you can exchange to obtain a permanent access token associated with the newly-created anonymous user holding the transfer. The parameter is URL-encoded, make sure to handle it accordingly.</td></tr><tr><td><code>state</code></td><td>Identical to the state parameter that was initially specified (if any).</td></tr></tbody></table>

If you need to perform actions when a connection is added or removed, you should rely on [webhooks](https://docs.powens.com/documentation/integration-guides/webhooks).


---

# Agent Instructions: Querying This Documentation

If you need additional information that is not directly available in this page, you can query the documentation dynamically by asking a question.

Perform an HTTP GET request on the current page URL with the `ask` query parameter:

```
GET https://docs.powens.com/api-reference/overview/webview.md?ask=<question>
```

The question should be specific, self-contained, and written in natural language.
The response will contain a direct answer to the question and relevant excerpts and sources from the documentation.

Use this mechanism when the answer is not explicitly present in the current page, you need clarification or additional context, or you want to retrieve related documentation sections.
