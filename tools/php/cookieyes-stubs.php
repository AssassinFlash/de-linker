<?php
/** Native CookieYes 3.5.7 API signatures; static analysis only. */
// phpcs:ignoreFile -- Vendor API signatures, matching wp-cli-stubs.php.
namespace CookieYes\Lite\Includes {
    class Cache { public static function delete(string $group): void {} }
    /**
     * @method array<string, mixed> get_settings()
     * @method array<string, mixed> get_contents(string $language = '')
     * @method array<string, mixed> get_translations(string $language = '')
     * @method void set_settings(array<string, mixed> $value)
     * @method void set_contents(array<string, mixed> $value)
     * @method mixed get_name(string $language = '')
     * @method mixed get_description(string $language = '')
     * @method void set_name(mixed $value)
     * @method void set_description(mixed $value)
     * @method string get_slug()
     * @method int get_id()
     * @method bool get_visibility()
     * @method void set_visibility(bool $value)
     * @method int get_category()
     * @method string get_url_pattern()
     * @method void set_url_pattern(string $value)
     * @method void set_category(int $value)
     * @method void set_domain(string $value)
     * @method void set_duration(array<string, string> $value)
     */
    class Store {
        public function __construct(mixed $data = '') {}
        public function save(): int { return 1; }
    }
    class Base_Controller {
        public static function get_instance(): static { return new static(); }
        public function install_tables(): void {}
        /** @return \stdClass[] */
        public function get_items(): array { return []; }
    }
}
namespace CookieYes\Lite\Admin\Modules\Settings\Includes {
    class Settings {
        /** @return array<string, mixed> */
        public function get(): array { return []; }
        /** @param array<string, mixed> $settings */
        public function update(array $settings): void {}
    }
}
namespace CookieYes\Lite\Admin\Modules\Banners\Includes {
    class Banner extends \CookieYes\Lite\Includes\Store {}
    class Controller extends \CookieYes\Lite\Includes\Base_Controller {
        public function get_active_banner(): Banner|false { return false; }
    }
}
namespace CookieYes\Lite\Admin\Modules\Cookies\Includes {
    class Cookie extends \CookieYes\Lite\Includes\Store {}
    class Cookie_Categories extends \CookieYes\Lite\Includes\Store {}
    class Category_Controller extends \CookieYes\Lite\Includes\Base_Controller {}
    class Cookie_Controller extends \CookieYes\Lite\Includes\Base_Controller {}
}
