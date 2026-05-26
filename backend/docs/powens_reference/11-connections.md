# Connections

## API endpoints

{% hint style="success" %}
Authentication: endpoints listed in this page *require* [header authentication](/api-reference/overview/authentication.md) with a *user token*.
{% endhint %}

### Connections management

## Create a new connection

<mark style="color:green;">`POST`</mark> `https://{domain}.biapi.pro/2.0/users/{userId}/connections`

Request body: [#connectionrequest-object](#connectionrequest-object "mention")

#### Path Parameters

| Name                                     | Type             | Description             |
| ---------------------------------------- | ---------------- | ----------------------- |
| userId<mark style="color:red;">\*</mark> | Interger or "me" | ID of the related user. |

{% tabs %}
{% tab title="201: Created Connection created" %}
Response body: [#connection-object](#connection-object "mention")
{% endtab %}

{% tab title="400: Bad Request Invalid credentials" %}
Response body: [Errors](/api-reference/overview/errors.md#error-response) with `wrongPass` code
{% endtab %}
{% endtabs %}

## List connections

<mark style="color:blue;">`GET`</mark> `https://{domain}.biapi.pro/2.0/users/{userId}/connections`

#### Path Parameters

| Name                                     | Type             | Description             |
| ---------------------------------------- | ---------------- | ----------------------- |
| userId<mark style="color:red;">\*</mark> | Interger or "me" | ID of the related user. |

{% tabs %}
{% tab title="200: OK List of connections" %}
Response body: [#list-connections-1](#list-connections-1 "mention")
{% endtab %}
{% endtabs %}

## Get a connection

<mark style="color:blue;">`GET`</mark> `https://{domain}.biapi.pro/2.0/users/{userId}/connections/{connectionId}`

Get a single connection by ID.

#### Path Parameters

| Name                                           | Type             | Description             |
| ---------------------------------------------- | ---------------- | ----------------------- |
| userId<mark style="color:red;">\*</mark>       | Interger or "me" | ID of the related user. |
| connectionId<mark style="color:red;">\*</mark> | Integer          | ID of the connection.   |

{% tabs %}
{% tab title="200: OK Connection details" %}
Response body: [#connection-object](#connection-object "mention")
{% endtab %}
{% endtabs %}

## Update a connection

<mark style="color:green;">`POST`</mark> `https://{domain}.biapi.pro/2.0/users/{userId}/connections/{connectionId}`

Update a single connection by ID.

Request body: [#update-a-connection-1](#update-a-connection-1 "mention")

#### Path Parameters

| Name                                           | Type             | Description             |
| ---------------------------------------------- | ---------------- | ----------------------- |
| userId<mark style="color:red;">\*</mark>       | Interger or "me" | ID of the related user. |
| connectionId<mark style="color:red;">\*</mark> | Integer          | ID of the connection.   |

#### Query Parameters

| Name       | Type    | Description                                                                                                                                                                                                                                                |
| ---------- | ------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| background | Boolean | Flag to make the request asynchronous (i.e. the API will respond immediately and process the synchronization with the bank in background). When using this option, you must implement [polling on the connection](#get-a-connection) to monitor the state. |

{% tabs %}
{% tab title="200: OK Connection updated" %}
Response body: [#connection-object](#connection-object "mention")
{% endtab %}

{% tab title="400: Bad Request Invalid credentials" %}
Response body: [Errors](/api-reference/overview/errors.md#error-response) with `wrongPass` code
{% endtab %}
{% endtabs %}

## Sync a connection

<mark style="color:orange;">`PUT`</mark> `https://{domain}.biapi.pro/2.0/users/{userId}/connections/{connectionId}`

Request synchronization of a single connection by ID.

#### Path Parameters

| Name                                           | Type             | Description             |
| ---------------------------------------------- | ---------------- | ----------------------- |
| userId<mark style="color:red;">\*</mark>       | Interger or "me" | ID of the related user. |
| connectionId<mark style="color:red;">\*</mark> | Integer          | ID of the connection.   |

#### Query Parameters

| Name           | Type    | Description                                                                                                                                                                                                                                                                        |
| -------------- | ------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| psu\_requested | Boolean | Flag to indicate whether the refresh of the connection was asked by the final user. If set to `true` (the default) the process might trigger an SCA. If you wish to force synchronization when the PSU is not in your application you must set it to false for compliance reasons. |

{% tabs %}
{% tab title="200: OK Connection details" %}
Response body: [#connection-object](#connection-object "mention")
{% endtab %}
{% endtabs %}

## Delete a connection

<mark style="color:red;">`DELETE`</mark> `https://{domain}.biapi.pro/2.0/users/{userId}/connections/{connectionId}`

This operation deletes the connection and all its related data (accounts, transactions, subscriptions, documents, identities...). This is a hard delete and cannot be reversed: the data (including full history) is permanently erased from Powens' databases. \
\
This operation meets GDPR requirements related to the deletion of personal data. &#x20;

#### Path Parameters

| Name                                           | Type             | Description             |
| ---------------------------------------------- | ---------------- | ----------------------- |
| userId<mark style="color:red;">\*</mark>       | Interger or "me" | ID of the related user. |
| connectionId<mark style="color:red;">\*</mark> | Integer          | ID of the connection.   |

{% tabs %}
{% tab title="204: No Content Connection details" %}
Response body: [#connection-object](#connection-object "mention")
{% endtab %}
{% endtabs %}

### Web authorization

## Construct a connection URL for web authorization

<mark style="color:blue;">`GET`</mark> `https://{domain}.biapi.pro/2.0/webauth-url`

Constructs a connection URL for connectors (and sources) using the `webauth` auth mechanism. The same service can be used for both establishing a new connection and resuming an existing connection that requires an update for SCA or consent renewal (i.e. in the [`SCARequired` state](https://docs.budget-insight.com/reference/connections#connectionstate-values)).

The returned URL should be presented on the device of the PSU using the most appropriate front-end components, taking full advantage of URL-handling behaviors to enable app-to-app experiences when available.

#### Query Parameters

| Name                                            | Type    | Description                                                                                                                                           |
| ----------------------------------------------- | ------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| client\_id<mark style="color:red;">\*</mark>    | Integer | The client ID of your client application.                                                                                                             |
| redirect\_uri<mark style="color:red;">\*</mark> | String  | The final redirect URL to be redirected to after the flow has completed. This URL must not contain query parameters. Make sure to properly encode it. |
| id\_connector                                   | Integer | To add a new connection only, the ID of the connector. The connector must have `webauth` as its `auth_mechanism`.                                     |
| id\_connection                                  | Integer | To recover or resume a connection only, the ID of the connection.                                                                                     |
| source                                          | String  | The specific source (designated by its `name`) to add or reset when interacting with bank connectors.                                                 |
| state                                           | String  | An optional opaque string that will be returned 'as is' with the redirect URL.                                                                        |

{% tabs %}
{% tab title="200: OK URL created" %}
Response body: [#webauthurl-object](#webauthurl-object "mention")
{% endtab %}

{% tab title="409: Conflict Invalid connection state" %}
The connection is already up to date and a connection URL cannot be provided.

Response body: [Errors](/api-reference/overview/errors.md#error-response) with `invalidValue` code
{% endtab %}
{% endtabs %}

## Redirect to a URL for web authorization

<mark style="color:blue;">`GET`</mark> `https://{domain}.biapi.pro/2.0/webauth`

The [`/webauth-url` endpoint](#construct-a-connection-url-for-web-authorization) provides an alternate (recommended) way to obtain the redirection URL in order to optimize app-to-app experiences.

This endpoint is a special redirection service to help presenting the auth webview from a connector (e.g. using OAuth2 protocol). This service is not an API endpoint, the URL must be navigated to in a browser.

#### Query Parameters

| Name                                            | Type    | Description                                                                                                                                           |
| ----------------------------------------------- | ------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| client\_id<mark style="color:red;">\*</mark>    | Integer | The client ID of your client application.                                                                                                             |
| redirect\_uri<mark style="color:red;">\*</mark> | String  | The final redirect URL to be redirected to after the flow has completed. This URL must not contain query parameters. Make sure to properly encode it. |
| id\_connector                                   | Integer | To add a new connection only, the ID of the connector. The connector must have `webauth` as its `auth_mechanism`.                                     |
| id\_connection                                  | Integer | To recover or resume a connection only, the ID of the connection.                                                                                     |
| source                                          | String  | The specific source (designated by its `name`) to add or reset when interacting with bank connectors.                                                 |
| state                                           | String  | An optional opaque string that will be returned 'as is' with the redirect URL.                                                                        |
| token                                           | String  | A temporary [authorization code](/api-reference/overview/authentication.md#generate-a-temporary-code) to secure the call.                             |

{% tabs %}
{% tab title="307: Temporary Redirect Redirection to the connector URL" %}
Response body: [#webauthurl-object](#webauthurl-object "mention")
{% endtab %}
{% endtabs %}

{% hint style="info" %}
To optimize user experience, the URL should be opened in a fully-capable browser. From a website or webapp, perform a [full-page redirect](https://developer.mozilla.org/fr/docs/Web/HTTP/Status/302). In a native Android app, prefer opening the default browser or relying on [Chrome Custom Tabs](https://developer.chrome.com/multidevice/android/customtabs). In a native iOS app, prefer using a [SFSafariViewController](https://developer.apple.com/documentation/safariservices/sfsafariviewcontroller).
{% endhint %}

After the flow has terminated, a redirection will be performed to the provided `redirect_uri`, with additional query parameters:

#### **Success callback parameters**

<table><thead><tr><th width="224">Parameter</th><th width="87">Type</th><th>Description</th></tr></thead><tbody><tr><td><code>id_connection</code></td><td>Integer</td><td>The ID of the connection that was created or updated during the webauth flow.</td></tr></tbody></table>

#### **Error callback parameters**

<table><thead><tr><th width="225">Parameter</th><th width="90">Type</th><th>Description</th></tr></thead><tbody><tr><td><code>error</code></td><td>String</td><td>This parameter is added if an error occurred.</td></tr><tr><td><code>error_description</code></td><td>String</td><td>The description of the error, if available.</td></tr></tbody></table>

### Connection sources management

## List sources of a connection

<mark style="color:blue;">`GET`</mark> `https://{domain}.biapi.pro/2.0/users/{userId}/connections/{connectionId}/sources`

By default, `disabled` sources are omitted in the response. Add the `all` query parameter to include them.

#### Path Parameters

| Name                                           | Type             | Description             |
| ---------------------------------------------- | ---------------- | ----------------------- |
| userId<mark style="color:red;">\*</mark>       | Interger or "me" | ID of the related user. |
| connectionId<mark style="color:red;">\*</mark> | Integer          | ID of the connection.   |

#### Query Parameters

| Name | Type       | Description                       |
| ---- | ---------- | --------------------------------- |
| all  | Value-less | Flag to include disabled sources. |

{% tabs %}
{% tab title="200: OK List of connection sources" %}
Response body: [#delete-a-connection-1](#delete-a-connection-1 "mention")
{% endtab %}
{% endtabs %}

## Get a connection source

<mark style="color:blue;">`GET`</mark> `https://{domain}.biapi.pro/2.0/users/{userId}/connections/{connectionId}/sources/{sourceId}`

#### Path Parameters

| Name                                           | Type             | Description             |
| ---------------------------------------------- | ---------------- | ----------------------- |
| userId<mark style="color:red;">\*</mark>       | Interger or "me" | ID of the related user. |
| connectionId<mark style="color:red;">\*</mark> | Integer          | ID of the connection.   |
| sourceId<mark style="color:red;">\*</mark>     | Integer          | ID of the source.       |

#### Query Parameters

| Name | Type       | Description                                 |
| ---- | ---------- | ------------------------------------------- |
| all  | Value-less | Flag to enable access to a disabled source. |

{% tabs %}
{% tab title="200: OK Connection source details" %}
Response body: [#connectionsource-object](#connectionsource-object "mention")
{% endtab %}
{% endtabs %}

## Update a connection source

<mark style="color:green;">`POST`</mark> `https://{domain}.biapi.pro/2.0/users/{userId}/connections/{connectionId}/sources/{sourceId}`

Request body: [#connectionsourceupdaterequest-object](#connectionsourceupdaterequest-object "mention")

#### Path Parameters

| Name                                           | Type             | Description             |
| ---------------------------------------------- | ---------------- | ----------------------- |
| userId<mark style="color:red;">\*</mark>       | Interger or "me" | ID of the related user. |
| connectionId<mark style="color:red;">\*</mark> | Integer          | ID of the connection.   |
| sourceId<mark style="color:red;">\*</mark>     | Integer          | ID of the source.       |

#### Query Parameters

| Name | Type       | Description                                 |
| ---- | ---------- | ------------------------------------------- |
| all  | Value-less | Flag to enable access to a disabled source. |

{% tabs %}
{% tab title="200: OK Connection source details" %}
Response body: [#connectionsource-object](#connectionsource-object "mention")
{% endtab %}
{% endtabs %}

### Connection logs

## List synchronization logs

<mark style="color:blue;">`GET`</mark> `https://{domain}.biapi.pro/2.0/users/{userId}/connections/{connectionId}/logs`

List synchronization logs of a connection by ID.

#### Path Parameters

| Name                                           | Type             | Description             |
| ---------------------------------------------- | ---------------- | ----------------------- |
| userId<mark style="color:red;">\*</mark>       | Interger or "me" | ID of the related user. |
| connectionId<mark style="color:red;">\*</mark> | Integer          | ID of the connection.   |

#### Query Parameters

| Name       | Type    | Description                |
| ---------- | ------- | -------------------------- |
| limit      | Integer | Maximum number of results. |
| offset     | Integer | First result offset.       |
| min\_date  | Date    | Minimum date.              |
| max\_date  | Date    | Maximum date.              |
| id\_source | Integer | ID of a connection source. |

{% tabs %}
{% tab title="200: OK List of connection sources" %}
Response body: [#delete-a-connection-1](#delete-a-connection-1 "mention")
{% endtab %}
{% endtabs %}

## Webhooks

### Connection synced <a href="#connection-synced" id="connection-synced"></a>

A `CONNECTION_SYNCED` webhook is emitted after a connection has been synced.

Webhook request:

| Property                                      | Type                                                                                                                  | Description                                                                                     |
| --------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `user`                                        | [*User*](/api-reference/user-connections/users.md#user-object) object                                                 | The user related to the sync.                                                                   |
| `connection`                                  | [*Connection*](#connection-object) object                                                                             | The connection details.                                                                         |
| `connection.connector`                        | [*Connector*](/api-reference/user-connections/connectors.md#connector-object) object                                  | The connector associated with the connection.                                                   |
| `connection.sources`                          | Array of [*ConnectionSource*](#connectionsource-object) objects                                                       | The activated connection sources that were synced.                                              |
| `connection.accounts`                         | Array of [*BankAccount*](/api-reference/products/data-aggregation/bank-accounts.md#bankaccount-object) objects        | The activated bank accounts sources that were synced.                                           |
| `connection.accounts[].investments`           | Array of [*Investment*](/api-reference/products/wealth-aggregation/investments.md#investment-object) objects          | On each `account` item, the new investments that were found.                                    |
| `connection.accounts[].market_orders`         | Array of [*MarketOrder*](/api-reference/products/wealth-aggregation/market-orders.md#marketorder-object) objects      | On each `account` item, the new market orders that were found.                                  |
| `connection.accounts[].investments[].pockets` | Array of [*Pocket*](/api-reference/products/wealth-aggregation/pockets.md#pocket-object) objects                      | On each `investment` item, the new pockets that were found.                                     |
| ~~`connection.accounts[].recipients`~~        | Array of [*Recipient*](/api-reference/products/payments/transfers-obsolete.md#recipient-object) objects               | *(Deprecated)* On each `account` item, the new recipients that were found (for transfer usage). |
| `connection.accounts[].transactions`          | Array of [*Transaction*](/api-reference/products/data-aggregation/bank-transactions.md#transaction-object) objects    | On each `account` item, the new transactions that were found.                                   |
| ~~`connection.accounts[].transfers`~~         | Array of [*Transfer*](/api-reference/products/payments/transfers-obsolete.md#transfer-object) objects                 | *(Deprecated)* On each `account` item, the new transfers that were made.                        |
| `connection.subscriptions`                    | Array of [*Subscription*](/api-reference/products/documents-aggregation/subscriptions.md#subscription-object) objects | The activated subscriptions sources that were synced.                                           |
| `connection.subscriptions[].documents`        | Array of [*Document*](/api-reference/products/documents-aggregation/documents.md#document-object) objects             | On each `subscription` item, the new documents that were found.                                 |

### Connection deleted <a href="#connection-deleted" id="connection-deleted"></a>

A `CONNECTION_DELETED` webhook is emitted after a connection has been deleted.

Webhook request: [Connections](/api-reference/user-connections/connections.md#connection-object)

## Data model

### ***ConnectionRequest*****&#x20;object**

<table><thead><tr><th width="194">Name</th><th width="92">Type</th><th width="107">Required</th><th>Description</th></tr></thead><tbody><tr><td><code>id_connector</code></td><td>Integer</td><td>No</td><td>ID of the connector. Required if <code>connector_uuid</code> is not provided.</td></tr><tr><td><code>connector_uuid</code></td><td>String</td><td>No</td><td>UUID of the connector. Required if <code>id_connector</code> is not provided.</td></tr><tr><td><code>source</code></td><td>String</td><td>No</td><td>The specific source (designated by its <code>name</code>) to add when interacting with bank connectors.</td></tr></tbody></table>

To add a connection to a connector/source using the `credentials` [*AuthMechanism*](/api-reference/user-connections/connectors.md#authmechanism-values), you must also include in the request values from the [connector `fields`](/api-reference/user-connections/connectors.md#connector-object) definition.

### *ConnectionsList* object <a href="#list-connections" id="list-connections"></a>

<table><thead><tr><th width="190.33333333333331">Property</th><th>Type</th><th>Description</th></tr></thead><tbody><tr><td><code>connections</code></td><td>Array of <a href="#connection-object"><em>Connection</em></a> objects</td><td>List of connections.</td></tr></tbody></table>

### ***Connection*****&#x20;object**

<table><thead><tr><th width="192.33333333333331">Property</th><th width="171">Type</th><th>Description</th></tr></thead><tbody><tr><td><code>id</code></td><td>Integer</td><td>ID of the connection.</td></tr><tr><td><code>id_user</code></td><td>Integer or null</td><td>ID of the related user.</td></tr><tr><td><code>id_connector</code></td><td>Integer</td><td>ID of the related connector.</td></tr><tr><td><del><code>id_provider</code></del></td><td>Integer</td><td><em>(Deprecated)</em> ID of the provider.</td></tr><tr><td><del><code>id_bank</code></del></td><td>Integer</td><td><em>(Deprecated)</em> ID of the bank.</td></tr><tr><td><code>state</code></td><td><a href="#connectionstate-values"><em>ConnectionState</em></a> string or null</td><td>If the last update failed, the state code. The <code>null</code> value indicates a successful sync.</td></tr><tr><td><del><code>error</code></del></td><td><a href="#connectionstate-values"><em>ConnectionState</em></a> string or null</td><td><em>(Deprecated)</em> If the last update failed, the state code. The <code>null</code> value indicates a successful sync.</td></tr><tr><td><code>error_message</code></td><td>String or null</td><td>If the last update failed, an optional message from the institution to guide the user into recovering from the error.</td></tr><tr><td><code>fields</code></td><td>Array of <a href="/pages/aEgj6uKNfjLxPdpZ831x#connectorfield-object"><em>ConnectorField</em></a> objects or null</td><td>For connections in an error state, an optional list of connector fields that must be prompted to the end-user.</td></tr><tr><td><code>last_update</code></td><td>DateTime or null</td><td>Last successful update.</td></tr><tr><td><code>created</code></td><td>DateTime or null</td><td>Creation date of the connection.</td></tr><tr><td><code>active</code></td><td>Boolean</td><td>Whether this connection is active and will be automatically synced.</td></tr><tr><td><code>last_push</code></td><td>DateTime or null</td><td>Last successful push.</td></tr><tr><td><code>expire</code></td><td>DateTime or null</td><td>Highest value among expiration dates of connection sources.</td></tr><tr><td><code>connector_uuid</code></td><td>String</td><td>UUID of the related connector.</td></tr><tr><td><code>next_try</code></td><td>DateTime or null</td><td>Scheduled date of next synchronization.</td></tr></tbody></table>

**Available expands**

The following parameters can be used for [response properties expansion](/api-reference/overview/api-design.md#responses-expansion):

<table><thead><tr><th width="220.33333333333331">Property</th><th width="195">Type</th><th>Description</th></tr></thead><tbody><tr><td><code>connector</code></td><td><a href="/pages/aEgj6uKNfjLxPdpZ831x#connector-object"><em>Connector</em></a> object</td><td>The connector associated with this connection.</td></tr><tr><td><code>accounts</code></td><td>Array of <a href="/pages/6ZTi4nFvuqvWCMNrWCTt#bankaccount-object"><em>BankAccount</em></a> objects</td><td>The list of <strong>activated</strong> bank accounts associated with the connection (disabled accounts are omitted).</td></tr><tr><td><code>all_accounts</code></td><td>Array of <a href="/pages/6ZTi4nFvuqvWCMNrWCTt#bankaccount-object"><em>BankAccount</em></a> objects</td><td>The list of all bank accounts associated with the connection, including disabled ones.</td></tr><tr><td><code>subscriptions</code></td><td>Array of <a href="/pages/AJVkwP6UegvhEPl4PRoH#subscription-object"><em>Subscription</em></a> objects</td><td>The list of <strong>activated</strong> subscriptions associated with the connection (disabled subscriptions are omitted).</td></tr><tr><td><code>all_subscriptions</code></td><td>Array of <a href="/pages/AJVkwP6UegvhEPl4PRoH#subscription-object"><em>Subscription</em></a> objects</td><td>The list of all subscriptions associated with the connection, including disabled ones.</td></tr><tr><td><code>sources</code></td><td>Array of <a href="#connectionsource-object"><em>ConnectionSource</em></a> objects</td><td>The details of the sources configured for the connection.</td></tr></tbody></table>

### ***ConnectionState*****&#x20;values**

Instructions for presenting and processing the various error states are available in <mark style="background-color:orange;">our dedicated integration guide</mark>.

<table><thead><tr><th width="258">Value</th><th>Description</th></tr></thead><tbody><tr><td><code>SCARequired</code></td><td>An SCA process must be performed to resume the synchronization process.</td></tr><tr><td><code>webauthRequired</code></td><td>A web-based authentication process is required using <a href="/pages/5W80jLGBq7ifvqhRCiXo#webauthurl-object">the /webauth endpoint</a>.</td></tr><tr><td><code>additionalInformationNeeded</code></td><td>Additional information is needed to resume synchronization, such as an OTP. Connections in this state have a <code>fields</code> property.</td></tr><tr><td><code>decoupled</code></td><td>User validation is required on a third-party app or device (ex: digital key).</td></tr><tr><td><code>validating</code></td><td>User validation is being processed on our side. This state is temporary.</td></tr><tr><td><code>actionNeeded</code></td><td>An action is needed on the website by the user, synchronization is blocked.</td></tr><tr><td><code>passwordExpired</code></td><td>The password has expired and needs to be changed by the user before the synchronization can be retried.</td></tr><tr><td><code>wrongpass</code></td><td>The authentication on website has failed and new credentials must be obtained from the user. Connections in this state have a <code>fields</code> property.</td></tr><tr><td><code>rateLimiting</code></td><td>The target website or API is temporarily blocking synchronizations due to rate limiting.</td></tr><tr><td><code>websiteUnavailable</code></td><td>The connector website or API is unavailable.</td></tr><tr><td><code>bug</code></td><td>An internal error has occurred during the synchronization.</td></tr><tr><td><code>notSupported</code></td><td>The source is not supported on the connector.</td></tr></tbody></table>

{% hint style="info" %}
Forward compatibility requirement: additional states may be added in the future. When implementing state handling, always fallback to a non-resolvable generic case for unknown values.
{% endhint %}

### *ConnectionUpdateRequest* object <a href="#update-a-connection" id="update-a-connection"></a>

<table><thead><tr><th width="175">Property</th><th width="107">Type</th><th width="103">Required</th><th>Description</th></tr></thead><tbody><tr><td><code>source</code></td><td>String</td><td>No</td><td>The specific source (designated by its <code>name</code>) to add or update when interacting with bank connectors.</td></tr><tr><td><code>active</code></td><td>Boolean</td><td>No</td><td>Whether the connection synchronization is active.</td></tr><tr><td><code>expire</code></td><td>DateTime</td><td>No</td><td>Set expiration of the connection to this date.</td></tr><tr><td><code>resume</code></td><td>Boolean</td><td>No</td><td>Resume a connection in the <code>decoupled</code> state.</td></tr><tr><td><code>refresh_auth</code></td><td>Boolean</td><td>No</td><td>For PSD2 connections, renew the PSU's authorization before its automatic expiration. This process <em>will</em> trigger an SCA. This flag is only effective for the <code>openapi</code> source, if any.</td></tr></tbody></table>

To edit a connection source using the `credentials` [*AuthMechanism*](/api-reference/user-connections/connectors.md#authmechanism-values), you can also include in the request new values from the connector `fields`.

### ***ConnectionSourcesList*****&#x20;object** <a href="#delete-a-connection" id="delete-a-connection"></a>

<table><thead><tr><th width="141.33333333333331">Property</th><th>Type</th><th>Description</th></tr></thead><tbody><tr><td><code>sources</code></td><td>Array of <a href="#connectionsource-object"><em>ConnectionSource</em></a> objects</td><td>Sources of the connection.</td></tr></tbody></table>

### ***ConnectionSource*****&#x20;object**

<table><thead><tr><th width="241.33333333333331">Property</th><th width="163">Type</th><th>Description</th></tr></thead><tbody><tr><td><code>id</code></td><td>Integer</td><td>ID of the connection source.</td></tr><tr><td><code>id_connection</code></td><td>Integer</td><td>ID of the related connection.</td></tr><tr><td><code>id_connector_source</code></td><td>Integer</td><td>ID of the related connector source.</td></tr><tr><td><code>name</code></td><td>String</td><td>Name of the connection source.</td></tr><tr><td><code>last_update</code></td><td>DateTime or null</td><td>Last successful update of the source.</td></tr><tr><td><code>disabled</code></td><td>DateTime or null</td><td>If set, this source is ignored on synchronizing the connection.</td></tr><tr><td><code>created</code></td><td>DateTime</td><td>Creation date of the connection source.</td></tr><tr><td><code>state</code></td><td><a href="#connectionstate-values"><em>ConnectionState</em></a> string or null</td><td>If the last update has failed, the state code. The null value indicates a successful sync.</td></tr><tr><td><code>access_expire</code></td><td>DateTime or null</td><td>Expiration date of the access, if known.</td></tr><tr><td><code>expire</code></td><td>DateTime or null</td><td>Expiration of the connection source. Used to purge the connection in case completion was not finished.</td></tr><tr><td><code>next_try</code></td><td>DateTime or null</td><td>Scheduled date of next synchronization.</td></tr></tbody></table>

### *ConnectionSourceUpdateRequest* object

<table><thead><tr><th width="175">Property</th><th width="107">Type</th><th width="103">Required</th><th>Description</th></tr></thead><tbody><tr><td><code>disabled</code></td><td>Boolean</td><td>No</td><td>Whether the source should be disabled or not.</td></tr></tbody></table>

### ***WebauthURL*****&#x20;object**

<table><thead><tr><th width="164.33333333333331">Property</th><th width="183">Type</th><th>Description</th></tr></thead><tbody><tr><td><code>url</code></td><td>String</td><td>The URL to display.</td></tr></tbody></table>


---

# Agent Instructions: Querying This Documentation

If you need additional information that is not directly available in this page, you can query the documentation dynamically by asking a question.

Perform an HTTP GET request on the current page URL with the `ask` query parameter:

```
GET https://docs.powens.com/api-reference/user-connections/connections.md?ask=<question>
```

The question should be specific, self-contained, and written in natural language.
The response will contain a direct answer to the question and relevant excerpts and sources from the documentation.

Use this mechanism when the answer is not explicitly present in the current page, you need clarification or additional context, or you want to retrieve related documentation sections.
