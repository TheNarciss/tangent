# Authentication

## User tokens API endpoints

### Create a new user and generate an associated access token

<mark style="color:green;">`POST`</mark> `https://{domain}.biapi.pro/2.0/auth/init`

This endpoint generates a new access token related to a new user.

Request body: [#authtokeninitrequest-object](#authtokeninitrequest-object "mention")

{% tabs %}
{% tab title="200: OK Token issued" %}
Response body: [#authtoken-object](#authtoken-object "mention")
{% endtab %}
{% endtabs %}

### Generate a temporary code

<mark style="color:blue;">`GET`</mark> `https://{domain}.biapi.pro/2.0/auth/token/code`

This endpoint generates a new temporary code for the current user.

This endpoint *requires* header authentication with a valid user access token.

In case the access token is already used by a trusted device, and you want to temporarily let another one (for example a web browser) access user resources, use this endpoint to generate a code that will expire in 30 minutes. If the generated code is intended to be used with our [webview](/api-reference/overview/webview.md), you can use the `singleAccess` token type.

#### Query Parameters

| Name | Type   | Description                 |
| ---- | ------ | --------------------------- |
| type | String | Type of the temporary code. |

{% tabs %}
{% tab title="200: OK Code issued" %}
Response body: [#authcode-object](#authcode-object "mention")
{% endtab %}
{% endtabs %}

### Exchange a temporary code for a permanent user access token

<mark style="color:green;">`POST`</mark> `https://{domain}.biapi.pro/2.0/auth/token/access`

This endpoint uses a temporary code to generate a permanent user access token.

Request body: [#authtokenexchangerequest-object](#authtokenexchangerequest-object "mention")

{% tabs %}
{% tab title="200: OK Token issued" %}
Response body: [#authtokenexchange-object](#authtokenexchange-object "mention")
{% endtab %}
{% endtabs %}

### Revoke an access token

<mark style="color:red;">`DELETE`</mark> `https://{domain}.biapi.pro/2.0/auth/token`

This endpoint invalidates *permanent* access tokens. Subsequent calls using the provided *permanent* access token will fail.

The invalidated token is the one that is provided in the header for authentication.

{% tabs %}
{% tab title="204: No Content Token revoked" %}

{% endtab %}
{% endtabs %}

### Generate a new token for an existing user

<mark style="color:green;">`POST`</mark> `https://{domain}.biapi.pro/2.0/auth/renew`

This endpoint generates a new permanent access token for an existing user, and revokes former tokens if explicitly requested.

Request body: [#authrenewrequest-object](#authrenewrequest-object "mention")

{% tabs %}
{% tab title="200: OK Token issued" %}
Response body: [#authtokenexchange-object](#authtokenexchange-object "mention")
{% endtab %}
{% endtabs %}

## Service tokens API endpoints

### Generate a service token

<mark style="color:green;">`POST`</mark> `https://{domain}.biapi.pro/2.0/auth/token`

This endpoint generates a special access token with a dedicated service `scope`. The generated token will expire after 30 minutes.

A service token is a token that is not associated with a user but rather used to access a specific feature or service. For example, the Pay product requires the use of a `payment` token.

Request body: [#authservicetokenrequest-object](#authservicetokenrequest-object "mention")

{% tabs %}
{% tab title="200: OK Token issued" %}
Response body: [#authservicetoken-object](#authservicetoken-object "mention")
{% endtab %}
{% endtabs %}

## Data model

### *AuthTokenInitRequest* object

<table><thead><tr><th width="185">Property</th><th width="82">Type</th><th width="109">Required</th><th>Description</th></tr></thead><tbody><tr><td><code>client_id</code></td><td>String</td><td>No</td><td>The ID of the calling client application.</td></tr><tr><td><code>client_secret</code></td><td>String</td><td>No</td><td>The client secret associated with the client ID.</td></tr></tbody></table>

If your client application credentials (`client_id` and `client_secret`) are both supplied, the generated token will be *permanent*. Otherwise, the token will expire in 30 minutes.

By default, the created user is temporary and will be deleted after 30 minutes if no *permanent* token is generated during this timeframe.

### ***AuthToken*****&#x20;object**

<table><thead><tr><th width="162.33333333333331">Property</th><th width="142">Type</th><th>Description</th></tr></thead><tbody><tr><td><code>auth_token</code></td><td>String</td><td>An access token to use for subsequent API calls.</td></tr><tr><td><code>type</code></td><td>String</td><td>The type of the token, <code>temporary</code> or <code>permanent</code> .</td></tr><tr><td><code>id_user</code></td><td>Integer</td><td>ID of the created user.</td></tr><tr><td><code>expires_in</code></td><td>Integer or null</td><td>The optional expiration delay of the token, in seconds.</td></tr></tbody></table>

### *AuthTokenType* value

<table><thead><tr><th width="246">Value</th><th>Description</th></tr></thead><tbody><tr><td><code>singleAccess</code></td><td>The code can only be used once.</td></tr><tr><td><code>requestAccess</code></td><td>The code expires after 30 min.</td></tr></tbody></table>

### *AuthCode* object

<table><thead><tr><th width="162.33333333333331">Property</th><th width="153">Type</th><th>Description</th></tr></thead><tbody><tr><td><code>code</code></td><td>String</td><td>The generated temporary code.</td></tr><tr><td><code>type</code></td><td>String</td><td>The type of the generated code. The only value is <code>temporary</code>.</td></tr><tr><td><code>access</code></td><td>String</td><td>The type of access granted, <code>single</code> or <code>standard</code>.</td></tr><tr><td><code>expires_in</code></td><td>Integer or null</td><td>The expiration delay of the code, in seconds.</td></tr></tbody></table>

### *AuthTokenExchangeRequest* object

<table><thead><tr><th width="195">Name</th><th width="92">Type</th><th width="102">Required</th><th>Description</th></tr></thead><tbody><tr><td><code>grant_type</code></td><td>String</td><td>No</td><td>The only accepted (and default) value is <code>authorization_code</code>.</td></tr><tr><td><code>client_id</code></td><td>String</td><td>Yes</td><td>The ID of the calling client application.</td></tr><tr><td><code>client_secret</code></td><td>String</td><td>Yes</td><td>The client secret associated with the client ID.</td></tr><tr><td><code>code</code></td><td>String</td><td>Yes</td><td>The temporary code that was delivered.</td></tr></tbody></table>

### *AuthTokenExchange* object

<table><thead><tr><th width="200.33333333333331">Property</th><th width="118">Type</th><th>Description</th></tr></thead><tbody><tr><td><code>access_token</code></td><td>String</td><td>The generated permanent user access token.</td></tr><tr><td><code>token_type</code></td><td>String</td><td>The type of token. The only value is <code>Bearer</code>.</td></tr></tbody></table>

### *AuthServiceTokenRequest* object

<table><thead><tr><th width="185">Name</th><th width="120">Type</th><th width="83">Required</th><th>Description</th></tr></thead><tbody><tr><td><code>grant_type</code></td><td>String</td><td>Yes</td><td>The only accepted value is <code>client_credentials</code>.</td></tr><tr><td><code>client_id</code></td><td>String</td><td>Yes</td><td>The ID of the calling client application.</td></tr><tr><td><code>client_secret</code></td><td>String</td><td>Yes</td><td>The client secret associated to the client ID.</td></tr><tr><td><code>scope</code></td><td><a href="#authscope-values"><em>AuthScope</em></a> string or array</td><td>Yes</td><td>The permission scopes to authorize for this token.<br>It can be a simple string value, or an array for multiple scopes.</td></tr></tbody></table>

### *AuthScope* values

<table><thead><tr><th width="108.33333333333331">Product</th><th width="228">Name</th><th>Description</th></tr></thead><tbody><tr><td>Pay</td><td><code>payments:admin</code></td><td>Grants all rights on payments.</td></tr><tr><td>Pay</td><td><code>payments:read-only</code></td><td>Only GET requests are allowed on payments.</td></tr><tr><td>Pay</td><td><code>payments:allow-sensitive</code></td><td>Grants read access on sensitive information for payments.</td></tr><tr><td>Pay</td><td><code>payments:validate</code></td><td>Allows to execute payments.</td></tr><tr><td>Pay</td><td><code>payments:cancel</code></td><td>Allows to submit payment cancellation requests.</td></tr><tr><td>Pay</td><td><del><code>payments</code></del></td><td><em>(Deprecated)</em>. Alias for <code>payments:admin</code>.</td></tr><tr><td>Pay</td><td><code>payment-links:admin</code></td><td>Allows management of <a href="https://app.gitbook.com/o/BoQ3mPSOBzPKMWXiBuvS/s/jaOZc6CNFstFU2WHDyoU/~/changes/80/products/payments/payment-links">payment links</a>.</td></tr></tbody></table>

### *AuthServiceToken* object

<table><thead><tr><th width="156.33333333333331">Property</th><th width="137">Type</th><th>Description</th></tr></thead><tbody><tr><td><code>token</code></td><td>String</td><td>The generated service token.</td></tr><tr><td><code>scope</code></td><td>String</td><td>The service token dedicated scope.</td></tr></tbody></table>

### *AuthRenewRequest* object

<table><thead><tr><th width="203">Name</th><th width="98">Type</th><th width="82">Required</th><th>Description</th></tr></thead><tbody><tr><td><code>grant_type</code></td><td>String</td><td>Yes</td><td>The only accepted value is <code>client_credentials</code>.</td></tr><tr><td><code>client_id</code></td><td>String</td><td>Yes</td><td>The ID of the calling client application.</td></tr><tr><td><code>client_secret</code></td><td>String</td><td>Yes</td><td>The client secret associated with the client ID.</td></tr><tr><td><code>id_user</code></td><td>Integer</td><td>Yes</td><td>User for whom the token has to be generated. If not supplied, a user will be created.</td></tr><tr><td><code>revoke_previous</code></td><td>Boolean</td><td>No</td><td>If true, all other permanent tokens for the user will be deleted. The default is false.</td></tr></tbody></table>


---

# Agent Instructions: Querying This Documentation

If you need additional information that is not directly available in this page, you can query the documentation dynamically by asking a question.

Perform an HTTP GET request on the current page URL with the `ask` query parameter:

```
GET https://docs.powens.com/api-reference/overview/authentication.md?ask=<question>
```

The question should be specific, self-contained, and written in natural language.
The response will contain a direct answer to the question and relevant excerpts and sources from the documentation.

Use this mechanism when the answer is not explicitly present in the current page, you need clarification or additional context, or you want to retrieve related documentation sections.
