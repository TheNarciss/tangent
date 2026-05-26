# Loan amortizations

## API endpoints <a href="#list-investments" id="list-investments"></a>

{% hint style="success" %}
Authentication: endpoints listed in this page *require* [header authentication](/api-reference/overview/authentication.md) with a *user token*.
{% endhint %}

## List loan amortizations

<mark style="color:blue;">`GET`</mark> `https://{domain}.biapi.pro/2.0/users/{userId}/amortizations`

List loan amortizations related to a user.

#### Path Parameters

| Name                                     | Type            | Description             |
| ---------------------------------------- | --------------- | ----------------------- |
| userId<mark style="color:red;">\*</mark> | Integer or "me" | ID of the related user. |

{% tabs %}
{% tab title="200: OK List of loan amortizations" %}
Response body: [#marketorderslist-object](#marketorderslist-object "mention")
{% endtab %}

{% tab title="401: Unauthorized You are not authorized to use this feature. Please contact us." %}

```javascript
{
    // Response
}
```

{% endtab %}
{% endtabs %}

{% code title="Filtering route aliases:" %}

```
/users/{userId}/amortizations
/users/{userId}/accounts/{accountId}/amortizations
/users/{userId}/connections/{connectionId}/amortizations
```

{% endcode %}

## Data model

### *LoanAmortizationsList* object

<table><thead><tr><th width="226.33333333333331">Property</th><th>Type</th><th>Description</th></tr></thead><tbody><tr><td><code>loanamortizations</code></td><td>Array of <a href="#loanamortization-object">LoanAmortizations</a> objects</td><td>List of loan amortizations.</td></tr></tbody></table>

### LoanAmortization object

<table><thead><tr><th width="255.33333333333331">Property</th><th>Description</th><th data-hidden>Type</th></tr></thead><tbody><tr><td><code>id_account</code></td><td>ID of the related account.</td><td>Integer</td></tr><tr><td><code>payment_date</code></td><td>Date of the payment.</td><td>Date or null</td></tr><tr><td><code>amortization_amount</code></td><td>Amount of the amortization.</td><td><a href="#monetaryamount-object">MonetaryAmount</a> object</td></tr><tr><td><code>interest_amount</code></td><td>Amount of the loan's interest.</td><td><a href="#monetaryamount-object">MonetaryAmount</a> object</td></tr><tr><td><code>insurance_amount</code></td><td>Amount of the loan's insurance.</td><td><a href="#monetaryamount-object">MonetaryAmount</a> object</td></tr><tr><td><code>total_payment_amount</code></td><td>Amount of the total due payment.</td><td><a href="#monetaryamount-object">MonetaryAmount</a> object</td></tr><tr><td><code>remaining_capital</code></td><td>Remaining capital to be refunded.</td><td><a href="#monetaryamount-object">MonetaryAmount</a> object</td></tr><tr><td><code>period</code></td><td>Period covered by amortization.<br>Should be monthly (YYYY_MM) or annual (YYYY).</td><td>String</td></tr><tr><td><code>calculated</code></td><td>List of properties of this response that has been calculated rather than directly obtained from the source.</td><td>Array of strings</td></tr><tr><td><code>deleted</code></td><td>Deletion date for amortizations that no longer exist (<code>null</code> if still present).</td><td>DateTime or null</td></tr><tr><td><code>last_update</code></td><td>Date of the last synchronization of the investment.</td><td>DateTime</td></tr></tbody></table>

### *MonetaryAmount* object

<table><thead><tr><th width="172.33333333333331">Property</th><th width="147">Type</th><th>Description</th></tr></thead><tbody><tr><td><code>currency</code></td><td>String</td><td><a href="https://docs.1010data.com/1010dataReferenceManual/DataTypesAndFormats/currencyUnitCodes.html">Currency codes (ISO 4217) </a>of the analyzed accounts. EUR only.</td></tr><tr><td><code>value</code></td><td>Decimal or null</td><td>Amount value. Rounded to two decimal places.</td></tr></tbody></table>


---

# Agent Instructions: Querying This Documentation

If you need additional information that is not directly available in this page, you can query the documentation dynamically by asking a question.

Perform an HTTP GET request on the current page URL with the `ask` query parameter:

```
GET https://docs.powens.com/api-reference/products/wealth-aggregation/loan-amortizations.md?ask=<question>
```

The question should be specific, self-contained, and written in natural language.
The response will contain a direct answer to the question and relevant excerpts and sources from the documentation.

Use this mechanism when the answer is not explicitly present in the current page, you need clarification or additional context, or you want to retrieve related documentation sections.
