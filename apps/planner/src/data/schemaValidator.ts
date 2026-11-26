import Ajv, { type AnySchema, type ValidateFunction } from "ajv";
import Ajv2020 from "ajv/dist/2020.js";

let draft7: Ajv;
let draft2020: Ajv2020;

function lazyValidator<T>(compile: () => ValidateFunction<T>) {
	let compiled: ValidateFunction<T>;
	function validate(value: unknown): value is T {
		compiled ??= compile();
		const valid = compiled(value);
		validate.errors = compiled.errors;
		return valid;
	}
	validate.errors = null as ValidateFunction<T>["errors"];
	return validate;
}

export function validateSchema<T = unknown>(schema: AnySchema) {
	return lazyValidator(() =>
		(draft7 ??= new Ajv({ strict: true, strictNumbers: true })).compile<T>(
			schema,
		),
	);
}

export function validate2020<T = unknown>(schema: AnySchema) {
	return lazyValidator(() =>
		(draft2020 ??= new Ajv2020({
			strict: true,
			strictNumbers: true,
		})).compile<T>(schema),
	);
}
