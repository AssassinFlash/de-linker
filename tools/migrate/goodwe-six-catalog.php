<?php
/**
 * Import the GoodWe commercial products from the owner's onboarding package.
 *
 * Run with wp eval-file goodwe-six-catalog.php /absolute/path/to/package plan|write.
 *
 * @package Linker\Migrate
 */

defined( 'ABSPATH' ) || exit;

/**
 * Read the local, read-only onboarding manifest.
 *
 * @param string $file Absolute JSON file path.
 * @return array<mixed>
 */
function linker_commerce_goodwe_six_read_manifest( string $file ): array {
	$text = file_get_contents( $file ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents -- The input is a local package file.
	if ( false === $text ) {
		WP_CLI::error( "Cannot read $file" );
	}
	return json_decode( $text, true, 512, JSON_THROW_ON_ERROR );
}

/**
 * Write product metadata in the JSON encoding used by Woo product views.
 *
 * @param int          $id Product ID.
 * @param string       $key Metadata key.
 * @param array<mixed> $value Data to encode.
 */
function linker_commerce_goodwe_six_json_meta( int $id, string $key, array $value ): void {
	update_post_meta( $id, $key, wp_slash( wp_json_encode( $value, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR ) ) );
}

/**
 * Find or import each source file and return the hosted file identities.
 *
 * @param string                    $dir Package root.
 * @param list<array<string,mixed>> $products Product manifest entries.
 * @param bool                      $write Whether to import missing attachments.
 * @return array<string,array{id:int,url:string}>
 */
function linker_commerce_goodwe_six_media( string $dir, array $products, bool $write ): array {
	global $wpdb;
	$uploads = wp_get_upload_dir();
	$files   = array();
	foreach ( linker_commerce_goodwe_six_read_manifest( "$dir/data/pdf_manifest.json" ) as $pdf ) {
		$file           = $pdf['filename'];
		$files[ $file ] = array(
			'path' => "$dir/pdfs/$file",
			'mime' => 'application/pdf',
			'sha'  => $pdf['sha256'],
		);
		$hint           = $pdf['existing_live_200_url'] ?? $pdf['retained_draft_410_url_candidate'];
		if ( $hint ) {
			$hint_path = wp_parse_url( $hint, PHP_URL_PATH );
			if ( ! is_string( $hint_path ) || ! str_starts_with( $hint_path, '/wp-content/uploads/' ) ) {
				WP_CLI::error( "Invalid uploads URL: $hint" );
			}
			$files[ $file ]['hint'] = substr( $hint_path, strlen( '/wp-content/uploads/' ) );
		}
	}
	foreach ( $products as $p ) {
		foreach ( $p['images'] as $image ) {
			$file                                 = basename( $image['local_file'] );
			$files[ $file ]['path']               = $dir . '/' . $image['local_file'];
			$files[ $file ]['mime']               = 'image/png';
			$files[ $file ]['alt'][ $p['model'] ] = $image['alt_en'];
		}
	}
	$wanted = array();
	foreach ( $files as $file => &$row ) {
		if ( ! is_readable( $row['path'] ) ) {
			WP_CLI::error( "Missing source $file" );
		}
		$sha = hash_file( 'sha256', $row['path'] );
		if ( isset( $row['sha'] ) && $row['sha'] !== $sha ) {
			WP_CLI::error( "PDF differs from manifest: $file" );
		}
		$wanted[ filesize( $row['path'] ) ][ $sha ] = $file;
		$row['sha']                                 = $sha;
	}
	unset( $row );
	$attachments = $wpdb->get_results( "SELECT p.ID, m.meta_value AS path FROM $wpdb->posts p JOIN $wpdb->postmeta m ON p.ID=m.post_id AND m.meta_key='_wp_attached_file' WHERE p.post_type='attachment' AND p.post_status='inherit' AND p.post_mime_type IN ('application/pdf','image/png') ORDER BY p.ID" );
	$ids_by_path = array();
	foreach ( $attachments as $attachment ) {
		$relative = $attachment->path;
		if ( ! preg_match( '#^\d{4}/\d{2}/[^/]+$#D', $relative ) ) {
			continue;
		}
		$id                       = (int) $attachment->ID;
		$ids_by_path[ $relative ] = $id;
		$path                     = $uploads['basedir'] . '/' . $relative;
		$size                     = is_file( $path ) ? filesize( $path ) : 0;
		if ( ! isset( $wanted[ $size ] ) ) {
			continue;
		}
		$name = $wanted[ $size ][ hash_file( 'sha256', $path ) ] ?? '';
		if ( isset( $files[ $name ] ) && ( ! isset( $files[ $name ]['relative'] ) || ( $files[ $name ]['hint'] ?? '' ) === $relative ) ) {
			$files[ $name ]['relative'] = $relative;
		}
	}
	$result = array();
	require_once ABSPATH . 'wp-admin/includes/image.php';
	foreach ( $files as $file => $row ) {
		$hint = $row['hint'] ?? '';
		$rel  = $row['relative'] ?? '';
		// Some hosted originals have a Woo relation and bytes but no attachment.
		if ( $hint && is_file( $uploads['basedir'] . '/' . $hint ) && hash_file( 'sha256', $uploads['basedir'] . '/' . $hint ) === $row['sha'] ) {
			$rel = $hint;
		}
		$id = $ids_by_path[ $rel ] ?? 0;
		if ( $id && '0' === get_post_meta( $id, '_linker_document_public', true ) ) {
			WP_CLI::error( "Attachment $id was explicitly withdrawn: $file" );
		}
		if ( $write && ! $id ) {
			if ( '' === $rel ) {
				$dest = wp_upload_dir();
				if ( $dest['error'] ) {
					WP_CLI::error( $dest['error'] );
				}
				$filename = sanitize_file_name( $file );
				$path     = $dest['path'] . '/' . $filename;
				if ( ! is_file( $path ) || hash_file( 'sha256', $path ) !== $row['sha'] ) {
					$filename = wp_unique_filename( $dest['path'], $filename );
					$path     = $dest['path'] . '/' . $filename;
					if ( ! copy( $row['path'], $path ) ) {
						WP_CLI::error( "Could not copy $file to uploads" );
					}
				}
				$rel = ltrim( $dest['subdir'] . '/' . $filename, '/' );
			}
			$path = $uploads['basedir'] . '/' . $rel;
			$id   = wp_insert_attachment(
				array(
					'post_mime_type' => $row['mime'],
					'post_title'     => pathinfo( $file, PATHINFO_FILENAME ),
					'post_status'    => 'inherit',
					'guid'           => $uploads['baseurl'] . '/' . $rel,
				),
				$path,
				0,
				true
			);
			if ( is_wp_error( $id ) ) {
				WP_CLI::error( $id->get_error_message() );
			}
			if ( 'image/png' === $row['mime'] ) {
				wp_update_attachment_metadata( $id, wp_generate_attachment_metadata( $id, $path ) );
			}
		}
		if ( $write && isset( $row['alt'] ) ) {
			$model = array_key_first( $row['alt'] );
			$alt   = $row['alt'][ $model ];
			if ( count( $row['alt'] ) > 1 ) {
				$alt = str_contains( $file, 'lynx-c' )
					? str_replace( array( $model . ' Lynx C series', $model ), array( 'Lynx C series', 'Lynx C' ), $alt )
					: preg_replace( '/GW100K-HT(?: 100 kW)?/', 'HT 100–120 kW', $alt );
			}
			update_post_meta( $id, '_wp_attachment_image_alt', $alt );
		}
		$result[ $file ] = array(
			'id'  => (int) $id,
			'url' => $rel ? $uploads['baseurl'] . '/' . $rel : '',
		);
	}
	return $result;
}

/**
 * Resolve the English term or create a shared brand or model-line term.
 *
 * @param string $taxonomy Woo taxonomy.
 * @param string $name Term name or slug.
 * @param bool   $create Whether to create a missing term.
 * @return int
 */
function linker_commerce_goodwe_six_term( string $taxonomy, string $name, bool $create ): int {
	$terms = get_terms(
		array(
			'taxonomy'   => $taxonomy,
			'slug'       => sanitize_title( $name ),
			'hide_empty' => false,
			'lang'       => '',
		)
	);
	if ( is_wp_error( $terms ) ) {
		WP_CLI::error( $terms->get_error_message() );
	}
	foreach ( $terms as $term ) {
		if ( ! pll_is_translated_taxonomy( $taxonomy ) || 'en' === pll_get_term_language( $term->term_id ) ) {
			return (int) $term->term_id;
		}
	}
	if ( ! $create || pll_is_translated_taxonomy( $taxonomy ) ) {
		WP_CLI::error( "Missing English $taxonomy term: $name" );
	}
	$term = wp_insert_term( $name, $taxonomy );
	if ( is_wp_error( $term ) ) {
		WP_CLI::error( $term->get_error_message() );
	}
	return (int) $term['term_id'];
}

/**
 * Apply the supplied terms while preserving unrelated product attributes.
 *
 * @param WC_Product                $en English product.
 * @param array<string,string|null> $values Attribute values by taxonomy.
 * @return array<string,WC_Product_Attribute>
 */
function linker_commerce_goodwe_six_attributes( WC_Product $en, array $values ): array {
	$attributes = $en->get_attributes( 'edit' );
	foreach ( $values as $taxonomy => $name ) {
		if ( null === $name ) {
			unset( $attributes[ $taxonomy ] );
			continue;
		}
		$term      = linker_commerce_goodwe_six_term( $taxonomy, $name, true );
		$attribute = $attributes[ $taxonomy ] ?? new WC_Product_Attribute();
		$attribute->set_id( wc_attribute_taxonomy_id_by_name( $taxonomy ) );
		$attribute->set_name( $taxonomy );
		$attribute->set_options( array( $term ) );
		$attribute->set_visible( true );
		if ( ! isset( $attributes[ $taxonomy ] ) ) {
			$attribute->set_position( count( $attributes ) );
		}
		$attributes[ $taxonomy ] = $attribute;
	}
	return $attributes;
}

/**
 * Build the product detail table from its approved technical figures.
 *
 * @param array<string,array<string,mixed>> $figures Figures with bilingual values and qualifiers.
 * @param string                            $lang Language code.
 * @return list<array<string,mixed>>
 */
function linker_commerce_goodwe_six_specs( array $figures, string $lang ): array {
	$labels = <<<'LABELS'
#Battery|Batterie
system_usable_energy_kwh|Usable energy|Nutzbare Energie
system_nominal_voltage_v|Nominal system voltage|Systemnennspannung
system_operating_voltage_range_v|Operating voltage range|Betriebsspannungsbereich
nominal_charge_discharge_power_kw|Rated charge/discharge power|Nennlade- und Nennentladeleistung
nominal_charge_discharge_current_a|Rated charge/discharge current|Nennlade- und Nennentladestrom
pack_model|Battery module|Batteriemodul
modules_per_stack_max|Modules per cabinet|Module je Schrank
module_energy_kwh_nominal|Nominal energy per module|Nennenergie je Modul
module_voltage_v_nominal|Nominal voltage per module|Nennspannung je Modul
pack_configuration|Cell configuration|Zellkonfiguration
chemistry|Cell chemistry|Zellchemie
stacks_parallel_max|Maximum number of parallel cabinets|Maximale Anzahl parallel geschalteter Schränke
usable_energy_test_dod_pct|Depth of discharge for usable energy measurement|Entladetiefe bei der Messung der nutzbaren Energie
usable_energy_test_c_rate|Charge/discharge rate for usable energy measurement|Lade- und Entladerate bei der Messung der nutzbaren Energie
cycle_life|Cell cycle life|Zyklenlebensdauer der Zellen
round_trip_efficiency|Round-trip efficiency|Zykluswirkungsgrad
nominal_battery_voltage_v|Nominal battery voltage|Batterienennspannung
battery_voltage_range_v|Battery voltage range|Batteriespannungsbereich
max_battery_charge_power_kw|Maximum charging power|Maximale Ladeleistung
max_battery_discharge_power_kw|Maximum discharging power|Maximale Entladeleistung
max_battery_charge_a|Maximum charge current|Maximaler Ladestrom
max_battery_discharge_a|Maximum discharge current|Maximaler Entladestrom
bms_comms|BMS communication|BMS-Kommunikation
#PV input|PV-Eingang
max_pv_input_power_w|Maximum PV input power|Maximale PV-Eingangsleistung
max_pv_input_v|Maximum input voltage|Maximale Eingangsspannung
nominal_pv_input_v|Nominal input voltage|Nenneingangsspannung
start_voltage_v|Start voltage|Startspannung
mppt_voltage_range_v|MPPT voltage range|MPPT-Spannungsbereich
mppt_full_load_voltage_range_v|MPPT voltage range at rated output|MPPT-Spannungsbereich bei Nennleistung
n_mppt|Number of MPPTs|Anzahl der MPP-Tracker
strings_per_mppt|Strings per MPPT|Strings je MPP-Tracker
max_input_current_per_mppt_a|Maximum input current per MPPT|Maximaler Eingangsstrom je MPP-Tracker
max_isc_per_mppt_a|Maximum short-circuit current per MPPT|Maximaler Kurzschlussstrom je MPP-Tracker
pv_standby_input_voltage_v|PV standby voltage range|PV-Spannungsbereich im Bereitschaftsbetrieb
#AC output|AC-Ausgang
ac_output_kw_nominal|Rated active power|Nennwirkleistung
ac_output_kw_max|Maximum active power|Maximale Wirkleistung
nominal_apparent_power_kva|Rated apparent power|Nennscheinleistung
max_apparent_power_kva|Maximum apparent power|Maximale Scheinleistung
nominal_ac_output_current_a|Rated output current|Nennausgangsstrom
max_ac_output_current_a|Maximum output current|Maximaler Ausgangsstrom
phases|Grid connection|Netzanschluss
backup_power_kw|Rated backup apparent power|Nennscheinleistung im Ersatzstrombetrieb
ups_switchover_ms|Backup transfer time|Umschaltzeit im Ersatzstrombetrieb
max_efficiency_pct|Maximum efficiency|Maximaler Wirkungsgrad
euro_efficiency_pct|European efficiency|Europäischer Wirkungsgrad
battery_to_ac_efficiency_pct|Battery-to-AC efficiency|Wirkungsgrad Batterie zu AC
#Installation and operation|Installation und Betrieb
dimensions_mm|Dimensions (W × H × D)|Abmessungen (B × H × T)
weight_kg|Weight|Gewicht
mounting_method|Installation|Aufstellung
ip_rating|Ingress protection rating|Schutzart
operating_temp_c|Operating temperature|Betriebstemperatur
relative_humidity_pct|Relative humidity|Relative Luftfeuchte
max_operating_altitude_m|Maximum operating altitude|Maximale Betriebshöhe
topology|Topology|Topologie
cooling|Cooling|Kühlung
comms|Communication interfaces|Kommunikationsschnittstellen
parallel_operation|Parallel operation|Parallelbetrieb
night_consumption_w|Night-time power consumption|Eigenverbrauch bei Nacht
LABELS;
	$groups = array();
	$i      = 'de' === $lang ? 1 : 0;
	$title  = '';
	foreach ( explode( "\n", $labels ) as $line ) {
		if ( str_starts_with( $line, '#' ) ) {
			$title = explode( '|', substr( $line, 1 ) )[ $i ];
			continue;
		}
		$fields = explode( '|', $line );
		$key    = $fields[0];
		if ( ! isset( $figures[ $key ] ) ) {
			continue;
		}
		$v    = $figures[ $key ];
		$unit = $v['unit'] ?? '';
		if ( in_array( $unit, array( 'pcs', 'cabinets' ), true ) ) {
			$unit = '';
		} elseif ( $i && 'cycles' === $unit ) {
			$unit = 'Zyklen';
		}
		$groups[ $title ]['spec_group_title'] = $title;
		$groups[ $title ]['spec_rows'][]      = array(
			'spec_label' => $fields[ 1 + $i ],
			'spec_value' => $i ? ( $v['value_de'] ?? $v['value'] ) : $v['value'],
			'spec_note'  => $v['qualifier'][ $lang ] ?? '',
			'spec_unit'  => $unit,
		);
	}
	return array_values( $groups );
}

/**
 * Load the six products and map the approved publication details.
 *
 * @param string $dir Package root.
 * @return list<array<string,mixed>>
 */
function linker_commerce_goodwe_six_inputs( string $dir ): array {
	$rows    = linker_commerce_goodwe_six_read_manifest( "$dir/data/products_onboarding_manifest.json" )['products'];
	$et      = array_column( $rows, null, 'model' )['GW50K-ET-10'];
	$manuals = array_filter( $et['_linker_documents'], static fn( $d ) => str_contains( $d['local_file'], 'Commercial-Smart-Inverter-Solutions' ) );
	foreach ( $rows as &$p ) {
		if ( 'battery-systems' === $p['device_class'] ) {
			$p['_tv_b2b_figures']['sales_unit_kind']['value']        = 'battery_system';
			$p['_tv_b2b_figures']['stacks_parallel_max']['unit']     = 'pcs';
			$p['_tv_b2b_figures']['stacks_parallel_max']['citation'] = array(
				'doc'  => 'GW_Lynx_C_User_Manual-EN.pdf',
				'page' => 23,
			);
			$p['_tv_b2b_figures']['usable_energy_test_c_rate']       = $p['_tv_b2b_figures']['c_rate'];
			$p['_tv_b2b_figures']['usable_energy_test_dod_pct']      = $p['_tv_b2b_figures']['dod_pct'];
			unset( $p['_tv_b2b_figures']['c_rate'], $p['_tv_b2b_figures']['dod_pct'] );
			$p['_tv_b2b_figures']['round_trip_efficiency']['qualifier'] = array(
				'en' => 'Measured at the beginning of battery life at 100% depth of discharge, with charging and discharging at 0.2C and 25 ± 2 °C.',
				'de' => 'Gemessen zu Beginn der Batterielebensdauer bei 100 % Entladetiefe, einer Lade- und Entladerate von 0,2C und 25 ± 2 °C.',
			);
			$p['_tv_b2b_figures']['system_voltage_v_nominal']           = $p['_tv_b2b_figures']['system_nominal_voltage_v'];
			$p['_linker_documents']                                     = array_merge( $p['_linker_documents'], $manuals );
			$p['short_description_en']                                  = str_replace( array( 'grounded floor mounting', 'up to 3 cabinets in parallel' ), array( 'floor-mounted', 'up to 3 identical cabinets in parallel at initial installation' ), $p['short_description_en'] );
			$p['short_description_de']                                  = str_replace( 'bis zu 3 Schränke parallel', 'bei Erstinstallation bis zu 3 baugleiche Schränke parallel', $p['short_description_de'] );
		}
		if ( str_ends_with( $p['model'], '-HT' ) ) {
			$p['short_description_en'] .= "\n" . '<p class="product-image-note">The third image shows the optional LCD version.</p>';
			$p['short_description_de'] .= "\n" . '<p class="product-image-note">Die dritte Abbildung zeigt die Ausführung mit optionalem LCD.</p>';
		}
		foreach ( $p['_linker_documents'] as &$document ) {
			if ( 'pdfs/GW_HT_1100V_Certificate-NC_RFG.pdf' === $document['local_file'] ) {
				$document['title']    = 'GoodWe HT — Poland, NC RfG equipment certificate (types A–D, PTPiREE / PSE), DNV TC-GCC-DNVGL-SE-0124-07790-1';
				$document['title_de'] = 'GoodWe HT – Polen, NC-RfG-Gerätezertifikat (Typ A bis D, PTPiREE / PSE), DNV TC-GCC-DNVGL-SE-0124-07790-1';
			} elseif ( 'pdfs/GW_HT_1100V_Certificate-VDE-AR-N_4110.pdf' === $document['local_file'] ) {
				$document['title']    = 'GoodWe HT — Germany, VDE-AR-N 4110 medium-voltage unit certificate, SGS CEBEC 2621/0136-CER';
				$document['title_de'] = 'GoodWe HT – Deutschland, Einheitenzertifikat für Mittelspannung nach VDE-AR-N 4110, SGS CEBEC 2621/0136-CER';
			}
		}
		unset( $document );
		if ( 'GW50K-ET-10' === $p['model'] ) {
			$p['_tv_b2b_figures']['ups_switchover_ms']['qualifier'] = array(
				'en' => 'With an external STS cabinet and a backup load below the inverter’s 50 kW rated power.',
				'de' => 'Mit externem STS-Umschaltschrank und einer Ersatzstromlast unter der Wechselrichter-Nennleistung von 50 kW.',
			);
			$p['short_description_en']                              = str_replace( 'an external GoodWe STS cabinet', 'the external GoodWe STS200-80-10 transfer switch', $p['short_description_en'] );
			$p['short_description_de']                              = str_replace( 'einen externen GoodWe-STS-Umschaltschrank', 'den externen GoodWe-Umschaltschrank STS200-80-10', $p['short_description_de'] );
			$p['_tv_b2b_figures']['topology']                       = array(
				'value'    => 'Non-isolated',
				'value_de' => 'Trafolos',
				'unit'     => '',
				'citation' => array(
					'doc'  => 'GW_ET40-50kW_Datasheet_EMEA-EN.pdf',
					'page' => 2,
				),
			);
		}
	}
	return $rows;
}

/**
 * Resolve a canonical SKU and its existing German translation.
 *
 * @param array<string,mixed> $p Product manifest entry.
 * @return array{en:int,de:int,slug:string}
 */
function linker_commerce_goodwe_six_pair( array $p ): array {
	global $wpdb;
	$en       = (int) wc_get_product_id_by_sku( $p['sku'] );
	$retained = (int) ( $p['retained_woo_draft_id'] ?? 0 );
	if ( $retained && $retained !== $en ) {
		WP_CLI::error( "Retained ID and SKU disagree: {$p['sku']} (ID $en, expected $retained)" );
	}
	if ( $en && ( 'en' !== pll_get_post_language( $en ) || get_post_meta( $en, '_sku', true ) !== $p['sku'] ) ) {
		WP_CLI::error( "Invalid English SKU owner: {$p['sku']}" );
	}
	$de      = $en ? (int) pll_get_post( $en, 'de' ) : 0;
	$holders = $wpdb->get_col( $wpdb->prepare( "SELECT ID FROM $wpdb->posts WHERE post_type='product' AND post_name=%s", $p['slug_en'] ) );
	foreach ( $holders as $id ) {
		if ( ! in_array( (int) $id, array( $en, $de ), true ) ) {
			WP_CLI::error( "Product $id already has slug {$p['slug_en']}" );
		}
	}
	return array(
		'en'   => $en,
		'de'   => $de,
		'slug' => $p['slug_en'],
	);
}

/**
 * Create an English or German draft for the supplied model.
 *
 * @param array<string,mixed> $p Product manifest entry.
 * @param string              $lang Language code.
 * @return int
 */
function linker_commerce_goodwe_six_new( array $p, string $lang ): int {
	$product = new WC_Product_Simple();
	$product->set_name( $p[ 'name_' . $lang ] );
	$product->set_slug( $p[ 'slug_' . $lang ] );
	$product->set_status( 'draft' );
	if ( 'en' === $lang ) {
		$product->set_sku( $p['sku'] );
		$product->set_manage_stock( false );
		$product->set_stock_status( 'instock' );
	}
	$id = $product->save();
	pll_set_post_language( $id, $lang );
	return $id;
}

/**
 * Update the retained gallery and feature references to the current product image.
 *
 * @param int $id Canonical product ID.
 * @param int $featured Current featured attachment ID.
 */
function linker_commerce_goodwe_six_gallery( int $id, int $featured ): void {
	foreach ( array( '_tv_legacy_acf_json', '_linker_de_acf_json' ) as $key ) {
		$raw = get_post_meta( $id, $key, true );
		if ( ! $raw ) {
			continue;
		}
		$acf = json_decode( $raw, true, 512, JSON_THROW_ON_ERROR );
		// Existing hero cards and gallery rows reference the superseded product image.
		$old = array_column( $acf['product_gallery'] ?? array(), 'gallery_image' );
		foreach ( array(
			'product_gallery'       => 'gallery_image',
			'feature_cards'         => 'feature_image',
			'application_scenarios' => 'scenario_image',
		) as $list => $field ) {
			foreach ( $acf[ $list ] ?? array() as $idx => $entry ) {
				if ( isset( $entry[ $field ] ) && in_array( $entry[ $field ], $old, true ) ) {
					$acf[ $list ][ $idx ][ $field ] = $featured;
				}
			}
		}
		linker_commerce_goodwe_six_json_meta( $id, $key, $acf );
	}
}

/**
 * Publish the catalog records for one English and German product pair.
 *
 * @param array<string,mixed>                    $p Product manifest entry.
 * @param array{en:int,de:int,slug:string}       $pair Existing product IDs and slug.
 * @param array<string,array{id:int,url:string}> $media Hosted attachments by package filename.
 * @return array{en:int,de:int,slug:string}
 */
function linker_commerce_goodwe_six_write_product( array $p, array $pair, array $media ): array {
	$en = $pair['en'] ? $pair['en'] : linker_commerce_goodwe_six_new( $p, 'en' );
	$de = $pair['de'] ? $pair['de'] : linker_commerce_goodwe_six_new( $p, 'de' );
	if ( ! $pair['de'] ) {
		pll_save_post_translations(
			array(
				'en' => $en,
				'de' => $de,
			)
		);
	}
	$src = wc_get_product( $en );
	$dst = wc_get_product( $de );
	if ( ! $src instanceof WC_Product || ! $dst instanceof WC_Product ) {
		WP_CLI::error( "Cannot load Woo products $en and $de" );
	}
	$brand       = linker_commerce_goodwe_six_term( 'product_brand', $p['brand'], false );
	$category    = linker_commerce_goodwe_six_term( 'product_cat', $p['woo_category_slug'], false );
	$category_de = (int) pll_get_term( $category, 'de' );
	if ( ! $category_de ) {
		WP_CLI::error( "Missing DE category for {$p['woo_category_slug']}" );
	}
	$gallery = array();
	foreach ( $p['images'] as $image ) {
		$id = $media[ basename( $image['local_file'] ) ]['id'];
		if ( 'featured' === $image['role'] ) {
			$src->set_image_id( $id );
		} else {
			$gallery[] = $id;
		}
	}
	$src->set_gallery_image_ids( $gallery );
	$src->set_attributes( linker_commerce_goodwe_six_attributes( $src, $p['attributes'] ) );
	$src->set_category_ids( array( $category ) );
	$docs = array();
	foreach ( $p['_linker_documents'] as $doc ) {
		$docs[] = array(
			'url'   => $media[ basename( $doc['local_file'] ) ]['url'],
			'title' => $doc['title'],
			'type'  => $doc['type'],
			'lang'  => $doc['lang'],
		);
	}
	if ( 'GW50K-ET-10' === $p['model'] ) {
		// The retained March edition and the current October edition are separate documents.
		$uploads  = wp_get_upload_dir();
		$relative = '2026/09/GW_Commercial-Smart-Inverter-Solutions_User-Manual-ET25-50kW-EN.pdf';
		$path     = $uploads['basedir'] . '/' . $relative;
		if ( ! is_readable( $path ) || '6d8712bf43813aff0999e7c91c4f3894c9c08835df872b6b6838c5d5d684b3e8' !== hash_file( 'sha256', $path ) ) {
			WP_CLI::error( 'Cannot identify the retained GoodWe ET solutions manual V2.4.' );
		}
		$docs[] = array(
			'url'   => $uploads['baseurl'] . '/' . $relative,
			'title' => 'GoodWe ET 25–50 kW Commercial and Industrial Smart Inverter Solutions Manual (EN, V2.4, 30 March 2026)',
			'type'  => 'manual',
			'lang'  => 'en',
		);
	}
	$figures = $p['_tv_b2b_figures'];
	foreach ( $figures as &$figure ) {
		$figure['citation']['url'] = $media[ $figure['citation']['doc'] ]['url'];
	}
	unset( $figure );
	linker_commerce_goodwe_six_json_meta( $en, '_linker_documents', $docs );
	update_post_meta( $en, '_linker_documents_managed', '1' );
	linker_commerce_goodwe_six_json_meta( $en, '_tv_b2b_figures', $figures );
	linker_commerce_goodwe_six_gallery( $en, (int) $src->get_image_id( 'edit' ) );
	foreach ( array(
		'en' => $en,
		'de' => $de,
	) as $lang => $id ) {
		if ( in_array( $p['model'], array( 'GW100K-HT', 'GW120K-HT' ), true ) ) {
			update_post_meta( $id, '_delinker_type', 'inverter' );
		}
		$terms = wp_set_object_terms( $id, array( $brand ), 'product_brand' );
		if ( is_wp_error( $terms ) ) {
			WP_CLI::error( $terms->get_error_message() );
		}
		linker_commerce_goodwe_six_json_meta( $id, 'linker_specs', linker_commerce_goodwe_six_specs( $figures, $lang ) );
		$product = 'en' === $lang ? $src : $dst;
		$product->set_name( $p[ 'name_' . $lang ] );
		$product->set_short_description( $p[ 'short_description_' . $lang ] );
		$product->set_slug( $p[ 'slug_' . $lang ] );
		if ( 'de' === $lang ) {
			$product->set_category_ids( array( $category_de ) );
		}
		$product->set_status( 'publish' );
		$product->save();
		if ( get_post_field( 'post_name', $id ) !== $p[ 'slug_' . $lang ] || get_post_status( $id ) !== 'publish' ) {
			WP_CLI::error( "Incorrect $lang publication for {$p['sku']} at $id" );
		}
	}
	return array(
		'en'   => $en,
		'de'   => $de,
		'slug' => $p['slug_en'],
	);
}

( static function ( array $args ): void {
	if ( 2 !== count( $args ) || ! in_array( $args[1], array( 'plan', 'write' ), true ) ) {
		WP_CLI::error( 'Use: wp eval-file goodwe-six-catalog.php /path/to/package plan|write' );
	}
	$products = linker_commerce_goodwe_six_inputs( $args[0] );
	$pairs    = array();
	foreach ( $products as $product ) {
		$pairs[ $product['sku'] ] = linker_commerce_goodwe_six_pair( $product );
	}
	$write = 'write' === $args[1];
	$media = linker_commerce_goodwe_six_media( $args[0], $products, $write );
	if ( $write ) {
		$titles_de = array();
		foreach ( $products as $product ) {
			$sku           = $product['sku'];
			$pairs[ $sku ] = linker_commerce_goodwe_six_write_product( $product, $pairs[ $sku ], $media );
			$titles_de    += array_filter( array_column( $product['_linker_documents'], 'title_de', 'title' ) );
		}
		$titles_option = \Linker\Commerce\Products\Materials::DE_DOCUMENT_TITLES;
		update_option( $titles_option, get_option( $titles_option, array() ) + $titles_de );
	}
	WP_CLI::log(
		'GOODWE_CATALOG=' . wp_json_encode(
			array(
				'products' => $pairs,
				'media'    => $media,
			),
			JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR
		)
	);
} )( $args ?? array() );
