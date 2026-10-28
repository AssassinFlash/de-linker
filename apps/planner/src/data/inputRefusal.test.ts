import assert from "node:assert/strict";
import test from "node:test";
import { ApiError } from "./protocol.ts";
import { isPreMutationInputRefusal } from "./inputRefusal.ts";

test("only a known input-refusal code and status release an import", () => {
	assert.equal(
		isPreMutationInputRefusal(new ApiError(422, "invalid_input")),
		true,
	);
	assert.equal(
		isPreMutationInputRefusal(
			new ApiError(422, "project_input_contract_required"),
		),
		true,
	);
	assert.equal(
		isPreMutationInputRefusal(new ApiError(413, "linker_planner_body")),
		true,
	);
	for (const status of [400, 413, 415, 422, 500]) {
		for (const code of [
			"request_failed",
			"upstream",
			"invalid_json_object",
			"invalid_reply",
			"toString",
			"constructor",
		])
			assert.equal(
				isPreMutationInputRefusal(new ApiError(status, code)),
				false,
			);
	}
	assert.equal(
		isPreMutationInputRefusal(new ApiError(500, "invalid_input")),
		false,
	);
	assert.equal(
		isPreMutationInputRefusal(new TypeError("lost response")),
		false,
	);
});
