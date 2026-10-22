# Contact selection copy

EN is the source. DE was composed for the native German form in Sie form. This is a selection summary and a real inclusion decision; the existing contact promise and customer message remain unchanged.

| Surface | English candidate | German candidate |
| --- | --- | --- |
| Fieldset / native team record | Product selection | Produktauswahl |
| Include checkbox | Include this selection with my message | Diese Auswahl meiner Nachricht beifügen |
| Excluded state | This selection will not be sent. | Diese Auswahl wird nicht mitgesendet. |
| Unavailable source | This selection could not be loaded. You can exclude it and send your message. | Diese Auswahl konnte nicht geladen werden. Sie können sie abwählen und Ihre Nachricht senden. |
| POST validation | Please review the product selection or exclude it before sending. | Bitte prüfen Sie die Produktauswahl oder wählen Sie sie vor dem Senden ab. |
| Power lower / upper bound | Minimum power (kW) / Maximum power (kW) | Mindestleistung (kW) / Höchstleistung (kW) |
| Capacity lower / upper bound | Minimum capacity (kWh) / Maximum capacity (kWh) | Mindestkapazität (kWh) / Höchstkapazität (kWh) |

Existing labels Search, Brand, Application, Phase, Power, Sort products and the existing sort-option labels retain their catalog terms. The existing Reset translation “Reset” is corrected to “Zurücksetzen”, matching the existing “Reset filters” term. English does not change. This corrects an already observed German control-label defect, not a marketing rewrite.

Author critique: “Include context” would hide which data travels and would provide no reliable removal feedback. The explicit selection name plus unchecked status describes the actual native checkbox action. Avoid “saved”, “ready” or promises of submission before a valid native request creates the record. The unavailable wording leaves a concrete way to send the original message. Separate labels prevent customer prose from being silently extended. Labels claim neither a product match nor a sizing result.

The linker-copywriting Hard Stops were applied to these short functional labels: no generic quality claims, vague “certified”, invented quantity, permission implication, defensive marketing paragraph or new company/customer promise. The only numbers are physical units already used by the archive.

Independent Spec critique identified two issues: (1) “no longer available / nicht mehr verfügbar” could imply product stock/withdrawal or an unproven past availability; the final line instead names failure to load selection data. (2) “will not be sent” must include the native POST, not merely omit team metadata. The implementation contract was narrowed to a checkbox whose value carries the selection JSON: unchecked controls are absent from FormData, with no hidden selection JSON, while a data-free marker retains explicit exclusion after a failed submission. Canonical Contact back URLs contain no selection query. Excluded selection is absent from order metadata/team output, and never appended to message.

Final copy above is retained with those two changes. Spec gave a **copy/contract-only PASS** on 2026-10-22; it explicitly does not claim product-source, native POST, queue, browser or deployed acceptance. The source and real consumers still require the parent's separate reviews and runtime gates.
