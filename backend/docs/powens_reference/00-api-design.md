# API design

## Root and versioning <a href="#root-and-versioning" id="root-and-versioning"></a>

Current version (2.0) of our API is available, for each API domain, at the following path:

```
https://{domain}.biapi.pro/2.0/*
```

In this documentation, all path references and examples are relative to this root.

## Services design <a href="#services-design" id="services-design"></a>

Our API exposes a set of *endpoints* to interact with *resources*. Endpoint routes are named after the resources they interact with:

<table><thead><tr><th width="249">Path example</th><th>Resource</th></tr></thead><tbody><tr><td><code>/connections/*</code></td><td>Manage connections</td></tr><tr><td><code>/accounts/*</code></td><td>Manage bank accounts</td></tr><tr><td><code>/auth/*</code></td><td>Common prefix for authentication services</td></tr></tbody></table>

Deep paths are sometimes uses to access sub-resources:

```
/users/1/connections/2/accounts/23/transactions/48
```

Interactions with resources mostly follow conventions by using dedicated [HTTP methods](https://www.w3.org/Protocols/rfc2616/rfc2616-sec9.html) to perform operations:

| Method                                          | Operation                   |
| ----------------------------------------------- | --------------------------- |
| `GET /resources`                                | List resources              |
| `GET /resources/{id}`                           | Get a unique resource by id |
| `POST /resources`                               | Create a new resource       |
| `POST /resources/{id}` or `PUT /resources/{id}` | Update a resource           |
| `DELETE /resources/{id}`                        | Delete a resource           |

Not all operations are valid for every resource, API reference of each service describes the specific behaviors by endpoint.

## HTTP response codes <a href="#http-response-codes" id="http-response-codes"></a>

We use various relevant HTTP response codes depending on the success or failure of the request. Successful responses (2XX status) return the entity documented with each endpoint in the services reference. Error responses (4XX and 5XX status) use a [common error format](/api-reference/overview/errors.md).

<table><thead><tr><th width="91.33333333333331">Code</th><th width="144">Message</th><th>Description</th></tr></thead><tbody><tr><td>200</td><td>OK</td><td>Defaut success code for responses.</td></tr><tr><td>202</td><td>Accepted</td><td>Alternate success code for requests that need further interaction to resume the operation (e.g. connection addition or sync).</td></tr><tr><td>204</td><td>No content</td><td>Success code for requests that return nothing.</td></tr><tr><td>400</td><td>Bad request</td><td>Error code when the request is invalid, e.g. the supplied parameters are incorrect.</td></tr><tr><td>401</td><td>Unauthorized</td><td>Error code when the service requires authentication and the proper header was incorrectly provided.</td></tr><tr><td>403</td><td>Forbidden</td><td>Error code when an authentication token with insufficient scope was provided to access an endpoint.</td></tr><tr><td>404</td><td>Not found</td><td>Error code when the route was incorrect, or the resource is unknown for the provided authorization scope.</td></tr><tr><td>409</td><td>Conflict</td><td>Error code when a request could not be honored because of a conflicting state with the API.</td></tr><tr><td>500</td><td>Internal servor error</td><td>Error code for failures related to internal bugs.</td></tr><tr><td>503</td><td>Service unavailable</td><td>Error code when our API is temporarily down for maintenance.</td></tr></tbody></table>

{% hint style="info" %}
Error handling should be preferably based on the [error code](/api-reference/overview/errors.md#error-codes) rather than the HTTP status code.
{% endhint %}

## Requests and responses format <a href="#requests-and-responses-format" id="requests-and-responses-format"></a>

Requests to the API, unless specified, should be formatted in [JSON](https://www.json.org/), with the appropriate `content-type` request header.

For convenience, we also accept `x-www-form-urlencoded` requests when the body does not imply nested levels.

Responses are exclusively returned as [JSON](https://www.json.org/) objects, you can specify it using the recommended `accept` request header.

## Lists pagination

On endpoints that allow access to a list of items, pagination is used to easily slice the results and navigate the whole collection.

Pagination relies on a limit on the number of returned items in a single API call, that can be set using the `limit` query parameter.\
Usage of the `limit` parameter is *advised* for most resources, and *mandatory* for some (explicitly documented), in order to control the maximum number of returned items.

Except documented otherwise, `limit` has a maximum value of 1000.

### Basic offset pagination

Most of collection endpoints accept an `offset` parameters. Combine it with `limit` to access arbitrary ranges of items.

### Relational pagination

Some paginated resources also return an easy-to-use `_link` property with links to use for sibling loads.

### *PaginationLinks* object

<table><thead><tr><th width="137.33333333333331">Property</th><th width="171">Type</th><th>Description</th></tr></thead><tbody><tr><td><code>self</code></td><td>Link object</td><td>Reference to the current page (with a <code>href</code> property).</td></tr><tr><td><code>prev</code></td><td>Link object or null</td><td>Reference to the previous page (with a <code>href</code> property), if any.</td></tr><tr><td><code>next</code></td><td>Link object or null</td><td>Full address of the next page (with a <code>href</code> property), if any.</td></tr></tbody></table>

Each of these link references is either `null` (if there is no previous or next page), or is an object with an `href` property, which is the URL of the relevant page (previous, current or next).

{% hint style="info" %}
The provided links are opaque and should be used "as is", they encapsulate the filtering logic expressed by parameters on the initial request.
{% endhint %}

<details>

<summary>Example</summary>

```
GET /users/me/transactions?min_date=2022-12-01&income=false&limit=50
```

```json
{
  "transactions": [ ... ],
  "_links": {
    "prev": null,
    "self": {
      "href": "https://{domain}.biapi.pro/2.0/users/me/transactions?min_date=2022-12-01&income=false&limit=50"
    },
    "next": {
      "href": "https://{domain}.biapi.pro/2.0/users/me/transactions?min_date=2022-12-01&income=false&limit=50&cursor=W3sib3AiOiAibHQiLCAidmFsdWUiOiAiMjAyMC0wMy0wOCJ9LCB7Im9wIjogImd0IiwgInZhbHVlIjogOTgwNzg3fV0="
    }
  }
}
```

</details>

## Lists temporal filtering <a href="#lists-windowing" id="lists-windowing"></a>

Some resources may be filtered using a temporal criterion on a property. In this case, the list endpoint usually support `min_date` and `max_date` parameters.

The value can be a date (in ISO YYYY-MM-DD format), but also a month or a year.

## Lists implicit filtering <a href="#lists-implicit-filtering" id="lists-implicit-filtering"></a>

Some collections use *soft-deletion* or an enabled/disabled state. For these resources, implicit filtering is applied to exclude deleted or disabled resources from the default API responses. You can access the excluded items by adding the `all` flag query parameter.

Example:

<table><thead><tr><th width="310">Path</th><th>Resources</th></tr></thead><tbody><tr><td><code>/user/me/accounts</code></td><td>Return bank accounts that are not disabled.</td></tr><tr><td><code>/user/me/accounts?all</code></td><td>Return all bank accounts.</td></tr><tr><td><code>/user/me/accounts/123?all</code></td><td>Interact with the disabled account 123.</td></tr></tbody></table>

## Response expansion <a href="#responses-expansion" id="responses-expansion"></a>

Most API calls support an expansion mechanism to enrich the response with linked sub-resources. This enables fetching a full set of data without performing multiple requests. Expansion is defined using the `expand` query parameter with a comma-separated list of wanted sub-resources. Nested sub-resources are also available with brackets.

Example: The following request will return the bank account 123 with associated connection, the list of latest transactions (it is not possible to control pagination or filtering here), and for each transaction the associated category:

```http
GET /users/me/connections/123?expand=accounts,connector[countries]
```

```json
{
  "id" : 123,
  "state": null,
  "accounts": [
    { "id": 1234, "name": "Current account", "disabled": "2020-06-01 12:34:56", … },
    { "id": 4567, "name": "Saving account", "disabled": "2020-06-01 12:34:56", … },
    …
  ],
  "connector" : {
    "id": 40,
    "name": "Connecteur de test",
    "auth_mechanism": "credentials",
    "capabilities": [ "bank", "document", "profile", … ],
    "countries": [ { "id": "fr", "name": "France" }, … ]
  },
  …
}
```

Each resource defines in its documentation the available expansions.


---

# Agent Instructions: Querying This Documentation

If you need additional information that is not directly available in this page, you can query the documentation dynamically by asking a question.

Perform an HTTP GET request on the current page URL with the `ask` query parameter:

```
GET https://docs.powens.com/api-reference/overview/api-design.md?ask=<question>
```

The question should be specific, self-contained, and written in natural language.
The response will contain a direct answer to the question and relevant excerpts and sources from the documentation.

Use this mechanism when the answer is not explicitly present in the current page, you need clarification or additional context, or you want to retrieve related documentation sections.
