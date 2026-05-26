# Bank accounts

## API endpoints

{% hint style="success" %}
Authentication: endpoints listed in this page *require* [header authentication](/api-reference/overview/authentication.md) with a *user token*.
{% endhint %}

## List bank accounts

<mark style="color:blue;">`GET`</mark> `https://{domain}.biapi.pro/2.0/users/{userId}/accounts`

#### Path Parameters

| Name                                     | Type            | Description             |
| ---------------------------------------- | --------------- | ----------------------- |
| userId<mark style="color:red;">\*</mark> | Integer or "me" | ID of the related user. |

#### Query Parameters

| Name | Type       | Description                       |
| ---- | ---------- | --------------------------------- |
| all  | Value-less | Flag to access disabled accounts. |

{% tabs %}
{% tab title="200: OK List of bank accounts" %}
Response body: [#bankaccountslist-object](#bankaccountslist-object "mention")
{% endtab %}
{% endtabs %}

{% code title="Filtering route alias:" %}

```
/users/{userId}/connections/{connectionId}/accounts
```

{% endcode %}

## Get a bank account

<mark style="color:blue;">`GET`</mark> `https://{domain}.biapi.pro/2.0/users/{userId}/accounts/{accountId}`

Get a single bank account by ID.

#### Path Parameters

| Name                                        | Type            | Description             |
| ------------------------------------------- | --------------- | ----------------------- |
| accountId<mark style="color:red;">\*</mark> | Integer         | ID of the bank account. |
| userId<mark style="color:red;">\*</mark>    | Integer or "me" | ID of the related user. |

{% tabs %}
{% tab title="200: OK Bank account details" %}
Response body: [#bankaccount-object](#bankaccount-object "mention")
{% endtab %}
{% endtabs %}

Bank account ressources partially support an update operation to handle activation/deactivation, or to override some display-related properties of accounts:

## Update a bank account

<mark style="color:green;">`POST`</mark> `https://{domain}.biapi/pro/2.0/users/{userId}/accounts/{accountId}`

Update a single bank account by ID.

Request body: [#bankaccountupdaterequest-object](#bankaccountupdaterequest-object "mention")

#### Path Parameters

| Name                                        | Type    | Description             |
| ------------------------------------------- | ------- | ----------------------- |
| accountId<mark style="color:red;">\*</mark> | Integer | ID of the bank account. |
| userId<mark style="color:red;">\*</mark>    | Integer | ID of the related user. |

#### Query Parameters

| Name | Type       | Description                                       |
| ---- | ---------- | ------------------------------------------------- |
| all  | Value-less | Add this flag to access a disabled bank accounts. |

{% tabs %}
{% tab title="200: OK Bank account updated" %}
Response body: [#bankaccount-object](#bankaccount-object "mention")
{% endtab %}
{% endtabs %}

## Life cycle <a href="#disabled-accounts" id="disabled-accounts"></a>

### Activation

Bank accounts can be in a disabled or enabled state.

{% hint style="warning" %}
For legal compliance, accounts are disabled by default. Also, disabling account will result in the deletion of account child resources (transactions, investments, market orders, balances).
{% endhint %}

#### Querying

Disabled accounts will only appear when passing the `all` parameter:

```
GET /users/{userId}/accounts/{id}?all
GET /users/{userId}/connections/{connectionId}/accounts/{id}?all
```

#### Enabling

To enable one such account, it is necessary to perform a `POST` request on that account, with the `all` parameter and `{ "disabled": false }`.

Please note that this action represents the PSU's consent.

## Webhooks

### Accounts  fetched

An `ACCOUNTS_FETCHED` webhook is emitted during a sync after bank accounts have been synchronized, but before the transactions are processed.

Webhook request :

<table><thead><tr><th width="235">Property</th><th width="263">Type</th><th width="250">Description</th></tr></thead><tbody><tr><td><code>user</code></td><td><em>User</em> object</td><td>The user related to the sync.</td></tr><tr><td><code>connection</code></td><td><em>Connection</em> object</td><td>Connection.</td></tr><tr><td><code>connection</code><br>  <code>.connector</code></td><td><em>Connector</em> object</td><td>The connector associated with the connection.</td></tr><tr><td><code>connection</code><br>  <code>.sources</code></td><td>Array of <em>ConnectionSource</em> objects</td><td>The activated connections sources that were synced.</td></tr><tr><td><code>connection</code><br>  <code>.accounts</code></td><td>Array of <a href="#bankaccount-object"><em>BankAccount</em></a> objects</td><td>The activated bank accounts sources that were synced.</td></tr></tbody></table>

### Accounts synced

An `ACCOUNT_SYNCED` webhook is emitted during a sync after a bank account was processed, including new transactions.\
Webhook request: [*BankAccount*](#bankaccount-object) object with the following additional properties:

<table><thead><tr><th width="198.33333333333331">Property</th><th width="267">Type</th><th>Description</th></tr></thead><tbody><tr><td><code>investments</code></td><td>Array of <a href="/pages/iKhSCWcWBNvoKu6pRt1a#investment-object"><em>Investment</em></a> objects</td><td>The new investments that were found.</td></tr><tr><td><code>investments[]</code><br>  <code>.pockets</code></td><td>Array of <a href="/pages/il9kRFimRhX9apvn0OWG#pocket-object"><em>Pocket</em></a> objects</td><td>On each <code>investment</code> item, the new pockets that were found.</td></tr><tr><td><del><code>recipients</code></del></td><td>Array of <em>Recipient</em> objects</td><td><em>(Deprecated)</em> The new recipients that were found (for transfer usage).</td></tr><tr><td><code>transactions</code></td><td>Array of <a href="/pages/FmNMlfgHBosSWbMOIJjv#transaction-object"><em>Transaction</em></a> objects</td><td>The new transactions that were found.</td></tr><tr><td><del><code>transfers</code></del></td><td>Array of <em>Transfer</em> objects</td><td><em>(Deprecated)</em> The new transfers that were found.</td></tr></tbody></table>

### Account categorized

An `ACCOUNT_CATEGORIZED` webhook is emitted during a sync after bank accounts have been synchronized, and after the transactions are processed.

<table><thead><tr><th width="198.33333333333331">Property</th><th width="267">Type</th><th>Description</th></tr></thead><tbody><tr><td><code>transactions</code></td><td>Array of <a href="/pages/FmNMlfgHBosSWbMOIJjv#transaction-object"><em>Transaction</em></a> objects</td><td>The new transactions that were found.</td></tr></tbody></table>

### Account disabled

An `ACCOUNT_DISABLED` webhook is emitted after a bank account was disabled. The `disabled` property in the request contains the deactivation date.

Webhook request: *BankAccount* object

### Account enabled <a href="#account-enabled" id="account-enabled"></a>

An `ACCOUNT_ENABLED` webhook is emitted after a bank account was enabled. The `disabled` property in the request will be `null`.

Webhook request: *BankAccount* object

### Account found

An `ACCOUNT_FOUND` webhook is emitted after a **new** bank account was discovered. The account is `disabled` by default.

Webhook request:

<table><thead><tr><th width="203.33333333333331">Property</th><th width="198">Type</th><th>Description</th></tr></thead><tbody><tr><td><code>id</code></td><td>Integer</td><td>ID of the bank account.</td></tr><tr><td><code>id_user</code></td><td>Integer</td><td>ID of the related user.</td></tr><tr><td><code>id_connection</code></td><td>Integer</td><td>ID of the related connection.</td></tr><tr><td><code>disabled</code></td><td>DateTime</td><td>New accounts are disabled by default, so the property is set to the discovery date.</td></tr><tr><td><code>type</code></td><td><a href="/pages/WoiemzMmXgp1u3bjLKMj#accounttypename-values"><em>AccountTypeName</em></a> <em>string</em></td><td>Technical code of the account type.</td></tr></tbody></table>

## Data model

### *BankAccountsList* object

<table><thead><tr><th width="150.33333333333331">Property</th><th width="244">Type</th><th>Description</th></tr></thead><tbody><tr><td><code>accounts</code></td><td>Array of <a href="#bankaccount-object"><em>BankAccount</em></a> objects</td><td>List of bank accounts.</td></tr><tr><td><code>balances</code></td><td>Object</td><td>Associative map of ISO currency codes to the total balance (decimal number) of accounts in the given currency.</td></tr><tr><td><code>coming_balances</code></td><td>Object</td><td>Associative map of coming balances.</td></tr></tbody></table>

### ***BankAccount*****&#x20;object**

<table><thead><tr><th width="182.33333333333331">Property</th><th width="215">Type</th><th>Description</th></tr></thead><tbody><tr><td><code>id</code></td><td>Integer</td><td>ID of the bank account.</td></tr><tr><td><code>id_connection</code></td><td>Integer or null</td><td>ID of the related connection.</td></tr><tr><td><code>id_user</code></td><td>Integer or null</td><td>ID of the related user.</td></tr><tr><td><code>id_source</code></td><td>Integer or null</td><td>ID of the related connection source.</td></tr><tr><td><code>id_parent</code></td><td>Integer or null</td><td>ID of the parent account.</td></tr><tr><td><code>number</code></td><td>String or null</td><td>Account number.</td></tr><tr><td><code>original_name</code></td><td>String</td><td>Original name of the account, as seen on the bank.</td></tr><tr><td><code>balance</code></td><td>Decimal or null</td><td>Balance of the account.</td></tr><tr><td><code>coming</code></td><td>Decimal or null</td><td>Amount of coming operations not yet debited.</td></tr><tr><td><code>display</code></td><td>Boolean</td><td>Whether the bank account should be presented.</td></tr><tr><td><code>last_update</code></td><td>DateTime or null</td><td>Last successful update of the account.</td></tr><tr><td><code>deleted</code></td><td>DateTime or null</td><td>If set, this account is not found on the website anymore.</td></tr><tr><td><code>disabled</code></td><td>DateTime or null</td><td>If set, this account has been disabled by user and will not be synchronized anymore.</td></tr><tr><td><code>iban</code></td><td>String or null</td><td>Account IBAN.</td></tr><tr><td><code>currency</code></td><td><a href="/pages/HmWmHsTZQ5ujENC5Pnie#currency-object"><em>Currency</em></a> object or null</td><td>Account currency.</td></tr><tr><td><code>type</code></td><td><a href="/pages/WoiemzMmXgp1u3bjLKMj#accounttype-object"><em>AccountType</em></a> object</td><td>Technical code of the account type.</td></tr><tr><td><code>id_type</code></td><td>Integer</td><td>ID of the account type.</td></tr><tr><td><code>bookmarked</code></td><td>Integer</td><td>This account has been bookmarked by user.</td></tr><tr><td><code>name</code></td><td>String</td><td>The name of the account.</td></tr><tr><td><code>error</code></td><td>String or null</td><td>If the last update has failed, the error code.</td></tr><tr><td><code>usage</code></td><td><a href="#bankaccountusage-values"><em>BankAccountUsage</em></a> string</td><td>Account usage. If not overridden, the value of <code>original_usage</code> is returned.</td></tr><tr><td><del><code>ownership</code></del></td><td><a href="#bankaccountownership-values"><em>BankAccountOwnership</em></a> string or null</td><td><em>(Deprecated)</em> Relationship between the credentials owner and the account.</td></tr><tr><td><code>company_name</code></td><td>String or null</td><td>Name of the company holding the employee savings of the account.</td></tr><tr><td><code>loan</code></td><td><a href="#loan-object"><em>Loan</em></a> object or null</td><td>For <code>loan</code> accounts, the loan details.</td></tr></tbody></table>

**Available expands**

The following parameters can be used for response properties expansion:

<table><thead><tr><th width="193.33333333333331">Property</th><th width="198">Type</th><th>Description</th></tr></thead><tbody><tr><td><code>connection</code></td><td><a href="/pages/5W80jLGBq7ifvqhRCiXo#connection-object"><em>Connection</em></a> object</td><td>The connection associated with this bank account.</td></tr></tbody></table>

### ***BankAccountUsage*****&#x20;values**

<table><thead><tr><th width="160">Value</th><th>Description</th></tr></thead><tbody><tr><td><code>PRIV</code></td><td>Private account.</td></tr><tr><td><code>ORGA</code></td><td>Professional account.</td></tr><tr><td><code>null</code></td><td>No usage detail.</td></tr></tbody></table>

{% hint style="info" %}
Forward compatibility requirement: additional usages may be added in the future. When implementing usage handling, always fallback to a generic case for unknown values.
{% endhint %}

### ***BankAccountOwnership*****&#x20;values (deprecated)**

<table><thead><tr><th width="156">Value</th><th>Description</th></tr></thead><tbody><tr><td><code>owner</code></td><td>Account holder.</td></tr><tr><td><code>co-owner</code></td><td>Holder on a joint account.</td></tr><tr><td><code>attorney</code></td><td>Account authorized agent.</td></tr></tbody></table>

{% hint style="info" %}
Forward compatibility requirement: additional ownership values may be added in the future. When implementing ownership handling, always fallback to a generic case for unknown values.
{% endhint %}

### ***Loan*****&#x20;object**

<table><thead><tr><th>Property</th><th width="162.33333333333331">Type</th><th>Description</th></tr></thead><tbody><tr><td><code>total_amount</code></td><td>Decimal or null</td><td>Total amount of the loan.</td></tr><tr><td><code>available_amount</code></td><td>Decimal or null</td><td>Amount of the loan not yet released and still available.</td></tr><tr><td><code>used_amount</code></td><td>Decimal or null</td><td>Amount of the load already used.</td></tr><tr><td><code>subscription_date</code></td><td>Date or null</td><td>Subscription date of the loan.</td></tr><tr><td><code>maturity_date</code></td><td>Date or null</td><td>Estimated end date of the loan.</td></tr><tr><td><code>start_repayment_date</code></td><td>Date or null</td><td>When starts the repayment of the loan. <br>In case of deferred loans, some fees could be payed by the borrower before the first repayment term planned at this <code>start_repayment_date</code>.</td></tr><tr><td><code>deferred</code></td><td>Boolean or null</td><td>(beta) True if loan repayment has not yet begun.</td></tr><tr><td><code>next_payment_amount</code></td><td>Decimal or null</td><td>Amount of the next payment.</td></tr><tr><td><code>next_payment_date</code></td><td>Date or null</td><td>Date of the next payment.</td></tr><tr><td><code>rate</code></td><td>Decimal or null</td><td>Rate of the loan.</td></tr><tr><td><code>nb_payments_left</code></td><td>Integer or null</td><td>Number of payments still due.</td></tr><tr><td><code>nb_payments_done</code></td><td>Integer or null</td><td>Number of payments done.</td></tr><tr><td><code>nb_payments_total</code></td><td>Integer or null</td><td>Total number of payments.</td></tr><tr><td><code>last_payment_amount</code></td><td>Decimal or null</td><td>Amount of the last payment.</td></tr><tr><td><code>last_payment_date</code></td><td>Date or null</td><td>Date of the last payment.</td></tr><tr><td><code>account_label</code></td><td>String or null</td><td>Name of the debited account.</td></tr><tr><td><code>insurance_label</code></td><td>String or null</td><td>Label of the insurance.</td></tr><tr><td><code>insurance_amount</code></td><td>Decimal or null</td><td>Amount of the loan's insurance.</td></tr><tr><td><code>insurance_rate</code></td><td>Decimal or null</td><td>Rate of the insurance (between 0 and 1).</td></tr><tr><td><code>duration</code></td><td>Integer or null</td><td>Duration of the loan, in months.</td></tr><tr><td><code>type</code></td><td>String</td><td>Type of the loan: <code>mortgage</code>, <code>consumercredit,  revolvingcredit</code> or <code>loan</code> (by default).</td></tr></tbody></table>

### *BankAccountUpdateRequest* object

<table><thead><tr><th width="152">Name</th><th width="137">Type</th><th width="103">Required</th><th>Description</th></tr></thead><tbody><tr><td><code>display</code></td><td>Boolean</td><td>No</td><td>Whether the bank account should be displayed and included in aggregated metrics.</td></tr><tr><td><code>name</code></td><td>String</td><td>No</td><td>Display name of the account.</td></tr><tr><td><code>disabled</code></td><td>Boolean</td><td>No</td><td>Whether the bank account should be synchronized.</td></tr><tr><td><code>bookmarked</code></td><td>Boolean</td><td>No</td><td>Whether the bank account is bookmarked.</td></tr><tr><td><code>usage</code></td><td><a href="#bankaccountusage-values"><em>BankAccountUsage</em></a> string</td><td>No</td><td>Account usage.</td></tr></tbody></table>


---

# Agent Instructions: Querying This Documentation

If you need additional information that is not directly available in this page, you can query the documentation dynamically by asking a question.

Perform an HTTP GET request on the current page URL with the `ask` query parameter:

```
GET https://docs.powens.com/api-reference/products/data-aggregation/bank-accounts.md?ask=<question>
```

The question should be specific, self-contained, and written in natural language.
The response will contain a direct answer to the question and relevant excerpts and sources from the documentation.

Use this mechanism when the answer is not explicitly present in the current page, you need clarification or additional context, or you want to retrieve related documentation sections.
