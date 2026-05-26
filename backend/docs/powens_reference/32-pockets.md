# Pockets

## API endpoints <a href="#list-investments" id="list-investments"></a>

{% hint style="success" %}
Authentication: endpoints listed in this page *require* [header authentication](/api-reference/overview/authentication.md) with a *user token*.
{% endhint %}

## List pockets

<mark style="color:blue;">`GET`</mark> `https://{domain}.biapi.pro/2.0/users/{userId}/pockets`

List pockets related to a user.

#### Path Parameters

| Name                                     | Type            | Description             |
| ---------------------------------------- | --------------- | ----------------------- |
| userId<mark style="color:red;">\*</mark> | Integer or "me" | ID of the related user. |

{% tabs %}
{% tab title="200: OK List of pockets" %}
Response body: [#pocketslist-object](#pocketslist-object "mention")
{% endtab %}
{% endtabs %}

{% code title="Filtering route aliases:" %}

```
/users/{userId}/investments/{investmentId}/pockets
/users/{userId}/accounts/{accountId}/pockets
/users/{userId}/connections/{connectionId}/pockets
```

{% endcode %}

## Get a pocket

<mark style="color:blue;">`GET`</mark> `https://{domain}.biapi.pro/2.0/pockets/{pocketId}`

Get a single pocket by ID.

#### Path Parameters

| Name                                       | Type    | Description       |
| ------------------------------------------ | ------- | ----------------- |
| pocketId<mark style="color:red;">\*</mark> | Integer | ID of the pocket. |

{% tabs %}
{% tab title="200: OK Pocket details" %}
Response body: [#pocket-object](#pocket-object "mention")
{% endtab %}
{% endtabs %}

## Data model

### *PocketsList* object

<table><thead><tr><th width="190.33333333333331">Property</th><th>Type</th><th>Description</th></tr></thead><tbody><tr><td><code>pockets</code></td><td>Array of <a href="#pocket-object"><em>Pocket</em></a> objects</td><td>List of pockets.</td></tr></tbody></table>

### *Pocket* object

<table><thead><tr><th width="221.33333333333331">Property</th><th width="183">Type</th><th>Description</th></tr></thead><tbody><tr><td><code>id</code></td><td>Integer</td><td>ID of the pocket.</td></tr><tr><td><code>id_investment</code></td><td>Integer</td><td>ID of the related investment.</td></tr><tr><td><code>id_account</code></td><td>Integer</td><td>ID of the related account.</td></tr><tr><td><code>label</code></td><td>String</td><td>Display name of the pocket.</td></tr><tr><td><code>quantity</code></td><td>Decimal</td><td>Quantity of stocks in the pocket.</td></tr><tr><td><code>value</code></td><td>Decimal</td><td>Total current value of the pocket.</td></tr><tr><td><code>condition</code></td><td><a href="#pocketcondition-object"><em>PocketCondition</em></a> string</td><td>Condition for the availability of the pocket.</td></tr><tr><td><code>availability_date</code></td><td>Date or null</td><td>Date of availability, if applicable.</td></tr><tr><td><code>deleted</code></td><td>Date or null</td><td>Deletion date for pockets that no longer exist (<code>null</code> if still present).</td></tr><tr><td><code>last_update</code></td><td>DateTime</td><td>Date of the last synchronization of the pocket.</td></tr></tbody></table>

### *PocketCondition* values

<table><thead><tr><th width="172">Value</th><th>Description</th></tr></thead><tbody><tr><td><code>unknown</code></td><td>There is no available information on the condition.</td></tr><tr><td><code>date</code></td><td>The pocket will become available at a specific date.</td></tr><tr><td><code>acquired</code></td><td>The pocket is acquired (the underlying shares are acquired but cannot be transferred).</td></tr><tr><td><code>available</code></td><td>The pocket is available and the underlying shares are transferable (the condition was fulfilled or the availability date is in the past).</td></tr><tr><td><code>retirement</code></td><td>The pocket will be available when the employee retires (precise date is not always indicated).</td></tr></tbody></table>

{% hint style="info" %}
Forward compatibility requirement: additional values may be added in the future. When implementing value matching, always fallback to a generic case for unknown values.
{% endhint %}


---

# Agent Instructions: Querying This Documentation

If you need additional information that is not directly available in this page, you can query the documentation dynamically by asking a question.

Perform an HTTP GET request on the current page URL with the `ask` query parameter:

```
GET https://docs.powens.com/api-reference/products/wealth-aggregation/pockets.md?ask=<question>
```

The question should be specific, self-contained, and written in natural language.
The response will contain a direct answer to the question and relevant excerpts and sources from the documentation.

Use this mechanism when the answer is not explicitly present in the current page, you need clarification or additional context, or you want to retrieve related documentation sections.
