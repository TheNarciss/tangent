# Bank transactions

## API endpoints <a href="#list-transactions" id="list-transactions"></a>

{% hint style="success" %}
Authentication: endpoints listed in this page *require* [header authentication](/api-reference/overview/authentication.md) with a *user token*.
{% endhint %}

## List bank transactions

<mark style="color:blue;">`GET`</mark> `https://{domain}.biapi.pro/2.0/users/{userId}/transactions`

List bank transactions of the authenticated user. By default, only active (not `deleted`) transactions are returned, use the `all` parameter to get the full list.

#### Path Parameters

| Name                                     | Type            | Description             |
| ---------------------------------------- | --------------- | ----------------------- |
| userId<mark style="color:red;">\*</mark> | Integer or "me" | ID of the related user. |

#### Query Parameters

| Name                                    | Type              | Description                                                                              |
| --------------------------------------- | ----------------- | ---------------------------------------------------------------------------------------- |
| all                                     | Value-less        | Flag to include deleted transactions.                                                    |
| limit<mark style="color:red;">\*</mark> | Integer           | Number of transactions to return. The maximum value is 1000.                             |
| income                                  | Boolean           | Filter on incomes or expenditures.                                                       |
| deleted                                 | Boolean           | Filter on deleted transactions.                                                          |
| filter                                  | String            | Name of the field to use for explicit filtering: `application_date` (default) or `date`. |
| min\_date                               | Date or Month     | Minimum date of the filtering field.                                                     |
| max\_date                               | Date or Month     | Maximum date of the filtering field.                                                     |
| wording                                 | String            | Filter transactions containing the given string.                                         |
| min\_value                              | Decimal           | Minimal (inclusive) value.                                                               |
| max\_value                              | Decimal           | Maximum (inclusive) value.                                                               |
| search                                  | String            | Search in wording, dates, values, categories.                                            |
| value                                   | Decimal or String | Value of the transaction. "XX\|-XX" and "±XX" format is also accepted.                   |
| last\_update                            | DateTime          | Filter transactions updated **after** the specified date.                                |

