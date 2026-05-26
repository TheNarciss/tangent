# Bank account types

## API endpoints

## List bank account types

<mark style="color:blue;">`GET`</mark> `https://{domain}.biapi.pro/2.0/account_types`

List all bank account types available in the API.

{% tabs %}
{% tab title="200: OK List of account types" %}
Response body: [#accounttypeslist-object](#accounttypeslist-object "mention")
{% endtab %}
{% endtabs %}

## Get a bank account type

<mark style="color:blue;">`GET`</mark> `https://{domain}.biapi.pro/2.0/account_types/{typeId}`

Get a single bank account type by ID.

#### Path Parameters

| Name                                     | Type    | Description                  |
| ---------------------------------------- | ------- | ---------------------------- |
| typeId<mark style="color:red;">\*</mark> | Integer | ID of the bank account type. |

{% tabs %}
{% tab title="200: OK Account type details" %}
Response body: [#accounttype-object](#accounttype-object "mention")
{% endtab %}
{% endtabs %}

## **Data model**

### *AccountTypesList* object

<table><thead><tr><th width="191.33333333333331">Property</th><th width="247">Type</th><th>Description</th></tr></thead><tbody><tr><td><code>accounttypes</code></td><td>Array of <a href="#accounttype-object"><em>AccountType</em></a> objects</td><td>List of supported account types.</td></tr></tbody></table>

### ***AccountType*****&#x20;object**

<table><thead><tr><th width="192.33333333333331">Property</th><th width="195">Type</th><th>Description</th></tr></thead><tbody><tr><td><code>id</code></td><td>Number</td><td>ID of the account type.</td></tr><tr><td><code>name</code></td><td><a href="#accounttypename-values"><em>AccountTypeName</em></a> string</td><td>Technical code of the account type.</td></tr><tr><td><code>id_parent</code></td><td>Number or null</td><td>Optional, the id of the parent type.</td></tr><tr><td><code>is_invest</code></td><td>Boolean</td><td>Whether the type corresponds to an 'investment' account type. These types usually present investments and may have limitations regarding transfers.</td></tr><tr><td><code>display_name</code></td><td>String</td><td>The display name of the account type, in French.</td></tr><tr><td><code>display_name_p</code></td><td>String</td><td>The plural display name of the account type, in French.</td></tr></tbody></table>

### ***AccountTypeName*****&#x20;values**

<table><thead><tr><th width="203">Value</th><th>Description</th></tr></thead><tbody><tr><td><code>article83</code></td><td>Article 83.</td></tr><tr><td><code>capitalisation</code></td><td>Capitalization contract.</td></tr><tr><td><code>card</code></td><td>Card.</td></tr><tr><td><code>cat</code></td><td>Term Deposit Account. (Compte à Terme).</td></tr><tr><td><code>cel</code></td><td>Home Savings Account - shorter-term version of the PEL, also linked to housing loans. (Compte Épargne Logement).</td></tr><tr><td><code>checking</code></td><td>Checking account.</td></tr><tr><td><code>crowdlending</code></td><td>Crowdlending.</td></tr><tr><td><code>csl</code></td><td>General Savings Account. (Compte sur Livre).</td></tr><tr><td><code>deposit</code></td><td>Deposit account.</td></tr><tr><td><del><code>joint</code></del></td><td>(Deprecated) Joint account.</td></tr><tr><td><code>ldds</code></td><td>Sustainable and solidarity development savings (Livrets de développement durable et solidaire).</td></tr><tr><td><code>lifeinsurance</code></td><td>Life insurance account.</td></tr><tr><td><code>livret_a</code></td><td>Livret A Savings Account</td></tr><tr><td><code>livret_b</code></td><td>Livret B Savings Account.</td></tr><tr><td><code>loan</code></td><td>Loan.</td></tr><tr><td><code>madelin</code></td><td>Madelin retirement contract.</td></tr><tr><td><code>market</code></td><td>Market account.</td></tr><tr><td><code>pea</code></td><td>Shared savings plan (Plan d'Épargne en Actions).</td></tr><tr><td><code>pee</code></td><td>Company savings plan (Plan d'Épargne Entreprise).</td></tr><tr><td><code>per</code></td><td>Retirement savings plan (Plan d'Épargne Retraite).</td></tr><tr><td><code>perco</code></td><td>Group retirement savings plan (Plan d'Épargne pour la Retraite Collectif).</td></tr><tr><td><code>perp</code></td><td>Popular retirement savings plan (Plan d'Épargne Retraite Populaire).</td></tr><tr><td><code>pel</code></td><td>Home Savings Plan (Plan Épargne Logement).</td></tr><tr><td><code>real_estate</code></td><td>Real estate placement.</td></tr><tr><td><code>rsp</code></td><td>Special profit-sharing reserve (Réserve Spéciale de Participation).</td></tr><tr><td><code>savings</code></td><td>Savings account.</td></tr><tr><td><code>unknown</code></td><td>Unknown account type.</td></tr></tbody></table>


---

# Agent Instructions: Querying This Documentation

If you need additional information that is not directly available in this page, you can query the documentation dynamically by asking a question.

Perform an HTTP GET request on the current page URL with the `ask` query parameter:

```
GET https://docs.powens.com/api-reference/products/data-aggregation/bank-account-types.md?ask=<question>
```

The question should be specific, self-contained, and written in natural language.
The response will contain a direct answer to the question and relevant excerpts and sources from the documentation.

Use this mechanism when the answer is not explicitly present in the current page, you need clarification or additional context, or you want to retrieve related documentation sections.
