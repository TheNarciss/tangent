# Document types

## API endpoints

## List document types

<mark style="color:blue;">`GET`</mark> `https://{domain}.biapi.pro/2.0/documenttypes`

{% tabs %}
{% tab title="200: OK List of documents types" %}
Response body: [#documenttypeslist-object](#documenttypeslist-object "mention")
{% endtab %}
{% endtabs %}

## Data model

### *DocumentTypesList* object

| Property        | Type                                                    | Description             |
| --------------- | ------------------------------------------------------- | ----------------------- |
| `documenttypes` | Array of [*DocumentType*](#documenttype-values) strings | List of document types. |

### *DocumentType* values

| Value                           |
| ------------------------------- |
| `zimage`                        |
| `pdf`                           |
| `odt`                           |
| `bill`                          |
| `RIB`                           |
| `statement`                     |
| `contract`                      |
| `notice`                        |
| `report`                        |
| `other`                         |
| ~~`income_tax`~~ (*deprecated*) |
| `kiid`                          |
| `certificate`                   |
| `identity`                      |
| `payslip`                       |
| `exchange_statement`            |
| `bill_debit_advice`             |

{% hint style="info" %}
Forward compatibility requirement: additional types may be added in the future. When implementing type handling, always fallback to a generic case for unknown values.
{% endhint %}


---

# Agent Instructions: Querying This Documentation

If you need additional information that is not directly available in this page, you can query the documentation dynamically by asking a question.

Perform an HTTP GET request on the current page URL with the `ask` query parameter:

```
GET https://docs.powens.com/api-reference/products/documents-aggregation/document-types.md?ask=<question>
```

The question should be specific, self-contained, and written in natural language.
The response will contain a direct answer to the question and relevant excerpts and sources from the documentation.

Use this mechanism when the answer is not explicitly present in the current page, you need clarification or additional context, or you want to retrieve related documentation sections.
