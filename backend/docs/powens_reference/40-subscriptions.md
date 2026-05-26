# Subscriptions

## API endpoints

{% hint style="success" %}
Authentication: endpoints listed in this page *require* [header authentication](/api-reference/overview/authentication.md) with a *user token*.
{% endhint %}

## List subscriptions

<mark style="color:blue;">`GET`</mark> `https://{domain}.biapi.pro/2.0/users/{userId}/subscriptions`

#### Path Parameters

| Name                                     | Type            | Description             |
| ---------------------------------------- | --------------- | ----------------------- |
| userId<mark style="color:red;">\*</mark> | Integer or "me" | ID of the related user. |

#### Query Parameters

| Name | Type       | Description                            |
| ---- | ---------- | -------------------------------------- |
| all  | Value-less | Flag to access disabled subscriptions. |

{% tabs %}
{% tab title="200: OK List of subscriptions" %}
Response body: [#subscriptionslist-object](#subscriptionslist-object "mention")
{% endtab %}
{% endtabs %}

{% code title="Filtering route alias:" %}

```
/users/{userId}/connections/{connectionId}/subscriptions
```

{% endcode %}

## Get a subscription

<mark style="color:blue;">`GET`</mark> `https://{domain}.biapi.pro/2.0/users/{userId}/subscriptions/{subscriptionId}`

Get a single subscription by ID.

#### Path Parameters

| Name                                             | Type            | Description             |
| ------------------------------------------------ | --------------- | ----------------------- |
| subscriptionId<mark style="color:red;">\*</mark> | Integer         | ID of the subscription. |
| userId<mark style="color:red;">\*</mark>         | Integer or "me" | ID of the related user. |

{% tabs %}
{% tab title="200: OK Subscription details" %}
Response body: [#subscription-object](#subscription-object "mention")
{% endtab %}
{% endtabs %}

Subscription resources partially support an update operation to handle activation/deactivation:

## Update a subscription

<mark style="color:green;">`POST`</mark> `https://{domain}.biapi.pro/2.0/users/{userId}/subscriptions/{subscriptionId}`

Update a single subscription by ID.

Request body: [#subscriptionupdaterequest-object](#subscriptionupdaterequest-object "mention")

#### Path Parameters

| Name                                             | Type    | Description             |
| ------------------------------------------------ | ------- | ----------------------- |
| subscriptionId<mark style="color:red;">\*</mark> | Integer | ID of the subscription. |
| userId<mark style="color:red;">\*</mark>         | Integer | ID of the related user. |

#### Query Parameters

| Name | Type       | Description                                      |
| ---- | ---------- | ------------------------------------------------ |
| all  | Value-less | Add this flag to access a disabled subscription. |

{% tabs %}
{% tab title="200: OK Subscription updated" %}
Response body: [#subscription-object](#subscription-object "mention")
{% endtab %}
{% endtabs %}

## Life cycle <a href="#disabled-accounts" id="disabled-accounts"></a>

Subscriptions can be in a disabled or enabled state.

{% hint style="warning" %}
For legal compliance, subscriptions are disabled by default. Also, disabling subscription will result in the deletion of subscription child resources (documents).
{% endhint %}

#### Querying

Disabled subscriptions will only appear when passing the `all` parameter:

```
GET /users/{userId}/subscriptions/{id}?all
GET /users/{userId}/connections/{connectionId}/subscriptions/{id}?all
```

#### Enabling

To enable one such subscription, it is necessary to perform a `POST` request on that subscription, with the `all` parameter and `{ "disabled": false }`.

Please note that this action represents the PSU's consent.

## Webhooks <a href="#subscription-webhooks" id="subscription-webhooks"></a>

### Subscription synced <a href="#subscription-synced" id="subscription-synced"></a>

A `SUBSCRIPTION_SYNCED` webhook is emitted during a sync after a subscription was processed, including new documents.

Webhook request: [*Subscription*](#subscription-object) object with the following additional properties:

<table><thead><tr><th width="173.33333333333331">Property</th><th width="249">Type</th><th>Description</th></tr></thead><tbody><tr><td><code>documents</code></td><td>Array of <em>Document</em> objects</td><td>The new documents that were found.</td></tr></tbody></table>

### Subscription found <a href="#subscription-found" id="subscription-found"></a>

A `SUBSCRIPTION_FOUND` webhook is emitted after a **new** subscription was discovered.

Webhook request:

<table><thead><tr><th width="212">Property</th><th width="180.33333333333331">Type</th><th>Description</th></tr></thead><tbody><tr><td><code>id</code></td><td>Integer</td><td>ID of the bank account.</td></tr><tr><td><code>id_user</code></td><td>Integer</td><td>ID of the related user.</td></tr><tr><td><code>id_connection</code></td><td>Integer</td><td>ID of the related connection.</td></tr></tbody></table>

## Data model

### ***SubscriptionsList*****&#x20;object**

<table><thead><tr><th width="190.33333333333331">Property</th><th>Type</th><th>Description</th></tr></thead><tbody><tr><td><code>subscriptions</code></td><td>Array of <a href="#subscription-object"><em>Subscription</em></a> objects</td><td>List of subscriptions.</td></tr></tbody></table>

### ***Subscription*****&#x20;object**

<table><thead><tr><th width="197">Property</th><th width="173.33333333333331">Type</th><th>Description</th></tr></thead><tbody><tr><td><code>id</code></td><td>Integer</td><td>ID of the subscription.</td></tr><tr><td><code>id_connection</code></td><td>Integer or null</td><td>ID of the related connection.</td></tr><tr><td><code>id_user</code></td><td>Integer or null</td><td>ID of the related user.</td></tr><tr><td><code>id_source</code></td><td>Integer or null</td><td>ID of the related connection source.</td></tr><tr><td><code>number</code></td><td>String or null</td><td>Subscription number.</td></tr><tr><td><code>label</code></td><td>String</td><td>Label of the subscription.</td></tr><tr><td><code>subscriber</code></td><td>String or null</td><td>Name of the subscriber.</td></tr><tr><td><code>validity</code></td><td>Date or null</td><td>The subscription is valid until this date, if any.</td></tr><tr><td><code>renewdate</code></td><td>Date or null</td><td>Next renew date, is any.</td></tr><tr><td><code>last_update</code></td><td>DateTime or null</td><td>Last successful update of the subscription.</td></tr><tr><td><code>deleted</code></td><td>DateTime or null</td><td>If set, this subscription is not found on the website anymore.</td></tr><tr><td><code>disabled</code></td><td>DateTime or null</td><td>If set, this subscription has been disabled by user and will not be synchronized anymore.</td></tr><tr><td><code>error</code></td><td>String or null</td><td>If the last update has failed, the error code.</td></tr></tbody></table>

**Available expands**

The following parameters can be used for [response properties expansion](/api-reference/overview/api-design.md#responses-expansion):

<table><thead><tr><th width="178.33333333333331">Property</th><th width="202">Type</th><th>Description</th></tr></thead><tbody><tr><td><code>connection</code></td><td><a href="/pages/5W80jLGBq7ifvqhRCiXo#connection-object"><em>Connection</em></a> object</td><td>The connection associated with this subscription.</td></tr></tbody></table>

### *SubscriptionUpdateRequest* object

<table><thead><tr><th width="178.33333333333331">Property</th><th width="114">Type</th><th width="104">Required</th><th>Description</th></tr></thead><tbody><tr><td><code>disabled</code></td><td>Boolean</td><td>No</td><td>Whether the subscription must be disabled or enabled.</td></tr></tbody></table>


---

# Agent Instructions: Querying This Documentation

If you need additional information that is not directly available in this page, you can query the documentation dynamically by asking a question.

Perform an HTTP GET request on the current page URL with the `ask` query parameter:

```
GET https://docs.powens.com/api-reference/products/documents-aggregation/subscriptions.md?ask=<question>
```

The question should be specific, self-contained, and written in natural language.
The response will contain a direct answer to the question and relevant excerpts and sources from the documentation.

Use this mechanism when the answer is not explicitly present in the current page, you need clarification or additional context, or you want to retrieve related documentation sections.
