# Balances

## API endpoints

{% hint style="success" %}
Authentication: endpoints listed in this page *require* [header authentication](/api-reference/overview/authentication.md) with a *user token*.
{% endhint %}

## Get balances of an account

{% hint style="info" %}
The balance information provided by banks may not always reflect the real-time balance displayed in the bank’s online portal or mobile application. In some cases, it may correspond to the previous day’s balance (e.g., as of 10:00 PM or midnight), a near real-time balance, or another reference point determined by the bank. As a result, this balance must not be relied upon for accounting reconciliation purposes.
{% endhint %}

<mark style="color:blue;">`GET`</mark> `https://{domain}.biapi.pro/2.0/users/{userId}/accounts/{accountId}/balances`

Get balances (income, outcome and balance) of a single account, for a given period.

#### Path Parameters

| Name                                        | Type   | Description            |
| ------------------------------------------- | ------ | ---------------------- |
| accountId<mark style="color:red;">\*</mark> | String | ID of the bank account |

#### Query Parameters

| Name      | Type | Description                                                              |
| --------- | ---- | ------------------------------------------------------------------------ |
| min\_date | Date | Minimum date (inclusive). The default is the start of the current month. |
| max\_date | Date | Maximum date (inclusive). The default is the end of the current month.   |

{% tabs %}
{% tab title="200: OK List of balances" %}
Response body: [#balancegroupslist-object](#balancegroupslist-object "mention")
{% endtab %}
{% endtabs %}

#### Path Parameters

| Name                                        | Type   | Description  |
| ------------------------------------------- | ------ | ------------ |
| accountId<mark style="color:red;">\*</mark> | String | KZiKbVB6V4BF |

#### Query Parameters

| Name      | Type | Description  |
| --------- | ---- | ------------ |
| min\_date | Date | fljlFaZDqiN4 |
| max\_date | Date | wlFJvI4sxPuY |

## Data model

### ***BalanceGroupsList*****&#x20;object**

<table><thead><tr><th width="220.33333333333331">Property</th><th width="156">Type</th><th>Description</th></tr></thead><tbody><tr><td><code>balances</code></td><td>Array of <a href="#balancegroup-object"><em>BalanceGroup</em></a> objects</td><td>List of balance group items matching the requested period and bounds.</td></tr><tr><td><code>first_date</code></td><td>Date</td><td>Minimum available date for results.</td></tr><tr><td><code>last_date</code></td><td>Date</td><td>Maximum available date for results.</td></tr><tr><td><code>result_min_date</code></td><td>Date</td><td>Minimum date of results in the current response.</td></tr><tr><td><code>result_max_date</code></td><td>Date</td><td>Maximum date of results in the current response.</td></tr></tbody></table>

### ***BalanceGroup*****&#x20;object**

<table><thead><tr><th width="166.33333333333331">Property</th><th width="232">Type</th><th>Description</th></tr></thead><tbody><tr><td><code>min_date</code></td><td>Date</td><td>Start date of the group item.</td></tr><tr><td><code>max_date</code></td><td>Date</td><td>End date of the group item.</td></tr><tr><td><code>currencies</code></td><td>Array of <a href="#balancecurrencygroup-object"><em>BalanceCurrencyGroup</em></a> objects</td><td>List of balance details grouped by currency.</td></tr><tr><td><code>n_overdraft</code></td><td>Integer</td><td>Number of days with a negative balance</td></tr><tr><td><code>balance</code></td><td>Decimal</td><td>Final account balance at the end of the period</td></tr><tr><td><code>expenses</code>, <code>incomes</code>, <code>remains</code></td><td>Decimal</td><td>Total expenses, incomes, and net flow</td></tr><tr><td><code>currencies</code></td><td><code>BalanceCurrencyGroup[]</code></td><td>Breakdown per currency</td></tr><tr><td><code>daily_balances</code></td><td><code>DailyBalance[]</code></td><td>Daily values for balance, income, expense, and net result</td></tr></tbody></table>

### ***BalanceCurrencyGroup*****&#x20;object**

<table><thead><tr><th width="144">Property</th><th width="137.33333333333331">Type</th><th>Description</th></tr></thead><tbody><tr><td><code>id</code></td><td>String</td><td>ISO code of the currency.</td></tr><tr><td><code>symbol</code></td><td>String</td><td>Display symbol of the currency.</td></tr><tr><td><code>balance</code></td><td>Decimal</td><td>Balance of the account at the end of the period group.</td></tr><tr><td><code>expenses</code></td><td>Decimal</td><td>Total of expenses over the period group.</td></tr><tr><td><code>incomes</code></td><td>Decimal</td><td>Total of incomes over the period group.</td></tr><tr><td><code>remains</code></td><td>Decimal</td><td>Difference between expenses and incomes over the period group.</td></tr></tbody></table>

### ***DailyBalance***

{% hint style="info" %}
The day-by-day balance becomes available as soon as date parameters are specified in the GET query.
{% endhint %}

<table><thead><tr><th width="144">Property</th><th width="137.33333333333331">Type</th><th>Description</th></tr></thead><tbody><tr><td>date</td><td>Date</td><td>The specific day</td></tr><tr><td>balance</td><td>Decimal</td><td>Balance of the account at the end of the day.</td></tr><tr><td>expenses</td><td>Decimal</td><td>Total of expenses over the day.</td></tr><tr><td>incomes</td><td>Decimal</td><td>Total of incomes over the day.</td></tr><tr><td>remains</td><td>Decimal</td><td>Difference between expenses and incomes over the day</td></tr></tbody></table>


---

# Agent Instructions: Querying This Documentation

If you need additional information that is not directly available in this page, you can query the documentation dynamically by asking a question.

Perform an HTTP GET request on the current page URL with the `ask` query parameter:

```
GET https://docs.powens.com/api-reference/products/data-aggregation/balances.md?ask=<question>
```

The question should be specific, self-contained, and written in natural language.
The response will contain a direct answer to the question and relevant excerpts and sources from the documentation.

Use this mechanism when the answer is not explicitly present in the current page, you need clarification or additional context, or you want to retrieve related documentation sections.
