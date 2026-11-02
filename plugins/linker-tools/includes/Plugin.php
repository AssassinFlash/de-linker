<?php
/**
 * Plugin bootstrap.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools;

use Linker\Tools\Configurator\EngineProxy;
use Linker\Tools\Configurator\Mount;
use Linker\Tools\Genie\ConversationMail;
use Linker\Tools\Genie\ContactRequest;
use Linker\Tools\Genie\Conversations;
use Linker\Tools\Genie\Entries;
use Linker\Tools\Genie\Hero;
use Linker\Tools\Genie\InquiryRequest;
use Linker\Tools\Genie\InquirySummary;
use Linker\Tools\Genie\PageCache;
use Linker\Tools\Genie\PageIndexing;
use Linker\Tools\Genie\Preview;
use Linker\Tools\Genie\Proxy;
use Linker\Tools\Genie\QualityPage;
use Linker\Tools\Genie\QualityRoute;
use Linker\Tools\Genie\QualityStore;
use Linker\Tools\Genie\Retention;
use Linker\Tools\Genie\UserContext;
use Linker\Tools\Genie\WindPress;

/**
 * Hooks Linker Tools into WordPress.
 */
final class Plugin {

	/**
	 * Sets up the plugin.
	 *
	 * @param Assets                    $assets        Registers the built apps as scripts.
	 * @param Redirects                 $redirects     Retires the tool entry addresses that moved.
	 * @param SiteChrome                $site_chrome   The chrome's scripts (menu images, hover).
	 * @param Conversations             $conversations Conversation posts for Genie.
	 * @param Proxy                     $proxy         REST proxy to the Genie service.
	 * @param Entries                   $entries       Chips, dock and disclosure.
	 * @param Retention                 $retention     Deletes expired guest conversations.
	 * @param UserContext               $user_context  The customer-identity seam.
	 * @param WindPress                 $windpress     Scan provider for the entries' Tailwind classes.
	 * @param Mount                     $mount         The Solution Configurator's mount point.
	 * @param EngineProxy               $engine_proxy  The same-origin route to the sizing engine.
	 * @param QualityStore              $quality       The quality check's verdicts and the digest's summary.
	 * @param QualityRoute              $quality_route The route the quality worker reports to.
	 * @param QualityPage               $quality_page  The quality check's admin page.
	 * @param Preview                   $preview       Genie's preview card (ticket #249).
	 * @param ConversationMail          $mail        "Email me this conversation" and its confirmation link (ticket #235).
	 * @param ContactRequest            $contact       "Let Linker contact me": the contact card's route (#243).
	 * @param InquirySummary            $inquiry       The conversation summary an inquiry carries (#244).
	 * @param InquiryRequest            $inquiry_card  The inquiry confirmation card's route (#250).
	 * @param Hero                      $hero          The home hero's Genie entry (#232).
	 * @param PageCache                 $page_cache    Drops Genie's cached copy of a page when it is saved (#405).
	 * @param PageIndexing              $page_indexing Keeps the workspace page out of the index and its sitemap.
	 * @param Protection\Resources      $resources Public resource admission.
	 * @param Protection\ProviderBudget $provider_budget Private provider transport seam.
	 */
	public function __construct(
		private readonly Assets $assets,
		private readonly Redirects $redirects,
		private readonly SiteChrome $site_chrome,
		private readonly Conversations $conversations,
		private readonly Proxy $proxy,
		private readonly Entries $entries,
		private readonly Retention $retention,
		private readonly UserContext $user_context,
		private readonly WindPress $windpress,
		private readonly Mount $mount,
		private readonly EngineProxy $engine_proxy,
		private readonly QualityStore $quality,
		private readonly QualityRoute $quality_route,
		private readonly QualityPage $quality_page,
		private readonly Preview $preview,
		private readonly ConversationMail $mail,
		private readonly ContactRequest $contact,
		private readonly InquirySummary $inquiry,
		private readonly InquiryRequest $inquiry_card,
		private readonly Hero $hero,
		private readonly PageCache $page_cache,
		private readonly PageIndexing $page_indexing,
		private readonly Protection\Resources $resources = new Protection\Resources(),
		private readonly Protection\ProviderBudget $provider_budget = new Protection\ProviderBudget()
	) {}

	/**
	 * Adds the plugin's hooks.
	 */
	public function register(): void {
		add_action( 'init', array( $this->assets, 'register' ) );
		add_action( 'init', array( $this->assets, 'load_text_domain' ) );
		add_action( 'init', array( $this->conversations, 'register' ) );
		add_action( 'rest_api_init', array( $this->proxy, 'register' ) );
		// A deleted conversation's file readings leave the service's turn log (#236).
		add_action( 'before_delete_post', array( $this->proxy, 'forget' ) );
		add_action( 'rest_api_init', array( $this->engine_proxy, 'register' ) );
		add_action( 'rest_api_init', array( $this->quality_route, 'register' ) );
		add_action( 'rest_api_init', array( $this->contact, 'register' ) );
		add_action( 'rest_api_init', array( $this->inquiry_card, 'register' ) );
		$this->redirects->register();
		$this->site_chrome->register();
		$this->entries->register();
		$this->retention->register();
		// Registered first in the bootstrap: `determine_current_user` must be
		// listening before anything asks who is making the request.
		$this->user_context->register();
		$this->windpress->register();
		$this->mount->register();
		$this->quality->register();
		$this->quality_page->register();
		$this->preview->register();
		$this->mail->register();
		$this->inquiry->register();
		( new \Linker\Tools\Genie\InquiryAssessmentContext() )->register();
		$this->hero->register();
		// A saved page drops Genie's cached copy of it and of its language twin (#405).
		$this->page_cache->register();
		// The workspace page is a login wall; it stays out of the index and the sitemap.
		$this->page_indexing->register();
		$this->provider_budget->register();
		$this->resources->register();
	}
}
