/**
 * The cookie jar both proxy drivers use: the dock's `credentials: same-origin`
 * and the production guest, in one place.
 *
 * A cleared cookie (empty value, or an expiry of the Unix epoch) leaves the
 * jar. The proxy client used to do both; the production jar only dropped an
 * empty value. One rule now.
 */

export class CookieJar {
	constructor() {
		this.cookies = new Map();
	}

	keep(response) {
		for (const raw of response.headers?.getSetCookie?.() ?? []) {
			const [pair] = raw.split(';');
			const eq = pair.indexOf('=');
			if (eq < 0) {
				continue;
			}
			const name = pair.slice(0, eq).trim();
			const value = pair.slice(eq + 1).trim();
			if (name === '') {
				continue;
			}
			if (value === '' || /expires=Thu, 01 Jan 1970/i.test(raw)) {
				this.cookies.delete(name);
			} else {
				this.cookies.set(name, value);
			}
		}
	}

	header() {
		return [...this.cookies].map(([name, value]) => `${name}=${value}`).join('; ');
	}
}
