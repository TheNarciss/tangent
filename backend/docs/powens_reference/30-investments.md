# Investments

## API endpoints <a href="#list-investments" id="list-investments"></a>

{% hint style="success" %}
Authentication: endpoints listed in this page *require* [header authentication](/api-reference/overview/authentication.md) with a *user token*.
{% endhint %}

## List investments

<mark style="color:blue;">`GET`</mark> `https://{domain}.biapi.pro/2.0/users/{userId}/investments`

List investments related to a user.

#### Path Parameters

| Name                                     | Type            | Description             |
| ---------------------------------------- | --------------- | ----------------------- |
| userId<mark style="color:red;">\*</mark> | Integer or "me" | ID of the related user. |

#### Query Parameters

| Name  | Type   | Description                                  |
| ----- | ------ | -------------------------------------------- |
| label | String | Filter investments using keywords in labels. |
| code  | String | Filter investments by ISIN code.             |

{% tabs %}
{% tab title="200: OK List of investments" %}
Response body: [#investmentslist-object](#investmentslist-object "mention")
{% endtab %}
{% endtabs %}

{% code title="Filtering route aliases:" %}

```
/users/{userId}/accounts/{accountId}/investments
/users/{userId}/connections/{connectionId}/investments
```

{% endcode %}

## Get an investment

<mark style="color:blue;">`GET`</mark> `https://{domain}.biapi.pro/2.0/investments/{investmentId}`

Get a single investment by ID.

#### Path Parameters

| Name                                           | Type    | Description           |
| ---------------------------------------------- | ------- | --------------------- |
| investmentId<mark style="color:red;">\*</mark> | Integer | ID of the investment. |

{% tabs %}
{% tab title="200: OK Investment details" %}
Response body: [#investment-object](#investment-object "mention")
{% endtab %}
{% endtabs %}

## Get history of an investment

<mark style="color:blue;">`GET`</mark> `https://{domain}.biapi.pro/2.0/investments/{investmentId}/history`

Get history of a single investment by ID.

#### Path Parameters

| Name                                           | Type    | Description           |
| ---------------------------------------------- | ------- | --------------------- |
| investmentId<mark style="color:red;">\*</mark> | Integer | ID of the investment. |

{% tabs %}
{% tab title="200: OK Investment history values" %}
Response body: [#investmenthistoryvalueslist-object](#investmenthistoryvalueslist-object "mention")
{% endtab %}
{% endtabs %}

## Data model

### *InvestmentsList* object

<table><thead><tr><th width="221">Property</th><th width="185.33333333333331">Type</th><th>Description</th></tr></thead><tbody><tr><td><code>valuation</code></td><td>Decimal</td><td>Total valuation of all investments.</td></tr><tr><td><code>diff</code></td><td>Decimal</td><td>Total absolute capital gain or loss.</td></tr><tr><td><code>diff_percent</code></td><td>Decimal</td><td>Total relative capital gain or loss.</td></tr><tr><td><code>prev_diff</code></td><td>Decimal</td><td>Total absolute capital gain or loss since the previous value.</td></tr><tr><td><code>prev_diff_percent</code></td><td>Decimal</td><td>Total relative capital gain or loss since the previous value (in ratio, 1 meaning 100%).</td></tr><tr><td><code>calculated</code></td><td>Array of strings</td><td>List of properties of this response that has been calculated rather than directly obtained from the source.</td></tr><tr><td><code>investments</code></td><td>Array of <a href="#investment-object"><em>Investment</em></a> objects</td><td>List of investments.</td></tr></tbody></table>

### *Investment* object

<table><thead><tr><th width="230.33333333333331">Property</th><th width="192">Type</th><th>Description</th></tr></thead><tbody><tr><td><code>id</code></td><td>Integer</td><td>ID of the investment.</td></tr><tr><td><code>id_account</code></td><td>Integer</td><td>ID of the related account.</td></tr><tr><td><code>label</code></td><td>String</td><td>Display name of the investment.</td></tr><tr><td><code>code</code></td><td>String or null</td><td>Technical code of the investment.</td></tr><tr><td><code>code_type</code></td><td>String</td><td>Code type: <code>ISIN</code> or <code>AMF</code>.</td></tr><tr><td><code>stock_symbol</code></td><td>String or null</td><td>Stock ticker symbol of the investment in the associated stock market.</td></tr><tr><td><code>source</code></td><td>String</td><td>Source of the ISIN code: <code>website</code> or <code>notFound</code>.</td></tr><tr><td><code>description</code></td><td>String or null</td><td>Description of the investment.</td></tr><tr><td><code>quantity</code></td><td>Decimal</td><td>Quantity of stocks of this investment.</td></tr><tr><td><code>unitprice</code></td><td>Decimal</td><td>Buy price of one stock.</td></tr><tr><td><code>unitvalue</code></td><td>Decimal</td><td>Current value of one stock.</td></tr><tr><td><code>valuation</code></td><td>Decimal</td><td>Total current value of the investment.</td></tr><tr><td><code>diff</code></td><td>Decimal</td><td>Absolute capital gain or loss.</td></tr><tr><td><code>diff_percent</code></td><td>Decimal</td><td>Relative capital gain or loss (in ratio, 1 meaning 100%).</td></tr><tr><td><code>prev_diff</code></td><td>Decimal or null</td><td>Absolute capital gain or loss since the previous value.</td></tr><tr><td><code>prev_diff_percent</code></td><td>Decimal or null</td><td>Relative capital gain or loss since the previous value (in ratio, 1 meaning 100%).</td></tr><tr><td><code>vdate</code></td><td>Date</td><td>Value date of the investment.</td></tr><tr><td><code>prev_vdate</code></td><td>Date or null</td><td>Value date of the investment when the previous synchronization occurred.</td></tr><tr><td><code>portfolio_share</code></td><td>Decimal</td><td>Allocation ratio of the investment in the portfolio (1 meaning 100%).</td></tr><tr><td><code>calculated</code></td><td>Array of strings</td><td>List of properties of this response that has been calculated rather than directly obtained from the source.</td></tr><tr><td><code>deleted</code></td><td>Date or null</td><td>Deletion date for investments that no longer exist (<code>null</code> if still present).</td></tr><tr><td><code>last_update</code></td><td>DateTime</td><td>Date of the last synchronization of the investment.</td></tr><tr><td><code>original_currency</code></td><td><a href="/pages/HmWmHsTZQ5ujENC5Pnie#currency-object"><em>Currency</em></a> object or null</td><td>For international investments, currency of the investment (if different from the bank account).</td></tr><tr><td><code>original_valuation</code></td><td>Decimal or null</td><td>For international investments, valuation of the inverstment in the original currency.</td></tr><tr><td><code>original_unitvalue</code></td><td>Decimal or null</td><td>For international investments, current value of one stock in the original currency.</td></tr><tr><td><code>original_unitprice</code></td><td>Decimal or null</td><td>For international investments, buy price of the investment in the original currency.</td></tr><tr><td><code>original_diff</code></td><td>Decimal or null</td><td>For international investments, difference between the buy price and the current valuation in the original currency.</td></tr><tr><td><code>details</code></td><td><a href="#investmentdetails-object"><em>InvestmentDetails</em></a> object or null</td><td>Additional information for the investment (if available and activated).</td></tr></tbody></table>

### *InvestmentDetails* object

<table><thead><tr><th width="242.33333333333331">Property</th><th width="159">Type</th><th>Description</th></tr></thead><tbody><tr><td><code>performance_1_year</code></td><td>Decimal or null</td><td>Performance of the stock between one year ago and today (in ratio, 1 meaning 100%).</td></tr><tr><td><code>performance_3_years</code></td><td>Decimal or null</td><td>Performance of the stock between three years ago and today (in ratio, 1 meaning 100%).</td></tr><tr><td><code>performance_5_years</code></td><td>Decimal or null</td><td>Performance of the stock between five years ago and today (in ratio, 1 meaning 100%).</td></tr><tr><td><code>srri</code></td><td>Decimal or null</td><td>Synthetic Risk and Reward Indicator of the stock (from 1 to 7).</td></tr><tr><td><code>asset_category</code></td><td>String or null</td><td>Asset category of the stock (Actions, Obligations…).</td></tr><tr><td><code>recommended_period</code></td><td>String or null</td><td>Minimum recommended period of investment.</td></tr><tr><td><code>last_update</code></td><td>DateTime or null</td><td>Date of the last synchronization of the additional information.</td></tr></tbody></table>

### *InvestmentHistoryValuesList* object

<table><thead><tr><th width="229.33333333333331">Property</th><th>Type</th><th>Description</th></tr></thead><tbody><tr><td><code>investmentvalues</code></td><td>Array of <a href="#investmenthistory-object"><em>InvestmentHistory</em></a> objects</td><td>List of investment history values.</td></tr></tbody></table>

### *InvestmentHistoryValue* object

<table><thead><tr><th width="236.33333333333331">Property</th><th width="155">Type</th><th>Description</th></tr></thead><tbody><tr><td><code>id</code></td><td>Integer</td><td>ID of the investment history.</td></tr><tr><td><code>id_investment</code></td><td>Integer</td><td>ID of the related investment.</td></tr><tr><td><code>vdate</code></td><td>Date</td><td>Date of the investment history.</td></tr><tr><td><code>unitvalue</code></td><td>Decimal</td><td>Value of one stock at the date indicated in <code>vdate</code>.</td></tr><tr><td><code>original_currency</code></td><td><a href="https://docs.budget-insight.com/reference/bank-accounts#currency-object"><em>Currency</em></a> or null</td><td>Original currency of the investment history (if different from the account currency).</td></tr><tr><td><code>original_unitvalue</code></td><td>Decimal or null</td><td>Value of one stock in the original currency at the date indicated in <code>vdate</code>.</td></tr></tbody></table>


---

# Agent Instructions: Querying This Documentation

If you need additional information that is not directly available in this page, you can query the documentation dynamically by asking a question.

Perform an HTTP GET request on the current page URL with the `ask` query parameter:

```
GET https://docs.powens.com/api-reference/products/wealth-aggregation/investments.md?ask=<question>
```

The question should be specific, self-contained, and written in natural language.
The response will contain a direct answer to the question and relevant excerpts and sources from the documentation.

Use this mechanism when the answer is not explicitly present in the current page, you need clarification or additional context, or you want to retrieve related documentation sections.
