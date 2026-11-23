import { useEffect, useRef, useState } from "react";
import { __ } from "../../i18n.ts";
import { FileDropzone } from "../FileDropzone.tsx";

export function useReportLogo(blocked: boolean, issuedLogo?: string | null) {
	const [selection, setLogo] = useState<{
			name?: string;
			data: string;
		} | null>(),
		[logoError, setLogoError] = useState(false),
		[reading, setReading] = useState(false);
	const logo =
		selection === undefined && issuedLogo
			? { data: issuedLogo, name: undefined }
			: selection;
	const reader = useRef<FileReader | null>(null);
	const logoInput = useRef<HTMLInputElement>(null);
	const resetLogo = () => {
		reader.current?.abort();
		reader.current = null;
		setLogo(null);
		setLogoError(false);
		setReading(false);
	};
	useEffect(
		() => () => {
			reader.current?.abort();
			reader.current = null;
		},
		[],
	);
	const logoField = (
		<div className="sc-report-logo">
			<div>
				<FileDropzone
					inputRef={logoInput}
					label={__("Your logo on the PDF (optional)", "linker-tools")}
					action={__("Choose logo", "linker-tools")}
					accept="image/png,image/jpeg"
					disabled={blocked}
					{...(logo?.name && { filename: logo.name })}
					onFile={(file) => {
						resetLogo();
						if (
							file.size > 500000 ||
							!["image/png", "image/jpeg"].includes(file.type)
						) {
							setLogoError(true);
							return;
						}
						const next = new FileReader();
						reader.current = next;
						setReading(true);
						next.onload = () => {
							if (reader.current === next && typeof next.result === "string") {
								setLogo({ name: file.name, data: next.result });
								setReading(false);
							}
						};
						next.onerror = () => {
							if (reader.current === next) {
								setLogoError(true);
								setReading(false);
							}
						};
						next.readAsDataURL(file);
					}}
				/>
				<small>{__("PNG or JPG, up to 500 kB.", "linker-tools")}</small>
				{logoError && (
					<small role="alert">
						{__(
							"The logo could not be used. Choose a PNG or JPG of up to 500 kB.",
							"linker-tools",
						)}
					</small>
				)}
			</div>
			{(logo || logoError || reading) && (
				<div className="sc-actions">
					{logo && (
						<img src={logo.data} alt={__("Report logo", "linker-tools")} />
					)}
					<button
						type="button"
						className="sc-button"
						disabled={blocked}
						onClick={() => {
							resetLogo();
							if (logoInput.current) {
								logoInput.current.value = "";
								logoInput.current.focus();
							}
						}}
					>
						{__("Remove logo", "linker-tools")}
					</button>
				</div>
			)}
		</div>
	);
	return { logo, logoField, logoPending: reading || logoError };
}
