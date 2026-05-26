# Connectors

## API endpoints

{% hint style="success" %}
Authentication: endpoints listed in this page do not require authentication.
{% endhint %}

### Connectors

## List connectors

<mark style="color:blue;">`GET`</mark> `https://{domain}.biapi.pro/2.0/connectors`

List all connectors available on the domain.

This endpoint *does not require* authentication.

#### Query Parameters

| Name           | Type   | Description                                                                                                              |
| -------------- | ------ | ------------------------------------------------------------------------------------------------------------------------ |
| country\_codes | String | Filter on countries, using comma-separated [ISO 3166-1 alpha-2 codes](https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2). |
| id\_payment    | String | Filter on a payment id to get only the connectors compatible with this payment.                                          |

{% tabs %}
{% tab title="200: OK List of connectors" %}
Response body: [#connectorslist-object](#connectorslist-object "mention")
{% endtab %}
{% endtabs %}

{% code title="Deprecated route aliases:" %}

```http
/banks
/providers
```

{% endcode %}

## Get a connector

<mark style="color:blue;">`GET`</mark> `https://{domain}.biapi.pro/2.0/connectors/{connectorUuid}`

Get a single connector by UUID.

This endpoint *does not require* authentication.

#### Path Parameters

| Name                                            | Type   | Description                                                          |
| ----------------------------------------------- | ------ | -------------------------------------------------------------------- |
| connectorUuid<mark style="color:red;">\*</mark> | String | <p>UUID of the connector.<br>IDs are also accepted (deprecated).</p> |

{% tabs %}
{% tab title="200: OK Connector" %}
Response body: [#connector-object](#connector-object "mention")
{% endtab %}
{% endtabs %}

## Update a connector

<mark style="color:orange;">`PUT`</mark> `https://{domain}.biapi.pro/2.0/connectors/{connectorUuid}`

This endpoint *requires* [header authentication](/api-reference/overview/authentication.md) with a *config token*.

Request body: [#update-a-connector-1](#update-a-connector-1 "mention")

#### Path Parameters

| Name                                            | Type   | Description                                                          |
| ----------------------------------------------- | ------ | -------------------------------------------------------------------- |
| connectorUuid<mark style="color:red;">\*</mark> | String | <p>UUID of the connector.<br>IDs are also accepted (deprecated).</p> |

{% tabs %}
{% tab title="200: OK Connector updated" %}
Response body: [#connector-object](#connector-object "mention")
{% endtab %}
{% endtabs %}

## Batch enable/disable connectors

<mark style="color:purple;">`PATCH`</mark> `https://{domain}.biapi.pro/2.0/connectors`

This endpoint *requires* [header authentication](/api-reference/overview/authentication.md) with a *config token*.

Request body: A key-value object with connector UUIDs as keys, and [#update-a-connector-1](#update-a-connector-1 "mention") as value.

{% tabs %}
{% tab title="200: OK Connectors updated" %}

{% endtab %}
{% endtabs %}

## Batch enable/disable connectors (deprecated)

<mark style="color:orange;">`PUT`</mark> `https://{domain}.biapi.pro/2.0/connectors/{connectorIds}`

This endpoint *requires* [header authentication](/api-reference/overview/authentication.md) with a *config token*.

Request body: [#update-a-connector-1](#update-a-connector-1 "mention")

#### Path Parameters

| Name                                           | Type   | Description                                      |
| ---------------------------------------------- | ------ | ------------------------------------------------ |
| connectorIds<mark style="color:red;">\*</mark> | String | Comma-separated list of connector IDs to update. |

{% tabs %}
{% tab title="200: OK Connectors updated" %}
Response body: [#connector-object](#connector-object "mention")
{% endtab %}
{% endtabs %}

### Connector sources

## List connector sources

<mark style="color:blue;">`GET`</mark> `https://{domain}.biapi.pro/2.0/connectors/{connectorUuid}/sources`

This endpoint *does not require* authentication.

#### Path Parameters

| Name                                            | Type   | Description                    |
| ----------------------------------------------- | ------ | ------------------------------ |
| connectorUuid<mark style="color:red;">\*</mark> | String | UUID or the related connector. |

#### Query Parameters

| Name           | Type   | Description                                                                                                              |
| -------------- | ------ | ------------------------------------------------------------------------------------------------------------------------ |
| country\_codes | String | Filter on countries, using comma-separated [ISO 3166-1 alpha-2 codes](https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2). |

{% tabs %}
{% tab title="200: OK List of connector sources" %}
Response body: [#connectorsourceslist-object](#connectorsourceslist-object "mention")
{% endtab %}
{% endtabs %}

## Get a connector source

<mark style="color:blue;">`GET`</mark> `https://{domain}.biapi.pro/2.0/connectors/{connectorUuid}/sources/{sourceId}`

This endpoint *does not require* authentication.

#### Path Parameters

| Name                                            | Type    | Description                    |
| ----------------------------------------------- | ------- | ------------------------------ |
| connectorUuid<mark style="color:red;">\*</mark> | String  | UUID or the related connector. |
| sourceId<mark style="color:red;">\*</mark>      | Integer | ID of the connector source.    |

{% tabs %}
{% tab title="200: OK Connector source details" %}
Response body: [#connectorsource-object](#connectorsource-object "mention")
{% endtab %}
{% endtabs %}

## Update a connector source

<mark style="color:orange;">`PUT`</mark> `https://{domain}.biapi.pro/2.0/connectors/{connectorUuid}/sources/{sourceId}`

This endpoint *requires* [header authentication](/api-reference/overview/authentication.md) with a *config token*.

Request body: [#update-a-connector-source-1](#update-a-connector-source-1 "mention")

#### Path Parameters

| Name                                            | Type    | Description                    |
| ----------------------------------------------- | ------- | ------------------------------ |
| connectorUuid<mark style="color:red;">\*</mark> | String  | UUID or the related connector. |
| sourceId<mark style="color:red;">\*</mark>      | Integer | ID of the connector source.    |

{% tabs %}
{% tab title="200: OK Connector source updated" %}
Response body: [#connectorsource-object](#connectorsource-object "mention")
{% endtab %}
{% endtabs %}

## Data model

### ***ConnectorsList*****&#x20;object**

<table><thead><tr><th width="213.33333333333331">Property</th><th width="185">Type</th><th>Description</th></tr></thead><tbody><tr><td><code>connectors</code></td><td>Array of <a href="#connector-object"><em>Connector</em></a> objects</td><td>The list of connectors. The key is absent on deprecated endpoint routes.</td></tr><tr><td><del><code>banks</code></del></td><td>Array of <a href="#connector-object"><em>Connector</em></a> objects</td><td>(<em>Deprecated</em>) The list of connectors. The key is only present on deprecated endpoint routes.</td></tr></tbody></table>

### ***Connector*****&#x20;object**

<table><thead><tr><th width="203.33333333333331">Property</th><th width="209">Type</th><th>Description</th></tr></thead><tbody><tr><td><code>id</code></td><td>Integer</td><td>ID of the connector, <em>not</em> stable across API domains.</td></tr><tr><td><code>uuid</code></td><td>String</td><td>Unique connector identifier, stable across API domains.</td></tr><tr><td><code>name</code></td><td>String</td><td>Name of the bank or provider.</td></tr><tr><td><code>hidden</code></td><td>Boolean or null</td><td>Whether this connector is hidden from users.</td></tr><tr><td><code>charged</code></td><td>Boolean</td><td>Usage of this connector is charged.</td></tr><tr><td><code>code</code></td><td>String or null</td><td>Bank code.</td></tr><tr><td><code>beta</code></td><td>Boolean</td><td>If true, this connector is likely unstable.</td></tr><tr><td><code>color</code></td><td>String or null</td><td>Branding color of the bank or provider.</td></tr><tr><td><code>slug</code></td><td>String or null</td><td>A short letter code to identify the connector. Slugs are <em>not</em> unique.</td></tr><tr><td><del><code>sync_frequency</code></del></td><td>Decimal or null</td><td><em>(Deprecated)</em> How many days to wait between syncs.</td></tr><tr><td><code>months_to_fetch</code></td><td>Integer or null</td><td>Number of months of history to fetch when synchronizing a connection.</td></tr><tr><td><code>auth_mechanism</code></td><td><a href="#authmechanism-values"><em>AuthMechanism</em></a> string or null</td><td>Authentication mechanism to use to add a connection.</td></tr><tr><td><code>available_auth_mechanisms</code></td><td>Array of <a href="#authmechanism-values"><em>AuthMechanism</em></a> strings</td><td>The list of available mechanisms to add a connection (internal use only).</td></tr><tr><td><code>transfer_mechanism</code></td><td><a href="#authmechanism-values"><em>AuthMechanism</em></a> or null</td><td>Authentication mechanism to use to validate a transfer.</td></tr><tr><td><code>siret</code></td><td>String</td><td>SIRET code, for providers.</td></tr><tr><td><code>restricted</code></td><td>Boolean</td><td>If true, new connections cannot be added with this connector.</td></tr><tr><td><code>capabilities</code></td><td>Array of strings</td><td>The list of capabilities implemented on the connector. E.g. <code>profile</code> means that the connector is able to return <a href="/pages/2UHVwuTLdZJudG43bbzs">identity information</a>.</td></tr><tr><td><code>account_usages</code></td><td>Array of <a href="/pages/6ZTi4nFvuqvWCMNrWCTt#bankaccountusage-values"><em>BankAccountUsage</em></a> strings</td><td>The list of account usages returned by the sources of the connector.</td></tr><tr><td><code>payment_settings</code></td><td><a href="#paymentsettings-object"><em>PaymentSettings</em></a> object</td><td>An object providing information about payment feature on this connector. Only present if <em>Pay</em> product is enabled on the connector.</td></tr><tr><td><code>products</code></td><td>Array of <a href="#product-values"><em>Product</em></a> strings</td><td>The list of products implemented on the connector. (e.g. <code>pay</code> means that the connector has Pay product).</td></tr></tbody></table>

#### **Available expands**

The following parameters can be used for [response properties expansion](/api-reference/overview/api-design.md#responses-expansion):

<table><thead><tr><th width="144.33333333333331">Property</th><th width="301">Type</th><th>Description</th></tr></thead><tbody><tr><td><code>sources</code></td><td>Array of <a href="#connectorsource-object"><em>ConnectorSource</em></a> objects</td><td>The details of the sources available for the connector.</td></tr><tr><td><code>fields</code></td><td>Array of <a href="#connectorfield-object"><em>ConnectorField</em></a> objects</td><td>The list of initial form fields associated with the connector. Only relevant when building a <mark style="background-color:orange;">custom connection integration</mark>.</td></tr><tr><td><code>payment</code><br><code>_fields</code></td><td>Array of <a href="#connectorpaymentfield-object"><em>ConnectorPaymentField</em></a> objects</td><td>The list of initial form fields to use when validating a payment.<br>Only relevant when <a href="https://docs.powens.com/documentation/integration-guides/pay/advanced/implementing-your-own-payment-validation-webview">implementing your own payment validation webview</a>.</td></tr><tr><td><code>countries</code></td><td>Array of <a href="#connectorcountry-object"><em>ConnectorCountry</em></a> objects</td><td>Countries where users can open or have accounts/subscriptions with the given institution.</td></tr><tr><td><code>urls</code></td><td>Array of strings</td><td>List of connector's URLs from which we get the data.</td></tr></tbody></table>

### ***AuthMechanism*****&#x20;values**

<table><thead><tr><th width="164">Value</th><th>Description</th></tr></thead><tbody><tr><td><code>credentials</code></td><td>Connections will use a set of fields to save user credentials.</td></tr><tr><td><code>webauth</code></td><td>Connections will use a web-based flow to obtain access.</td></tr></tbody></table>

{% hint style="info" %}
Forward compatibility requirement: additional mechanisms may be added in the future. When implementing mechanism handling, always safely handle unsupported values.
{% endhint %}

### ***ConnectorField*****&#x20;object**

<table><thead><tr><th width="220.33333333333331">Name</th><th width="189">Type</th><th>Description</th></tr></thead><tbody><tr><td><code>name</code></td><td>String</td><td>The technical name of the field, used as a key when sending the values for the field.</td></tr><tr><td><code>connector_sources</code></td><td>Array of strings</td><td>The list of <a href="#connectorsource-object">connector source names</a> for which the field is relevant. Fields should be presented sequentially according to the source being added. The value can differ with the <code>auth_mechanism</code> preferentially used.</td></tr><tr><td><code>auth_mechanisms</code></td><td>Array of <a href="#authmechanism-values"><em>AuthMechanism</em></a> strings</td><td>The list of mechanisms for which the field is relevant. Fields should be presented sequentially according to the source being added.</td></tr><tr><td><code>type</code></td><td><a href="#connectorfieldtype-values"><em>ConnectorFieldType</em></a> string</td><td>Type of the field, to be used to present an appropriate UI form field to the end-user. Implementations should ignore unsupported types and fallback to a text field.</td></tr><tr><td><code>label</code></td><td>String</td><td>A short display label for the field.</td></tr><tr><td><code>required</code></td><td>Boolean</td><td>If true, the parameter is required, with a non-empty value, when creating a connection.</td></tr><tr><td><code>regex</code></td><td>String or null</td><td>An optional regular expression (PCRE-compatible) that the field value must validate.</td></tr><tr><td><code>values</code></td><td>Array of objects</td><td>For <code>list</code> fields, a closed list of fixed values to chose from. Entries are composed of <code>label</code> (string, display value of the field) and <code>value</code> (string, the actual value to send for the field).</td></tr></tbody></table>

### ***ConnectorPaymentField*****&#x20;object**

<table><thead><tr><th width="220.33333333333331">Name</th><th width="189">Type</th><th>Description</th></tr></thead><tbody><tr><td><code>name</code></td><td>String</td><td>The technical name of the field, used as a key when sending the values for the field.</td></tr><tr><td><code>auth_mechanisms</code></td><td>Array of strings</td><td>The list of validation mechanisms for which the field is relevant. Fields should be presented sequentially according to the source being added.</td></tr><tr><td><code>type</code></td><td><a href="#connectorfieldtype-values"><em>ConnectorFieldType</em></a> string</td><td>Type of the field, to be used to present an appropriate UI form field to the end-user. Implementations should ignore unsupported types and fallback to a text field.</td></tr><tr><td><code>label</code></td><td>String</td><td>A short display label for the field.</td></tr><tr><td><code>required</code></td><td>Boolean</td><td>If true, the parameter is required, with a non-empty value, when creating a connection.</td></tr><tr><td><code>regex</code></td><td>String or null</td><td>An optional regular expression (PCRE-compatible) that the field value must validate.</td></tr><tr><td><code>values</code></td><td>Array of objects</td><td>For <code>list</code> fields, a closed list of fixed values to chose from. Entries are composed of <code>label</code> (string, display value of the field) and <code>value</code> (string, the actual value to send for the field).</td></tr></tbody></table>

### ***ConnectorFieldType*****&#x20;values**

<table><thead><tr><th width="133">Value</th><th>Description</th></tr></thead><tbody><tr><td><code>text</code></td><td>A simple text field.</td></tr><tr><td><code>password</code></td><td>A simple text field for a sensitive value. Implementations should provide secure typing for such fields.</td></tr><tr><td><code>date</code></td><td>A date field. Input should be proposed in a user-friendly manner with a picker or a localized text input, but the value must be submitted as an ISO 8601 date string (yyyy-mm-dd).</td></tr><tr><td><code>list</code></td><td>A field whose value must be chosen in a closed list of <code>values</code>. The field can be presented with a dropdown or a similar control.</td></tr></tbody></table>

### ***ConnectorCountry*****&#x20;object**

<table><thead><tr><th width="160.33333333333331">Name</th><th width="167">Type</th><th>Description</th></tr></thead><tbody><tr><td><code>id</code></td><td>String</td><td>The country ISO 3166‑1 alpha‑2 code.</td></tr><tr><td><code>name</code></td><td>String</td><td>The country name.</td></tr></tbody></table>

### ***PaymentSettings*****&#x20;object**

<table><thead><tr><th width="260.3333333333333">Name</th><th>Type</th><th>Description</th></tr></thead><tbody><tr><td><code>available_validate_mechanisms</code></td><td>Array of strings</td><td>The list of payment validation mechanisms supported by this connector. As of Sept. 2023, the only supported mechanism is <code>webauth</code>.</td></tr><tr><td><code>beneficiary_types</code></td><td>Array of <a href="/pages/ufnJNDcj3aJ7A5Ivp70w#paymentaccountschemename-values"><em>PaymentAccountSchemeName</em></a></td><td>The list of supported payment beneficiary types for this connector.</td></tr><tr><td><code>execution_date_types</code></td><td>Array of <a href="/pages/ufnJNDcj3aJ7A5Ivp70w#executiondate-values"><em>ExecutionDate</em></a></td><td>The list of supported payment types.</td></tr><tr><td><code>execution_frequencies</code></td><td>Array of <a href="/pages/ufnJNDcj3aJ7A5Ivp70w#executionfrequency-values"><em>ExecutionFrequency</em></a></td><td>The list of supported periodic payment frequencies.</td></tr><tr><td><code>maximum_number_of_instructions</code></td><td>Integer</td><td>The maximum number of individual instructions for one payment. If <code>1</code>, the connector does not support Bulk payments.</td></tr><tr><td><code>providing_payer_account</code></td><td><a href="#providingpayeraccount-values"><em>ProvidingPayerAccount</em></a></td><td>Indicates if the connector needs the payer account identification in order to initiate a payment with their bank.</td></tr><tr><td><code>partial_status_tracking</code></td><td>Array of <a href="/pages/ufnJNDcj3aJ7A5Ivp70w#executiondate-values"><em>ExecutionDate</em></a></td><td>Indicates for which payment date types a payment can reach the final state <code>accepted</code> for this connector, meaning the bank does not provide us with the full tracking of the payment status. See <a href="/pages/ufnJNDcj3aJ7A5Ivp70w#paymentstate-values"><mark style="color:blue;">PaymentState values</mark></a> for more information. An empty list indicates that payments will never get the state <code>accepted</code> on this connector.</td></tr><tr><td><code>is_app_to_app_used</code></td><td><a href="#paymentapptoappused-object"><em>PaymentAppToAppUsed</em></a></td><td>Whether redirects can be caught by native applications on mobile platforms.</td></tr><tr><td><code>bank_provides_payer_account</code></td><td>Boolean or null</td><td>Whether the bank provides the payer account or not. <code>null</code> means this information is not yet available.</td></tr><tr><td><code>bank_provides_payer_label</code></td><td>Boolean or null</td><td>Whether the bank provides the payer account label or not. <code>null</code> means this information is not yet available.</td></tr><tr><td><code>transfer_date_types_where_</code><br><code>trusted_beneficiary_required</code></td><td>Array of <a href="/pages/ufnJNDcj3aJ7A5Ivp70w#executiondate-values"><em>ExecutionDate</em></a></td><td>List of execution date types for which the beneficiary must be trusted beforehand by the payer.</td></tr><tr><td><code>cancellation</code><br><code>_available</code></td><td>Boolean</td><td>Whether <a href="https://docs.powens.com/documentation/integration-guides/pay/cancelling-a-payment">cancellation</a> is available for this connector.</td></tr><tr><td><code>minimum_amount</code></td><td>PaymentAmount</td><td>The minimum amount for a payment on this connector. The amount can differ between payment types.</td></tr><tr><td><code>maximum_amount</code></td><td>PaymentAmount</td><td>The maximum amount for a payment on this connector. The amount can differ between payment types. Note that this amount is not necessarily a hard limit and a PSU payment account could have a specific transfer limit (whether higher or lower).</td></tr><tr><td><code>minimum_date_delta_days</code></td><td>Decimal</td><td>The minimum number of days in the future for a deferred or periodic payment.</td></tr><tr><td><code>maximum_date_delta_days</code></td><td>Decimal or null</td><td>The maximum number of days in the future for a deferred or periodic payment.</td></tr></tbody></table>

An example `payment_settings` object is the following:

<pre class="language-json"><code class="lang-json">{
  "available_validate_mechanisms": ["webauth"],
  "beneficiary_types": ["iban"],
  "execution_date_types": ["first_open_day", "deferred", "periodic"],
  "execution_frequencies": ["monthly", ...],
  "maximum_number_of_instructions": 10,
  "partial_status_tracking": ["first_open_day"],
  "is_app_to_app_used": {
    "android": false,
    "ios": null
  },
  "bank_provides_payer_account": true,
  "bank_provides_payer_label": null,
  "transfer_date_types_where_trusted_beneficiary_required": ["periodic"],
<strong>  "cancellation_available": true,
</strong><strong>  "minimum_amount": {
</strong><strong>    "first_open_day": 0.,
</strong><strong>    "deferred": 0.,
</strong><strong>    "instant": 0.
</strong><strong>  },
</strong><strong>  "maximum_amount": {
</strong><strong>    "first_open_day": 4000.,
</strong><strong>    "deferred": 4000.,
</strong><strong>    "instant": 1000.
</strong><strong>  },
</strong><strong>  "minimum_date_delta_days": 1,
</strong><strong>  "maximum_date_delta_days": 30,
</strong><strong>}
</strong></code></pre>

### ***ProvidingPayerAccount*****&#x20;values**

<table><thead><tr><th width="176">Value</th><th>Description</th></tr></thead><tbody><tr><td><code>not_used</code></td><td>The payer account is not necessary and must not be given.</td></tr><tr><td><code>optional</code></td><td>The payer account is optional. Providing the account may have an impact on the bank's webview (e.g. the payment account may be preselected for the user, or the user may not have the possibility to change it for another one).</td></tr><tr><td><code>mandatory</code></td><td>The payer account must be provided. The bank does not allow a payment initiation without this information.</td></tr></tbody></table>

### ***PaymentAppToAppUsed*****&#x20;object**

| Name      | Type            | Description                                                                     |
| --------- | --------------- | ------------------------------------------------------------------------------- |
| `android` | Boolean or Null | Whether redirections can be caught by a native application or not on Android.   |
| `ios`     | Boolean or Null | Whether redirections can be caught by a native application or not on Apple iOS. |

For all platforms, `null` means that the information is not available yet. Note that `true` does not mean the redirections are necessarily caught by a native application, since the end user may not have installed the appropriate application for this to happen.

An example `PaymentAppToAppUsed` object is the following:

```json
{
  "android": false,
  "ios": null
}
```

### ***PaymentAmount*****&#x20;object**

| Value            | Type    | Required | Description                                   |
| ---------------- | ------- | -------- | --------------------------------------------- |
| first\_open\_day | Decimal | No       | The amount limit for first open day payments. |
| instant          | Decimal | No       | The amount limit for instant payments.        |
| deferred         | Decimal | No       | The amount limit for deferred payments.       |
| periodic         | Decimal | No       | The amount limit for periodic payments.       |

### ***Product*****&#x20;values**

<table><thead><tr><th width="180">Value</th><th>Description</th></tr></thead><tbody><tr><td><code>bank</code></td><td>Bank product.</td></tr><tr><td><code>wealth</code></td><td>Wealth product.</td></tr><tr><td><code>bill</code></td><td>Bill product.</td></tr><tr><td><code>pay</code></td><td>Pay product.</td></tr></tbody></table>

### *ConnectorUpdateRequest* object <a href="#update-a-connector" id="update-a-connector"></a>

<table><thead><tr><th width="217">Name</th><th width="110">Type</th><th width="102">Required</th><th>Description</th></tr></thead><tbody><tr><td><code>hidden</code></td><td>Boolean</td><td>No</td><td>Whether the connector is hidden from users.</td></tr><tr><td><del><code>sync_periodicity</code></del></td><td>Decimal</td><td>No</td><td><em>(Deprecated)</em> Number of days between two automatic synchronizations. Overload global <code>sync_periodicity</code> parameter.</td></tr></tbody></table>

### ***ConnectorSourcesList*****&#x20;object**

<table><thead><tr><th width="151.33333333333331">Property</th><th>Type</th><th>Description</th></tr></thead><tbody><tr><td><code>sources</code></td><td>Array of <a href="#connectorsource-object"><em>ConnectorSource</em></a> objects</td><td>List of connector sources.</td></tr></tbody></table>

### ***ConnectorSource*****&#x20;object**

<table><thead><tr><th>Property</th><th width="160.33333333333331">Type</th><th>Description</th></tr></thead><tbody><tr><td><code>id</code></td><td>Integer</td><td>ID of the connector source.</td></tr><tr><td><code>id_connector</code></td><td>Integer</td><td>ID of the related connector.</td></tr><tr><td><code>name</code></td><td>String</td><td>Name of the connector source.</td></tr><tr><td><code>auth_mechanism</code></td><td><a href="#authmechanism-values"><em>AuthMechanism</em></a> string or null</td><td>Authentication mechanism to use to add a connection source.</td></tr><tr><td><code>available_auth_mechanisms</code></td><td>Array of <a href="#authmechanism-values"><em>AuthMechanism</em></a> strings</td><td>The list of available mechanisms to add a connection source.</td></tr><tr><td><code>disabled</code></td><td>DateTime or null</td><td>If set, this source is ignored on synchronizing the connection.</td></tr><tr><td><code>priority</code></td><td>Integer</td><td>The source priority order for the synchronization. Sources must be added following priority order.</td></tr><tr><td><code>account_usages</code></td><td>Array of <a href="/pages/6ZTi4nFvuqvWCMNrWCTt#bankaccountusage-values"><em>BankAccountUsage</em></a> strings</td><td>The list of account usages returned by the source.</td></tr></tbody></table>

### *ConnectorSourceUpdateRequest* object <a href="#update-a-connector-source" id="update-a-connector-source"></a>

<table><thead><tr><th width="192">Property</th><th width="160">Type</th><th width="102">Required</th><th>Description</th></tr></thead><tbody><tr><td><code>auth_mechanism</code></td><td><a href="#authmechanism-values"><em>AuthMechanism</em></a> string</td><td>No</td><td>The authentication mechanism to use for this connector source.</td></tr><tr><td><code>disabled</code></td><td>DateTime or null</td><td>No</td><td>If set, this source is ignored on synchronizing the connection.</td></tr></tbody></table>


---

# Agent Instructions: Querying This Documentation

If you need additional information that is not directly available in this page, you can query the documentation dynamically by asking a question.

Perform an HTTP GET request on the current page URL with the `ask` query parameter:

```
GET https://docs.powens.com/api-reference/user-connections/connectors.md?ask=<question>
```

The question should be specific, self-contained, and written in natural language.
The response will contain a direct answer to the question and relevant excerpts and sources from the documentation.

Use this mechanism when the answer is not explicitly present in the current page, you need clarification or additional context, or you want to retrieve related documentation sections.
