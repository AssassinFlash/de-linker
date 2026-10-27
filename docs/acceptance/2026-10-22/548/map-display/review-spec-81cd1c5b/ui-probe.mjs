// Component-level DOM evidence only. Native layout and the actual 1440/390
// keyboard/rendered matrix remain with the parent; no real network is used.
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {register} from "node:module";
const rootUrl=new URL("../../../../../../",import.meta.url);
register(new URL("apps/planner/tests/map-library-loader.mjs",rootUrl));
const {default:React,act}=await import(new URL("apps/planner/node_modules/react/index.js",rootUrl));
const {setupDom,until}=await import(new URL("apps/planner/tests/dom-fixture.mjs",rootUrl));
const fixture=setupDom();
const previous={fetch:globalThis.fetch,observer:Object.getOwnPropertyDescriptor(globalThis,"MutationObserver")};
globalThis.MutationObserver=window.MutationObserver;
const calls=[];
globalThis.fetch=async(...args)=>{calls.push(args.map(String));throw new Error("Unexpected network attempt");};
const {createRoot}=await import(new URL("apps/planner/node_modules/react-dom/client.js",rootUrl));
const {ToolIdentity}=await import(new URL("apps/planner/src/components/ToolIdentity.tsx",rootUrl));
const {default:MapViewport}=await import(new URL("apps/planner/src/components/design/MapViewport.tsx",rootUrl));
const {maps}=await import(new URL("apps/planner/tests/map-library-fixture.mjs",rootUrl));
const accepted=JSON.parse(readFileSync(new URL("docs/acceptance/2026-10-22/548/map-display/system-identity-copy/copy-final.json",rootUrl)));
const original=JSON.parse(readFileSync(new URL("../review-spec-f40db1d6/probe.json",import.meta.url))).numerical_support.fixture;
const root=createRoot(fixture.element),languages=[];
try{
	for(const language of ["en","de"]){
		const dictionary=new Map(accepted.messages.map(message=>[message.en,message[language]]));
		window.wp.i18n.__=(message)=>dictionary.get(message)??message;
		await act(async()=>root.render(React.createElement("div",null,React.createElement("input",{defaultValue:"UNSAVED REVIEW INPUT","data-review-input":true}),React.createElement(ToolIdentity))));
		const details=document.querySelector("details"),input=document.querySelector("[data-review-input]");
		const beforeCalls=calls.length,beforeLocation=location.href;
		await act(async()=>details.querySelector("summary").click());
		assert.equal(details.open,true);
		assert.equal(input.value,"UNSAVED REVIEW INPUT");
		assert.equal(location.href,beforeLocation);
		assert.equal(calls.length,beforeCalls);
		const content=document.querySelector(".lp-tool-identity").textContent;
		for(const message of accepted.messages)assert.ok(content.includes(message[language]),`${language}: ${message.id}`);
		const links=[...details.querySelectorAll("a")].map(a=>({label:a.textContent,url:a.href,rel:a.rel,target:a.target}));
		assert.equal(links.length,10);
		for(const link of accepted.credit_links){
			const label=link.label??link[`label_${language}`]??accepted.messages.find(m=>m.id===link.message_id)[language];
			assert.ok(links.some(a=>a.label===label&&a.url===new URL(link.url).href),label);
		}
		assert.ok(links.every(a=>a.target==="_blank"&&a.rel.includes("noreferrer")&&a.rel.includes("noopener")));
		await act(async()=>details.querySelector("summary").click());
		assert.equal(details.open,false);
		languages.push({language,accepted_messages:accepted.messages.length,credits:links,native_details_toggle:"open/close",unsaved_input_unchanged:true,location_unchanged:true,new_fetch_calls:0});
	}
	let references=0;
	await act(async()=>root.render(React.createElement(MapViewport,{document:original,poses:[],selected:null,select(){throw new Error("No selection expected");},disabled:false,openReferences(){references++;},camera:{current:null}})));
	await until(()=>[...document.querySelectorAll("button")].some(button=>button.textContent==="Coordinate references"));
	assert.ok(document.body.textContent.includes("This geometry cannot be shown on the map."));
	assert.equal(maps.length,0,"unsupported data must not create a renderer");
	await act(async()=>[...document.querySelectorAll("button")].find(button=>button.textContent==="Coordinate references").click());
	assert.equal(references,1);
	process.stdout.write(JSON.stringify({languages,map_unsupported_fallback:{notice:true,numeric_reference_action:true,renderer_instances:maps.length},total_fetch_calls:calls.length,evidence_limit:"Component DOM only, with native map library port. Does not prove browser layout, map tiles, actual network privacy, keyboard or full project persistence."},null,2)+"\n");
}finally{
	await fixture.dispose(root);
	globalThis.fetch=previous.fetch;
	if(previous.observer)Object.defineProperty(globalThis,"MutationObserver",previous.observer);else delete globalThis.MutationObserver;
}
