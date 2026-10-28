import React, { useEffect } from "react";
export const failures = [];
export function Canvas({ gl }) {
	useEffect(() => {
		const canvas = document.createElement("canvas");
		canvas.getContext = () => null;
		Promise.resolve(gl({ canvas })).catch((error) => failures.push(error));
	}, []);
	return React.createElement("div", { "data-test-canvas": "" });
}
export function useThree() {
	throw new Error("scene children must not mount");
}
