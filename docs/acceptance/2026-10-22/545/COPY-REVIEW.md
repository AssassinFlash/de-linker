# Internal aggregate reminder copy

Source: `Health/ReviewReminder::message()` and `Health/PendingReviews` in linker-commerce. English is the source; German and the team's existing Chinese locale are shipped in the commerce catalogs. This is internal staff notification copy, with no customer-facing sender or inquiry text change.

Draft: “Saved inquiries need staff review”, followed by saved count, age of oldest, count snapshot time and the native staff review link. It states that the inquiries are saved and their individual team notifications have not been released. It does not call customers spam, suggest the model made a rejection, or claim that a queued reminder has already reached a mailbox.

Review requested from the coordinating root: factual status wording, readability of the original notification's state, and EN/DE/Chinese language fidelity. Final ruling is recorded by that root before deployment. SMTP transport success remains a separate operational event from this rendered content.