{% tabs %}
{% tab title="200: OK List of transactions" %}
Response body: [#transactionslist-object](#transactionslist-object "mention")
{% endtab %}

{% tab title="409: Conflict No bank account is activated" %}
Response body: [Errors](/api-reference/overview/errors.md#error-response) with `noAccount` code
{% endtab %}
{% endtabs %}

{% hint style="warning" %}
Listing bank transactions requires [explicit pagination](/api-reference/overview/api-design.md#lists-pagination) (i.e. the `limit` parameter is required). Also, this endpoint provides [relational pagination](/api-reference/overview/api-design.md#relational-pagination).
{% endhint %}

{% code title="Route aliases" %}

```
/users/{userId}/transactions
/users/{userId}/accounts/{accountId}/transactions
```

{% endcode %}

## Get a bank transaction

<mark style="color:blue;">`GET`</mark> `https://{domain}.biapi.pro/2.0/users/{userId}/transactions/{transactionId}`

Get a single bank transaction by ID.

#### Path Parameters

| Name                                            | Type            | Description              |
| ----------------------------------------------- | --------------- | ------------------------ |
| userId<mark style="color:red;">\*</mark>        | Integer or "me" | ID for the related user. |
| transactionId<mark style="color:red;">\*</mark> | Integer         | ID of the transaction.   |

{% tabs %}
{% tab title="200: OK Transaction" %}
Response body: [#transaction-object](#transaction-object "mention")
{% endtab %}
{% endtabs %}

Transactions partially support updates to override some display-related properties:

## Update a bank transaction

<mark style="color:green;">`POST`</mark> `https://{domain}.biapi.pro/2.0/users/{userId}/transactions/{transactionId}`

Update metadata of a single bank transaction by ID.

Request body: [#transactionupdaterequest-object](#transactionupdaterequest-object "mention")

#### Path Parameters

| Name                                            | Type            | Description              |
| ----------------------------------------------- | --------------- | ------------------------ |
| userId<mark style="color:red;">\*</mark>        | Integer or "me" | ID for the related user. |
| transactionId<mark style="color:red;">\*</mark> | Integer         | ID of the transaction.   |

{% tabs %}
{% tab title="200: OK Updated transaction" %}
Response body: [#transaction-object](#transaction-object "mention")
{% endtab %}
{% endtabs %}

## Data model

### ***TransactionsList*****&#x20;object**

<table><thead><tr><th width="214">Property</th><th width="215.33333333333331">Type</th><th width="309.6666666666667">Description</th></tr></thead><tbody><tr><td><code>transactions</code></td><td>Array of <a href="#transaction-object"><em>Transaction</em></a> objects</td><td>List of transactions.</td></tr><tr><td><code>first_date</code></td><td>Date</td><td>Minimum available date for results.</td></tr><tr><td><code>last_date</code></td><td>Date</td><td>Maximum available date for results.</td></tr><tr><td><code>result_min_date</code></td><td>Date</td><td>Minimum date of results in the current response.</td></tr><tr><td><code>result_max_date</code></td><td>Date</td><td>Maximum date of results in the current response.</td></tr><tr><td><code>_links</code></td><td><a href="/pages/CX0NKH5hUwlBE34WcMCk#paginationlinks-object"><em>PaginationLinks</em></a> object</td><td>Opaque links to the current, previous and next pages in the collection.</td></tr></tbody></table>

### ***Transaction*****&#x20;object**

| Property               | Type                                                                                         | Description                                                                                                                                                                                                                  |
| ---------------------- | -------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `id`                   | Integer                                                                                      | ID of the transaction.                                                                                                                                                                                                       |
| `id_account`           | Integer                                                                                      | ID of the related account.                                                                                                                                                                                                   |
| `application_date`     | Date or null                                                                                 | Date considered by PFM services. This date can be edited.                                                                                                                                                                    |
| `date`                 | Date                                                                                         | Date when the transaction is posted to the account.                                                                                                                                                                          |
| `datetime`             | DateTime or null                                                                             | Date and time when the transaction is posted to the account, if available, in UTC.                                                                                                                                           |
| `vdate`                | Date or null                                                                                 | Value date of the transaction. In most cases, equivalent to `date`.                                                                                                                                                          |
| `vdatetime`            | DateTime or null                                                                             | Value date and time of the transaction, if available, in UTC. In most cases, equivalent to `datetime`.                                                                                                                       |
| `rdate`                | Date                                                                                         | Date when the transaction order has been given.                                                                                                                                                                              |
| `rdatetime`            | DateTime or null                                                                             | Date and time when the transaction order has been given, if available, in UTC.                                                                                                                                               |
| ~~`bdate`~~            | Date or null                                                                                 | *(Deprecated)* Date displayed by the bank for the transaction. Use `date` instead.                                                                                                                                           |
| ~~`bdatetime`~~        | DateTime or null                                                                             | *(Deprecated)* Date and time displayed by the bank for the transaction, if available, in UTC. Use `datetime` instead.                                                                                                        |
| `value`                | Decimal or null                                                                              | Value of the transaction.                                                                                                                                                                                                    |
| `gross_value`          | Decimal or null                                                                              | Gross value of the transaction.                                                                                                                                                                                              |
| `type`                 | [*TransactionType*](#transactiontype-values) string                                          | Type of transaction.                                                                                                                                                                                                         |
| `original_wording`     | String                                                                                       | Full label of the transaction, as seen on the bank.                                                                                                                                                                          |
| `simplified_wording`   | String                                                                                       | Simplified label of the transaction.                                                                                                                                                                                         |
| `wording`              | String or null                                                                               | Label of the transaction, can be edited.                                                                                                                                                                                     |
| `categories`           | Array                                                                                        | Array of category objects associated with the transaction. Each category object includes `code` and its `parent_code`. See [category object](/api-reference/products/data-aggregation/bank-transactions.md#category-object). |
| `date_scraped`         | DateTime                                                                                     | Date and time when the transaction was seen.                                                                                                                                                                                 |
| `coming`               | Boolean                                                                                      | If true, this transaction has not yet been posted to the account.                                                                                                                                                            |
| `active`               | Boolean                                                                                      | If false, PFM services will ignore this transaction.                                                                                                                                                                         |
| `id_cluster`           | Integer or null                                                                              | If the transaction is part of a cluster.                                                                                                                                                                                     |
| `comment`              | String or null                                                                               | User comment.                                                                                                                                                                                                                |
| `last_update`          | DateTime or null                                                                             | Last update of the transaction.                                                                                                                                                                                              |
| `deleted`              | DateTime or null                                                                             | If set, this transaction has been removed from the bank.                                                                                                                                                                     |
| `original_value`       | Decimal or null                                                                              | Value in the original currency.                                                                                                                                                                                              |
| `original_gross_value` | Decimal or null                                                                              | Gross value in the original currency.                                                                                                                                                                                        |
| `original_currency`    | [*Currency*](/api-reference/products/data-aggregation/currencies.md#currency-object) or null | Original currency.                                                                                                                                                                                                           |
| `commission`           | Decimal or null                                                                              | Commission taken on the transaction.                                                                                                                                                                                         |
| `commission_currency`  | [*Currency*](/api-reference/products/data-aggregation/currencies.md#currency-object) or null | Commission currency.                                                                                                                                                                                                         |
| ~~`country`~~          | String or null                                                                               | *(Deprecated)* Original country.                                                                                                                                                                                             |
| `card`                 | String or null                                                                               | Card number associated with the transaction.                                                                                                                                                                                 |
| `counterparty`         | [*Counterparty*](#counterparty-object) or null                                               | The transaction counterparty, i.e. an optional business or individual entity associated with the transaction.                                                                                                                |

#### **Available expands**

The following parameter can be used for [response properties expansion](/api-reference/overview/api-design.md#responses-expansion):

<table><thead><tr><th width="163.33333333333331">Property</th><th width="301">Type</th><th>Description</th></tr></thead><tbody><tr><td><code>attachments</code></td><td>Array of <a href="/pages/FmNMlfgHBosSWbMOIJjv#attachment-object">Attachment objects</a></td><td>The attachments related to a transaction.</td></tr><tr><td><code>categories</code></td><td>An array of objects </td><td><a href="/pages/huG4BAZ9Vr8Z36D5VEsM">The codes associated with the transaction.</a></td></tr></tbody></table>

### ***TransactionType*****&#x20;values**

<table><thead><tr><th width="235">Value</th><th>Description</th></tr></thead><tbody><tr><td><code>transfer</code></td><td>Transfer</td></tr><tr><td><code>order</code></td><td>Order</td></tr><tr><td><code>check</code></td><td>Check</td></tr><tr><td><code>deposit</code></td><td>Mandatory/voluntary deposits, contributions, money transfers</td></tr><tr><td><code>payback</code></td><td>Payback</td></tr><tr><td><code>withdrawal</code></td><td>Withdrawal</td></tr><tr><td><code>loan_repayment</code></td><td>Loan payment</td></tr><tr><td><code>bank</code></td><td>Bank fees</td></tr><tr><td><code>card</code></td><td>Card operation</td></tr><tr><td><code>deferred_card</code></td><td>Deferred card operation</td></tr><tr><td><code>summary_card</code></td><td>Monthly debit of a deferred card</td></tr><tr><td><code>unknown</code></td><td>Unknown transaction type</td></tr><tr><td><code>market_order</code></td><td>Market order</td></tr><tr><td><code>market_fee</code></td><td>Fees regarding a market order</td></tr><tr><td><code>arbitrage</code></td><td>Arbitrage</td></tr><tr><td><code>profit</code></td><td>Positive earnings from interests/coupons/dividends</td></tr><tr><td><code>refund</code></td><td>With opposition to a <code>payback</code>, a <code>refund</code> has a negative value</td></tr><tr><td><code>payout</code></td><td>Transfer from the e-commerce account (eg; Stripe) to the bank account</td></tr><tr><td><code>payment</code></td><td>Payment made with a payment method different from card</td></tr><tr><td><code>fee</code></td><td>Differs from <code>bank</code> type because it considers only tax/commission</td></tr></tbody></table>

{% hint style="info" %}
Forward compatibility requirement: additional types may be added in the future. When implementing type handling, always fallback to a generic case for unknown values.
{% endhint %}

### ***Category*****&#x20;object**

| Property      | Type           | Description                                                                                                                          |
| ------------- | -------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| `code`        | String         | Label of the children category *(part of* [Categorization](/api-reference/products/data-aggregation/categorization.md#categories)*)* |
| `parent_code` | String or null | Label of the parent category *(part of* [Categorization](/api-reference/products/data-aggregation/categorization.md#categories)*)*   |

### ***Counterparty*****&#x20;object**

<table><thead><tr><th width="269.3333333333333">Property</th><th width="205">Type</th><th>Description</th></tr></thead><tbody><tr><td><code>label</code></td><td>String or null</td><td>Label/name of the counterparty.</td></tr><tr><td><code>account_scheme_name</code></td><td><a href="#accountschemename-values"><em>AccountSchemeName</em></a> string or null</td><td>Type of the counterparty account number.</td></tr><tr><td><code>account_identification</code></td><td>String or null</td><td>Account number of the counterparty.</td></tr><tr><td><code>type</code></td><td>String or null</td><td>Type of the counterparty: <code>creditor</code> or <code>debtor</code>.</td></tr></tbody></table>

### ***AccountSchemeName*****&#x20;values**

<table><thead><tr><th width="301.3333333333333">Value</th><th>Description</th></tr></thead><tbody><tr><td><code>iban</code></td><td>International Bank Account Number.</td></tr><tr><td><code>bban</code></td><td>Basic Bank Account Number.</td></tr><tr><td><code>sort_code_account_number</code></td><td>United Kingdom local account number.</td></tr><tr><td><code>cpan</code></td><td>Card PAN.</td></tr><tr><td><code>tpan</code></td><td>Token which was provided by a Token Service Provider (TSP) in order to obfuscate a real card PAN.</td></tr></tbody></table>

### *TransactionUpdateRequest* object

<table><thead><tr><th width="219">Property</th><th width="93">Type</th><th width="88">Required</th><th>Description</th></tr></thead><tbody><tr><td><code>wording</code></td><td>String</td><td>No</td><td>New wording of the transaction.</td></tr><tr><td><code>application_date</code></td><td>Date</td><td>No</td><td>New application date of the transaction.</td></tr><tr><td><code>categories</code></td><td>Integer</td><td>No</td><td>Array of category objects associated with the transaction. Each category object includes <code>code</code> and its <code>parent_code</code>. See <a href="/pages/FmNMlfgHBosSWbMOIJjv#category-object">category object</a>.</td></tr><tr><td><code>comment</code></td><td>String</td><td>No</td><td>New comment of the transaction.</td></tr><tr><td><code>active</code></td><td>String</td><td>No</td><td>If false, the transaction is not considered in balance summaries and sums.</td></tr></tbody></table>


---

# Agent Instructions: Querying This Documentation

If you need additional information that is not directly available in this page, you can query the documentation dynamically by asking a question.

Perform an HTTP GET request on the current page URL with the `ask` query parameter:

```
GET https://docs.powens.com/api-reference/products/data-aggregation/bank-transactions.md?ask=<question>
```

The question should be specific, self-contained, and written in natural language.
The response will contain a direct answer to the question and relevant excerpts and sources from the documentation.

Use this mechanism when the answer is not explicitly present in the current page, you need clarification or additional context, or you want to retrieve related documentation sections.
