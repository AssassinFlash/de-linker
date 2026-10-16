<!-- source: https://api-docs.deepseek.com/api/list-models
     title: Lists Models | DeepSeek API Docs
     fetched (UTC, Apify apify/website-content-crawler): 2026-10-16T17:13:01.240Z -->

# Lists Models | DeepSeek API Docs

**object** stringrequired

**Possible values:** \[`list`\]

The object type, which is always `list`.

**data**

object\[\]

required

The list of model objects.

*   Array \[
    

**id** stringrequired

The model identifier, which can be referenced in the API endpoints.

**object** stringrequired

**Possible values:** \[`model`\]

The object type, which is always "model".

**owned\_by** stringrequired

The organization that owns the model.

**name** string

The display name of the model, for use in model pickers and model discovery tools.

**context\_window** integer

The total token capacity of the context window, counting both input and output tokens.

**max\_output\_tokens** integer

The maximum number of output tokens the server allows in a single response, i.e. the maximum accepted value of `max_tokens`.

**input\_modalities** string\[\]

**Possible values:** \[`text`, `image`\]

The input types the model accepts.

**output\_modalities** string\[\]

**Possible values:** \[`text`\]

The media types the model can generate.

**effort**

object

The effort levels available when thinking mode is enabled.

**supported\_levels** string\[\]required

The effort levels the model supports when thinking mode is enabled, in the recommended display order. These are the values accepted by the `reasoning_effort` parameter; `none`, which turns thinking mode off, is not included.

**default\_level** string

The effort level the server uses when thinking mode is enabled and the request does not specify one. Always one of `supported_levels`. Only present when the server defines a default for the model.

**api\_capabilities**

object

Model behavior declared per API protocol.

**anthropic\_messages**

object

**system\_prompt\_update** stringrequired

**Possible values:** \[`leading-only`, `in-history`\]

How the model picks up an updated system prompt during a conversation.

*   `leading-only`: only the system prompt at the start of the conversation takes effect. To change the system prompt, modify that leading system prompt; system messages appearing later in the history are not treated as system prompt updates.
*   `in-history`: a `system` message may be appended to the conversation history. The latest `system` message in the history provides the complete effective system prompt and replaces all earlier ones.

*   \]