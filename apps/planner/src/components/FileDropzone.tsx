import { useId, useState, type Ref } from "react";
import { __ } from "../i18n.ts";
import { Icon } from "./Icon.tsx";

interface FileDropzoneProps {
	label: string;
	action: string;
	name?: string;
	accept: string;
	filename?: string | undefined;
	disabled?: boolean;
	inputRef?: Ref<HTMLInputElement>;
	onFile: (file: File) => void;
}

export function FileDropzone({
	label,
	action,
	name,
	accept,
	filename,
	disabled,
	inputRef,
	onFile,
}: FileDropzoneProps) {
	const id = useId();
	const [dragging, setDragging] = useState(false);
	return (
		<label
			className="lk-dropzone"
			data-dragging={dragging || undefined}
			onDragOver={(event) => {
				if (!event.dataTransfer.types.includes("Files")) return;
				event.preventDefault();
				if (!event.currentTarget.control?.matches(":disabled"))
					setDragging(true);
			}}
			onDragLeave={() => setDragging(false)}
			onDrop={(event) => {
				event.preventDefault();
				setDragging(false);
				const file = event.dataTransfer.files[0];
				if (file && !event.currentTarget.control?.matches(":disabled"))
					onFile(file);
			}}
		>
			<span className="lk-dropzone-title" id={id + "-label"}>
				{label}
			</span>
			<Icon name="upload" className="lk-dropzone-icon" />
			<span
				className="lk-dropzone-description"
				id={id + "-name"}
				aria-live="polite"
			>
				{filename || __("Drop a file here", "linker-tools")}
			</span>
			<span className="lk-dropzone-action" aria-hidden="true">
				{action}
			</span>
			<input
				ref={inputRef}
				name={name}
				type="file"
				accept={accept}
				disabled={disabled}
				aria-labelledby={id + "-label"}
				aria-describedby={id + "-name"}
				onChange={(event) => {
					const file = event.currentTarget.files?.[0];
					if (file) {
						event.currentTarget.value = "";
						onFile(file);
					}
				}}
			/>
		</label>
	);
}
