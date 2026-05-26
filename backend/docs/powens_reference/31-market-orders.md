# Market orders

## API endpoints <a href="#list-investments" id="list-investments"></a>

{% hint style="success" %}
Authentication: endpoints listed in this page *require* [header authentication](/api-reference/overview/authentication.md) with a *user token*.
{% endhint %}

## List market orders

<mark style="color:blue;">`GET`</mark> `https://{domain}.biapi.pro/2.0/users/{userId}/marketorders`

List market orders related to a user.

#### Path Parameters

| Name                                     | Type            | Description             |
| ---------------------------------------- | --------------- | ----------------------- |
| userId<mark style="color:red;">\*</mark> | Integer or "me" | ID of the related user. |

{% tabs %}
{% tab title="200: OK List of market orders" %}
Response body: [#marketorderslist-object](#marketorderslist-object "mention")
{% endtab %}
{% endtabs %}

{% code title="Filtering route aliases:" %}

```
/users/{userId}/accounts/{accountId}/marketorders
/users/{userId}/connections/{connectionId}/marketorders
```

{% endcode %}

## Get a market order

<mark style="color:blue;">`GET`</mark> `https://{domain}.biapi.pro/2.0/marketorders/{marketOrderId}`

Get a single market order by ID.

#### Path Parameters

| Name                                            | Type    | Description             |
| ----------------------------------------------- | ------- | ----------------------- |
| marketOrderId<mark style="color:red;">\*</mark> | Integer | ID of the market order. |

{% tabs %}
{% tab title="200: OK Market order details" %}
Response body: [#marketorder-object](#marketorder-object "mention")
{% endtab %}
{% endtabs %}

## Data model

### *MarketOrdersList* object

<table><thead><tr><th width="190.33333333333331">Property</th><th>Type</th><th>Description</th></tr></thead><tbody><tr><td><code>marketorders</code></td><td>Array of <a href="#marketorder-object"><em>MarketOrder</em></a> objects</td><td>List of market orders.</td></tr></tbody></table>

### *MarketOrder* object

<table><thead><tr><th width="217.33333333333331">Property</th><th width="219">Type</th><th>Description</th></tr></thead><tbody><tr><td><code>id</code></td><td>Integer</td><td>ID of the market order.</td></tr><tr><td><code>id_account</code></td><td>Integer</td><td>ID of the related account.</td></tr><tr><td><code>number</code></td><td>String</td><td>Number of the market order.</td></tr><tr><td><code>label</code></td><td>String</td><td>Display name of the market order.</td></tr><tr><td><code>code</code></td><td>String or null</td><td>Technical code (ISIN) of the market order.</td></tr><tr><td><code>stock_symbol</code></td><td>String or null</td><td>Stock ticker symbol of the investment in the associated stock market.</td></tr><tr><td><code>order_direction</code></td><td><a href="#marketorderdirection-object"><em>MarkerOrderDirection</em></a> object</td><td>Market order direction.</td></tr><tr><td><code>order_type</code></td><td><a href="#marketordertype-object"><em>MarkerOrderType</em></a> object</td><td>Market order type.</td></tr><tr><td><code>stock_market</code></td><td>String or null</td><td>Stock market on which the order was executed (examples: "NASDAQ", "Xetra"…).</td></tr><tr><td><code>state</code></td><td>String</td><td>Current state of the market order (examples: "Executed", "Pending"…).</td></tr><tr><td><code>payment_method</code></td><td>String</td><td>Payment method ("CASH", "DEFERRED", "UNKNOWN").</td></tr><tr><td><code>date</code></td><td>DateTime or null</td><td>Creation date of the market order.</td></tr><tr><td><code>execution_date</code></td><td>DateTime or null</td><td>Execution date of the market order.</td></tr><tr><td><code>validity_date</code></td><td>DateTime or null</td><td>Validity date of the market order.</td></tr><tr><td><code>quantity</code></td><td>Decimal or null</td><td>Quantity of stocks purchased or sold.</td></tr><tr><td><code>amount</code></td><td>Decimal or null</td><td>Total amount that was purchased or sold.</td></tr><tr><td><code>ordervalue</code></td><td>Decimal or null</td><td>Limit or Trigger value (only applicable for "Limit" or "Trigger" types).</td></tr><tr><td><code>unitprice</code></td><td>Decimal or null</td><td>Value of one stock when the order was executed.</td></tr><tr><td><code>unitvalue</code></td><td>Decimal or null</td><td>Current value of the related stock.</td></tr><tr><td><code>deleted</code></td><td>DateTime or null</td><td>Deletion date for market orders that no longer exist (<code>null</code> if still present).</td></tr><tr><td><code>last_update</code></td><td>DateTime</td><td>Date of the last synchronization of the investment.</td></tr></tbody></table>

### *MarketOrderDirection* object

<table><thead><tr><th width="172.33333333333331">Property</th><th width="117">Type</th><th>Description</th></tr></thead><tbody><tr><td><code>id</code></td><td>Integer</td><td>ID of the the market order direction.</td></tr><tr><td><code>name</code></td><td>String</td><td>Market order direction: <code>BUY</code> or <code>SALE</code>.</td></tr></tbody></table>

### *MarketOrderType* object

<table><thead><tr><th width="181.33333333333331">Property</th><th width="115">Type</th><th>Description</th></tr></thead><tbody><tr><td><code>id</code></td><td>Integer</td><td>ID of the the market order type.</td></tr><tr><td><code>name</code></td><td>String</td><td>Market order type: <code>MARKET</code>, <code>LIMIT</code>, <code>TRIGGER or UNKNOWN</code>.</td></tr></tbody></table>


---

# Agent Instructions: Querying This Documentation

If you need additional information that is not directly available in this page, you can query the documentation dynamically by asking a question.

Perform an HTTP GET request on the current page URL with the `ask` query parameter:

```
GET https://docs.powens.com/api-reference/products/wealth-aggregation/market-orders.md?ask=<question>
```

The question should be specific, self-contained, and written in natural language.
The response will contain a direct answer to the question and relevant excerpts and sources from the documentation.

Use this mechanism when the answer is not explicitly present in the current page, you need clarification or additional context, or you want to retrieve related documentation sections.
