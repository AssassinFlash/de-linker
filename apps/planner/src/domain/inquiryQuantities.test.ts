import assert from "node:assert/strict";
import test from "node:test";
import { changeInquiryQuantity } from "./inquiryQuantities.ts";

test("requesting a spare leaves installed equipment unchanged and undo restores the original inputs", () => {
	const inputs = {
		equipment_selection: { inverter_product_id: 42 },
		equipment_candidate: { candidate_id: "a" },
	};
	const three = changeInquiryQuantity(inputs, 42, 2, 3);
	assert.deepEqual(three, {
		...inputs,
		inquiry_quantities: { "42": { planned_purchase: 2, requested: 3 } },
	});
	const four = changeInquiryQuantity(three, 42, 3, 4);
	assert.deepEqual(four.inquiry_quantities, {
		"42": { planned_purchase: 2, requested: 4 },
	});
	assert.deepEqual(changeInquiryQuantity(four, 42, 4, 2), inputs);
});
