import assert from "node:assert/strict";
import test from "node:test";
import React, { act, useState, useRef } from "react";
import flat from "../../../fixtures/planning/geometry-flat.json" with { type: "json" };
import { setupDom, until, enter, deferred } from "./dom-fixture.mjs";
import {
	applyGeometryCommand,
	emptyGeometry,
} from "../src/domain/geometryCommands.ts";
import { moduleSummary } from "../src/domain/panelPoses.ts";

function button(text) {
	const result = [...document.querySelectorAll("button")].find(
		(element) => element.textContent.trim() === text,
	);
	assert.ok(result, `Missing ${text}`);
	return result;
}
async function click(text) {
	await act(async () => button(text).click());
}

async function mount(
	t,
	{
		initial = emptyGeometry(),
		locale = "en-GB",
		query = async () => {
			throw new Error("No request expected");
		},
	} = {},
) {
	const fixture = setupDom();
	const { createRoot } = await import("react-dom/client");
	const { DesignEditor } =
		await import("../src/components/design/DesignEditor.tsx");
	const root = createRoot(fixture.element);
	let current = initial,
		edits = 0,
		valid = true;
	function Harness() {
		const [geometry, setGeometry] = useState(initial),
			[allowed, setAllowed] = useState(true);
		valid = allowed;
		const latest = useRef(initial);
		return React.createElement(DesignEditor, {
			geometry,
			locale,
			projectId: "1".repeat(32),
			session: { query_scope: "2".repeat(64) },
			client: { query, isCurrentScope: () => true },
			recheck() {
				throw new Error("No recheck expected");
			},
			onValidity: setAllowed,
			commit(command) {
				try {
					current = applyGeometryCommand(latest.current, command);
					latest.current = current;
					edits++;
					setGeometry(current);
					return true;
				} catch {
					return false;
				}
			},
		});
	}
	t.after(() => fixture.dispose(root));
	await act(async () =>
		root.render(
			React.createElement(React.StrictMode, null, React.createElement(Harness)),
		),
	);
	return {
		get current() {
			return current;
		},
		get edits() {
			return edits;
		},
		get valid() {
			return valid;
		},
	};
}


test("independent rejected 3D chunk probe", async(t)=>{
 await mount(t,{initial:flat});
 await click(flat.arrays[0].name); await click("Edit numeric properties"); await enter(document.querySelector('[name="rows"]'),"2.5");
 const stagedBefore=document.querySelector('[name="rows"]').value;
 let rejection=null;
 try { await click("3D"); await act(async()=>new Promise(r=>setTimeout(r,25))); }catch(e){rejection=e.message;}
 console.log(JSON.stringify({case:"rejected_lazy_3d_chunk_with_staged_raw",stagedBefore,rejection,remainingText:document.body.textContent,remainingInputs:document.querySelectorAll("input,button").length}));
 assert.equal(document.querySelector(".lp-design-section"),null);
});
