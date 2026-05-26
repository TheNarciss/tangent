# Documents

## API endpoints

{% hint style="success" %}
Authentication: endpoints listed in this page *require* [header authentication](/api-reference/overview/authentication.md) with a *user token*.
{% endhint %}

## List documents

<mark style="color:blue;">`GET`</mark> `https://{domain}.biapi/pro/2.0/users/{userId}/documents`

List documents associated with a user.

#### Path Parameters

| Name                                     | Type            | Description             |
| ---------------------------------------- | --------------- | ----------------------- |
| userId<mark style="color:red;">\*</mark> | Integer or "me" | ID of the related user. |

#### Query Parameters

| Name                                    | Type    | Description                                               |
| --------------------------------------- | ------- | --------------------------------------------------------- |
| id\_type                                | Integer | Filter with a document type.                              |
| min\_amount                             | Decimal | Minimal (inclusive) amount.                               |
| max\_amount                             | Decimal | Maximum (inclusive) amount.                               |
| limit<mark style="color:red;">\*</mark> | Integer | Number of documents to return. The maximum value is 1000. |

{% tabs %}
{% tab title="200: OK List of documents" %}
Response body: [#documentslist-object](#documentslist-object "mention")
{% endtab %}
{% endtabs %}

{% code title="FIltering route aliases:" %}

```
/users/{userId}/subscriptions/{subscriptionId}/documents
/users/{userId}/connections/{connectionId}/documents
/users/{userId}/transactions/{transactionId}/documents
```

{% endcode %}

## Get a document

<mark style="color:blue;">`GET`</mark> `https://{domain}.biapi/pro/2.0/documents/{documentId}`

Get a single document by ID.

#### Path Parameters

| Name                                         | Type            | Description         |
| -------------------------------------------- | --------------- | ------------------- |
| documentId<mark style="color:red;">\*</mark> | Integer or "me" | ID of the document. |

{% tabs %}
{% tab title="200: OK Document details" %}
Response body: [#document-object](#document-object "mention")
{% endtab %}
{% endtabs %}

Document resources support update operations to edit metadata:

## Update a document

<mark style="color:green;">`POST`</mark> `https://{domain}.biapi/pro/2.0/documents/{documentId}`

Update a single document by ID.

#### Path Parameters

| Name                                         | Type    | Description         |
| -------------------------------------------- | ------- | ------------------- |
| documentId<mark style="color:red;">\*</mark> | Integer | ID of the document. |

#### Request Body

| Name            | Type    | Description                         |
| --------------- | ------- | ----------------------------------- |
| id\_type        | Integer | New type of the document.           |
| date            | Date    | New date of the document.           |
| duedate         | Date    | New due date of the document.       |
| total\_amount   | Decimal | New total amount of the document.   |
| untaxed\_amount | Decimal | New untaxed amount of the document. |
| vat             | Decimal | New VAT amount of the document.     |
| income          | Boolean | Is an income or an outcome.         |
| name            | String  | New name of the document.           |

{% tabs %}
{% tab title="200: OK Document updated" %}
Response body: [#document-object](#document-object "mention")
{% endtab %}
{% endtabs %}

## Data model

### ***DocumentsList*****&#x20;object**

<table><thead><tr><th width="221">Property</th><th width="157.33333333333331">Type</th><th>Description</th></tr></thead><tbody><tr><td><code>documents</code></td><td>Array of <a href="#document-object"><em>Document</em></a> objects</td><td>List of documents.</td></tr><tr><td><code>first_date</code></td><td>Date</td><td>Minimum available date for results.</td></tr><tr><td><code>last_date</code></td><td>Date</td><td>Maximum available date for results.</td></tr><tr><td><code>result_min_date</code></td><td>Date</td><td>Minimum date of results in the current response.</td></tr><tr><td><code>result_max_date</code></td><td>Date</td><td>Maximum date of results in the current response.</td></tr></tbody></table>

### *Document* object

<table><thead><tr><th width="256">Property</th><th width="189.33333333333331">Type</th><th>Description</th></tr></thead><tbody><tr><td><code>id</code></td><td>Integer</td><td>ID of the document.</td></tr><tr><td><code>id_user</code></td><td>Integer</td><td>ID of the related user.</td></tr><tr><td><code>id_subscription</code></td><td>Integer or null</td><td>ID of the related subscription.</td></tr><tr><td><code>id_type</code></td><td>Integer or null</td><td>ID of the related document type.</td></tr><tr><td><code>id_file</code></td><td>Integer or null</td><td>ID of the related file.</td></tr><tr><td><code>id_thumbnail</code></td><td>Integer or null</td><td>ID of the related thumbnail.</td></tr><tr><td><code>name</code></td><td>String or null</td><td></td></tr><tr><td><code>date</code></td><td>DateTime or null</td><td></td></tr><tr><td><code>timestamp</code></td><td>DateTime</td><td>The moment when this document has been created.</td></tr><tr><td><code>thumb_url</code></td><td>String or null</td><td></td></tr><tr><td><code>url</code></td><td>String or null</td><td></td></tr><tr><td><code>duedate</code></td><td>Date or null</td><td></td></tr><tr><td><code>total_amount</code></td><td>Decimal or null</td><td></td></tr><tr><td><code>untaxed_amount</code></td><td>Decimal or null</td><td></td></tr><tr><td><code>vat</code></td><td>Decimal or null</td><td></td></tr><tr><td><code>income</code></td><td>Boolean or null</td><td></td></tr><tr><td><code>readonly</code></td><td>Boolean</td><td></td></tr><tr><td><code>number</code></td><td>String or null</td><td></td></tr><tr><td><code>issuer</code></td><td>String or null</td><td></td></tr><tr><td><code>last_update</code></td><td>DateTime or null</td><td></td></tr><tr><td><code>has_file_on_website</code></td><td>Boolean</td><td>Whether the file is available on website.</td></tr><tr><td><code>currency</code></td><td><a href="https://docs.budget-insight.com/reference/bank-accounts#currency-object"><em>Currency</em></a> or null</td><td>Document currency.</td></tr></tbody></table>


---

# Agent Instructions: Querying This Documentation

If you need additional information that is not directly available in this page, you can query the documentation dynamically by asking a question.

Perform an HTTP GET request on the current page URL with the `ask` query parameter:

```
GET https://docs.powens.com/api-reference/products/documents-aggregation/documents.md?ask=<question>
```

The question should be specific, self-contained, and written in natural language.
The response will contain a direct answer to the question and relevant excerpts and sources from the documentation.

Use this mechanism when the answer is not explicitly present in the current page, you need clarification or additional context, or you want to retrieve related documentation sections.
