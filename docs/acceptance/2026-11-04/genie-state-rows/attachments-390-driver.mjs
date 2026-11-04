/** Re-record `attachments-image-pdf` at 390 with a real photo and a real
 * hosted PDF, because the two 390 rows cited screenshots that never existed.
 *
 * Why they did not exist: `Recorder.record` wrapped `page.screenshot()` in
 * `try { … } catch {}` and wrote the path regardless, so a failed capture still
 * produced a passing row whose `screenshot` pointed at nothing. The recorder
 * now requires a non-empty file and records `screenshotError` instead of a
 * path when the capture fails (lib.mjs).
 *
 * This driver does not fake the attachment: it uploads one of the repo's own
 * product photos and one PDF the local instance really hosts, asks a question
 * about them, and reads back (a) the chips, (b) the turn's own HTTP status and
 * `turn_id`, (c) the answer text, and (d) that the answer names something the
 * photo/PDF actually contains. The screenshot is taken with the answer and its
 * attachment chips on screen at that width.
 */
import fs from "node:fs";
import path from "node:path";
import {
	BASE, COMBOS, ROUTES, Recorder, askTurn, check, consent, dock, evidenceFile,
	goto, newPage, openDock, chromium,
} from "./lib.mjs";

/** The repo's own nameplate sample: a real, readable type plate whose model
 * (SAJ H2-10K-T3) is in this instance's publication manifest. The GoodWe
 * battery photo next to it in eval/attachments/photos is a marketing shot that
 * the reader reports as unreadable — a legitimate product answer, but not an
 * "image + PDF" turn a customer would ask about. */
const PHOTO = path.resolve(
	process.env.GSTATES_PHOTO ??
		"../../../../docs/research/2026-10-17-deepseek-flash-vision/raw/nameplate-probe.png"
);
/** A datasheet this instance serves (HTTP 200 through the publication gate):
 * SAJ's H2 10-30K user manual, the same brand and series as the plate. The
 * H2-10-30K datasheet listed in the manifest answers 410 — withdrawn through
 * the publication gate — so it cannot stand in for a downloadable document. */
const PDF_URL =
	process.env.GSTATES_PDF_URL ??
	"http://127.0.0.1:8904/wp-content/uploads/2026/10/SAJ_H2_10-30K_User-Manual_DE-EN_EU.pdf";

const Q = {
	en: "What do these two attachments describe? Name the model and the key numbers you can read.",
	de: "Was beschreiben diese beiden Anhänge? Nennen Sie das Modell und die wichtigsten Zahlen, die Sie lesen können.",
};

const attachButton = (page) => dock(page).locator(".linker-genie-app__attach").first();
const chipCount = (page) =>
	dock(page)
		.locator(".linker-genie-app__attachment, .linker-genie-attachment, [class*=attachment-chip]")
		.count()
		.catch(() => 0);

async function runCombo(browser, combo) {
	const rec = new Recorder("genie", combo);
	const { context, page } = await newPage(browser, combo);
	const R = ROUTES[combo.lang];
	let pdfPath = null;
	const scratch = path.join("/tmp", `gstates-attach-${combo.lang}-${combo.width}`);
	try {
		fs.mkdirSync(scratch, { recursive: true });
		pdfPath = path.join(scratch, path.basename(PDF_URL.split("?")[0]));
		const reply = await page.request.get(PDF_URL);
		if (!reply.ok()) throw new Error(`hosted PDF ${PDF_URL} answered ${reply.status()}`);
		const bytes = await reply.body();
		fs.writeFileSync(pdfPath, bytes);

		await goto(page, R.genie, { wait: 3000 });
		await consent(page);
		await openDock(page);

		const attach = attachButton(page);
		const attachPresent = (await attach.count()) > 0;
		let chips = 0;
		let uploadError = null;
		if (attachPresent) {
			const [chooser] = await Promise.all([
				page.waitForEvent("filechooser", { timeout: 10000 }).catch(() => null),
				attach.click().catch(() => {}),
			]);
			if (chooser) {
				try {
					await chooser.setFiles([PHOTO, pdfPath]);
				} catch (error) {
					uploadError = String(error?.message ?? error).slice(0, 160);
				}
				await page.waitForTimeout(5000);
				chips = await chipCount(page);
			} else {
				uploadError = "no file chooser opened";
			}
		}

		// The question goes in only once the chips are there: the composer
		// refuses to send while a file is still being prepared.
		const turn = chips >= 2 ? await askTurn(page, Q[combo.lang]) : { ok: false, error: uploadError ?? "no chips" };

		// The answer must be about the attachments, not a generic reply: the
		// photo is a GoodWe battery label and the PDF is a SAJ ATS1 datasheet.
		// The plate names SAJ H2-10K-T3 and the datasheet is its own; an answer
		// that read the material names the brand and/or that model.
		const answer = (turn.text ?? "").toLowerCase();
		const mentionsAttachmentSubject = /saj|h2-10|h2 10|hybrid|datasheet|datenblatt|10\s?kw/i.test(answer);

		await rec.record(
			"attachments-image-pdf",
			[
				check("attach control present", attachPresent),
				check("the photo and the hosted PDF become two attachment chips", chips >= 2,
					`chips=${chips}${uploadError ? ` · ${uploadError}` : ""}`),
				check("the attachment turn is answered (2xx + turn_id + text)", turn.ok,
					turn.ok
						? `HTTP ${turn.httpStatus} · turn_id=${turn.turnId} · route=${turn.route ?? "n/a"} · ${turn.text.length} chars`
						: `HTTP ${turn.httpStatus ?? "none"} · ${turn.error}`),
				check("the answer is about the attached material", mentionsAttachmentSubject,
					String(turn.text ?? "").replace(/\s+/g, " ").slice(0, 120)),
				check("the hosted PDF is a real file", !!pdfPath && fs.statSync(pdfPath).size > 100000,
					pdfPath ? `${Math.round(fs.statSync(pdfPath).size / 1024)} KB · ${path.basename(pdfPath)}` : "not downloaded"),
			],
			page,
			`a real product photo (${path.basename(PHOTO)}) and a PDF this instance hosts (${path.basename(PDF_URL.split("?")[0])}) uploaded through the dock's own picker, then one real question about them on the official deepseek-flash vision/PDF channel`
		);
	} catch (e) {
		console.log("combo error (contained):", combo, String(e?.message || e).slice(0, 250));
		rec.rows.push({ key: `genie:attachments-image-pdf:${combo.lang}:${combo.width}`, error: String(e?.message || e).slice(0, 350) });
	} finally {
		if (pdfPath) fs.rmSync(path.dirname(pdfPath), { recursive: true, force: true });
		await context.close().catch(() => {});
	}
	return rec;
}

const browser = await chromium.launch({
	args: ["--disable-gpu", "--disable-dev-shm-usage", "--renderer-process-limit=1"],
});
const all = [];
for (const combo of COMBOS) all.push(await runCombo(browser, combo));
await browser.close();
const rows = all.flatMap((r) => r.rows);
fs.writeFileSync(await evidenceFile("genie-attachments-round3"), JSON.stringify({
	driver: "genie", fixRound: 3, base: BASE, observedAt: new Date().toISOString(),
	rows,
	modelBudget: "1 real vision/PDF turn per combo; the photo and the PDF are the repo's own and the instance's own hosted file",
}, null, 1));
console.log("attachments driver done:", rows.length, "records,", rows.filter((r) => r.status === "fail").length, "failed,",
	rows.filter((r) => !r.screenshot).length, "without a screenshot");
