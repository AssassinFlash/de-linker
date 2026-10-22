# Internal aggregate reminder copy

Source: `Health/ReviewReminder::message()` and `Health/PendingReviews` in linker-commerce. English is the source; German and the team's existing Chinese locale are shipped in the commerce catalogs. This is internal staff notification copy, with no customer-facing sender or inquiry text change.

Draft: “Saved inquiries need staff review”, followed by saved count, age of oldest, count snapshot time and the native staff review link. It states that the inquiries are saved and their individual team notifications have not been released. It does not call customers spam, suggest the model made a rejection, or claim that a queued reminder has already reached a mailbox.

Review requested from the coordinating root: factual status wording, readability of the original notification's state, and EN/DE/Chinese language fidelity. Final ruling is recorded by that root before deployment. SMTP transport success remains a separate operational event from this rendered content.


Root review ruling: state facts, snapshot time, exclusion of customer content and avoiding a delivery claim all pass. The first draft's count sentences were revised to avoid singular/plural grammar at 1. Final count wording is “Saved inquiries awaiting staff review: %d.” / “Gespeicherte Anfragen zur manuellen Prüfung: %d.” / “已保存、待人工复核的询盘：%d。”. The reminder uses the same wording with positional placeholder %1$d, followed by oldest age, snapshot, native admin link and the still-unreleased individual notification state. Updated catalogs are submitted to root for final language readback before deployment.


Final root readback: EN/DE/Chinese count-neutral wording accepted; status facts, snapshot time and the distinction between saved records and unreleased individual notifications are approved. Root reviewed. The rendered message and digest use the same count-neutral wording for 1 and plural counts.
