/*M!999999\- enable the sandbox mode */ 
-- MariaDB dump 10.20-11.8.9-MariaDB, for Linux (x86_64)
--
-- Host: 127.0.0.1    Database: live
-- ------------------------------------------------------
-- Server version	11.8.9-MariaDB-log

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*M!100616 SET @OLD_NOTE_VERBOSITY=@@NOTE_VERBOSITY, NOTE_VERBOSITY=0 */;

--
-- Table structure for table `wp_users`
--

DROP TABLE IF EXISTS `wp_users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `wp_users` (
  `ID` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `user_login` varchar(60) NOT NULL DEFAULT '',
  `user_pass` varchar(255) NOT NULL DEFAULT '',
  `user_nicename` varchar(50) NOT NULL DEFAULT '',
  `user_email` varchar(100) NOT NULL DEFAULT '',
  `user_url` varchar(100) NOT NULL DEFAULT '',
  `user_registered` datetime NOT NULL DEFAULT '0000-00-00 00:00:00',
  `user_activation_key` varchar(255) NOT NULL DEFAULT '',
  `user_status` int(11) NOT NULL DEFAULT 0,
  `display_name` varchar(250) NOT NULL DEFAULT '',
  PRIMARY KEY (`ID`),
  KEY `user_login_key` (`user_login`),
  KEY `user_nicename` (`user_nicename`),
  KEY `user_email` (`user_email`)
) ENGINE=InnoDB AUTO_INCREMENT=37 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `wp_users`
--

SET @OLD_AUTOCOMMIT=@@AUTOCOMMIT, @@AUTOCOMMIT=0;
LOCK TABLES `wp_users` WRITE;
/*!40000 ALTER TABLE `wp_users` DISABLE KEYS */;
INSERT INTO `wp_users` VALUES
(1,'owner@mail.example','$wp$2y$10$abcdefghijklmnopqrstuuMZcYxN0cqI7m3Ve6U2HHq0cS8yEJ9g.','owner','owner@mail.example','','2026-10-01 10:00:00','',0,'Owner'),
(2,'tester','$wp$2y$10$abcdefghijklmnopqrstuuMZcYxN0cqI7m3Ve6U2HHq0cS8yEJ9g.','tester','test@example.com','','2026-10-01 10:00:00','1760000000:$generic$5f4dcc3b5aa765d61d8327deb882cf99',0,'Test Account'),
(18,'jana.doe','$wp$2y$10$abcdefghijklmnopqrstuuMZcYxN0cqI7m3Ve6U2HHq0cS8yEJ9g.','jana-doe','jdoe@kunde.example','https://kunde.example','2026-10-01 10:00:00','1760000000:$generic$5f4dcc3b5aa765d61d8327deb882cf99',0,'Jana Doe');
/*!40000 ALTER TABLE `wp_users` ENABLE KEYS */;
UNLOCK TABLES;
COMMIT;
SET AUTOCOMMIT=@OLD_AUTOCOMMIT;

--
-- Table structure for table `wp_usermeta`
--

DROP TABLE IF EXISTS `wp_usermeta`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `wp_usermeta` (
  `umeta_id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `user_id` bigint(20) unsigned NOT NULL DEFAULT 0,
  `meta_key` varchar(255) DEFAULT NULL,
  `meta_value` longtext DEFAULT NULL,
  PRIMARY KEY (`umeta_id`),
  KEY `user_id` (`user_id`),
  KEY `meta_key` (`meta_key`(191))
) ENGINE=InnoDB AUTO_INCREMENT=2229 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `wp_usermeta`
--

SET @OLD_AUTOCOMMIT=@@AUTOCOMMIT, @@AUTOCOMMIT=0;
LOCK TABLES `wp_usermeta` WRITE;
/*!40000 ALTER TABLE `wp_usermeta` DISABLE KEYS */;
INSERT INTO `wp_usermeta` VALUES
(1,1,'wp_capabilities','a:1:{s:13:\"administrator\";b:1;}'),
(2,1,'_application_passwords','a:1:{i:0;a:7:{s:4:\"uuid\";s:4:\"6f1c\";s:6:\"app_id\";s:0:\"\";s:4:\"name\";s:6:\"deploy\";s:8:\"password\";s:25:\"$generic$0123456789abcdef\";s:7:\"created\";i:1760000000;s:9:\"last_used\";N;s:7:\"last_ip\";N;}}'),
(3,1,'session_tokens','a:1:{s:6:\"9f86d0\";a:4:{s:10:\"expiration\";i:1760100000;s:2:\"ip\";s:11:\"203.0.113.7\";s:2:\"ua\";s:11:\"Mozilla/5.0\";s:5:\"login\";i:1760000000;}}'),
(4,1,'first_name','Owner'),
(5,2,'wp_capabilities','a:1:{s:8:\"customer\";b:1;}'),
(6,18,'wp_capabilities','a:1:{s:8:\"customer\";b:1;}'),
(7,18,'first_name','Jana'),
(8,18,'last_name','Doe'),
(9,18,'nickname','jana.doe'),
(10,18,'billing_email','jdoe@kunde.example'),
(11,18,'billing_phone','+49 170 1234567'),
(12,18,'billing_address_1','Hauptstraße 5'),
(13,18,'billing_address_2',''),
(14,18,'billing_country','DE'),
(15,18,'tv_vat_id','DE123456789'),
(16,18,'tv_company_name','Doe Solar GmbH'),
(17,18,'linker_ai_conversations','[{\"role\": \"user\", \"text\": \"Ich bin Jana, 0170 1234567, jdoe@kunde.example\"}]'),
(18,18,'session_tokens','a:1:{s:4:\"ab12\";a:1:{s:2:\"ip\";s:11:\"203.0.113.8\";}}'),
(19,18,'tv_b2b_status','approved'),
(20,18,'community-events-location','a:1:{s:2:\"ip\";s:11:\"203.0.113.0\";}');
/*!40000 ALTER TABLE `wp_usermeta` ENABLE KEYS */;
UNLOCK TABLES;
COMMIT;
SET AUTOCOMMIT=@OLD_AUTOCOMMIT;

--
-- Table structure for table `wp_options`
--

DROP TABLE IF EXISTS `wp_options`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `wp_options` (
  `option_id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `option_name` varchar(191) NOT NULL DEFAULT '',
  `option_value` longtext NOT NULL,
  `autoload` varchar(20) NOT NULL DEFAULT 'yes',
  PRIMARY KEY (`option_id`),
  UNIQUE KEY `option_name` (`option_name`),
  KEY `autoload` (`autoload`)
) ENGINE=InnoDB AUTO_INCREMENT=328954 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `wp_options`
--

SET @OLD_AUTOCOMMIT=@@AUTOCOMMIT, @@AUTOCOMMIT=0;
LOCK TABLES `wp_options` WRITE;
/*!40000 ALTER TABLE `wp_options` DISABLE KEYS */;
INSERT INTO `wp_options` VALUES
(1,'siteurl','https://de-linker.com','on'),
(2,'home','https://de-linker.com','on'),
(3,'admin_email','owner@mail.example','on'),
(4,'_transient_feed_abc','a:1:{s:6:\"author\";s:21:\"someone@feeds.example\";}','off'),
(5,'_transient_timeout_feed_abc','1760000000','off'),
(6,'lc_apikey','lc-0123456789abcdef0123456789','off'),
(7,'woocommerce_stripe_settings','a:3:{s:7:\"enabled\";s:2:\"no\";s:15:\"test_secret_key\";s:24:\"sk_test_0123456789abcdef\";s:14:\"webhook_secret\";s:22:\"whsec_0123456789abcdef\";}','on'),
(8,'linker_ai_settings_v1','a:4:{s:8:\"provider\";s:8:\"deepseek\";s:7:\"api_key\";s:29:\"sk-0123456789abcdefghijklmnop\";s:5:\"model\";s:13:\"deepseek-chat\";s:10:\"max_tokens\";s:3:\"800\";}','off'),
(9,'tv_089_mail_log','a:2:{i:0;a:3:{s:2:\"to\";s:18:\"jdoe@kunde.example\";s:2:\"cc\";s:19:\"sales@de-linker.com\";s:7:\"subject\";s:22:\"Proforma für Jana Doe\";}i:1;a:2:{s:2:\"to\";s:19:\"guest@firma.example\";s:7:\"subject\";s:7:\"Anfrage\";}}','off'),
(10,'dlk_widget_state','{\"token\": \"abcdefgh12345678\", \"label\": \"Kontakt\", \"url\": \"https://de-linker.com/kontakt/\"}','off'),
(11,'woocommerce_myaccount_lost_password_endpoint','lost-password','on'),
(12,'seopress_pro_license_key','0123456789abcdef0123456789abcdef','on'),
(14,'tv_b2b_project_request_log','[{\"at\": \"2026-09-01\", \"email\": \"jdoe@kunde.example\", \"phone\": \"+49 170 1234567\", \"company\": \"Doe Solar GmbH\"}]','off'),
(15,'woocommerce_new_order_settings','a:3:{s:7:\"enabled\";s:3:\"yes\";s:9:\"recipient\";s:59:\"sales@de-linker.com, jdoe@kunde.example, owner@mail.example\";s:7:\"subject\";s:0:\"\";}','on'),
(13,'dlk_links','a:2:{s:4:\"shop\";s:31:\"https://de-linker.com/products/\";s:4:\"json\";s:37:\"{\"u\":\"https:\\/\\/de-linker.com\\/de\\/\"}\";}','off');
/*!40000 ALTER TABLE `wp_options` ENABLE KEYS */;
UNLOCK TABLES;
COMMIT;
SET AUTOCOMMIT=@OLD_AUTOCOMMIT;

--
-- Table structure for table `wp_posts`
--

DROP TABLE IF EXISTS `wp_posts`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `wp_posts` (
  `ID` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `post_author` bigint(20) unsigned NOT NULL DEFAULT 0,
  `post_date` datetime NOT NULL DEFAULT '0000-00-00 00:00:00',
  `post_date_gmt` datetime NOT NULL DEFAULT '0000-00-00 00:00:00',
  `post_content` longtext NOT NULL,
  `post_title` text NOT NULL,
  `post_excerpt` text NOT NULL,
  `post_status` varchar(20) NOT NULL DEFAULT 'publish',
  `comment_status` varchar(20) NOT NULL DEFAULT 'open',
  `ping_status` varchar(20) NOT NULL DEFAULT 'open',
  `post_password` varchar(255) NOT NULL DEFAULT '',
  `post_name` varchar(200) NOT NULL DEFAULT '',
  `to_ping` text NOT NULL,
  `pinged` text NOT NULL,
  `post_modified` datetime NOT NULL DEFAULT '0000-00-00 00:00:00',
  `post_modified_gmt` datetime NOT NULL DEFAULT '0000-00-00 00:00:00',
  `post_content_filtered` longtext NOT NULL,
  `post_parent` bigint(20) unsigned NOT NULL DEFAULT 0,
  `guid` varchar(255) NOT NULL DEFAULT '',
  `menu_order` int(11) NOT NULL DEFAULT 0,
  `post_type` varchar(20) NOT NULL DEFAULT 'post',
  `post_mime_type` varchar(100) NOT NULL DEFAULT '',
  `comment_count` bigint(20) NOT NULL DEFAULT 0,
  PRIMARY KEY (`ID`),
  KEY `post_name` (`post_name`(191)),
  KEY `type_status_date` (`post_type`,`post_status`,`post_date`,`ID`),
  KEY `post_parent` (`post_parent`),
  KEY `post_author` (`post_author`),
  KEY `type_status_author` (`post_type`,`post_status`,`post_author`)
) ENGINE=InnoDB AUTO_INCREMENT=6564 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `wp_posts`
--

SET @OLD_AUTOCOMMIT=@@AUTOCOMMIT, @@AUTOCOMMIT=0;
LOCK TABLES `wp_posts` WRITE;
/*!40000 ALTER TABLE `wp_posts` DISABLE KEYS */;
INSERT INTO `wp_posts` VALUES
(10,1,'2026-10-01 10:00:00','2026-10-01 10:00:00','<p>Schreiben Sie an sales@de-linker.com, Feld-Beispiel name@company.com, Fragen an jörg.müller@kunde.example.</p><img src=\"https://de-linker.com/wp-content/uploads/2026/07/logo@2x.png\"><a href=\"https://de-linker.com/de/kontakt/\">Kontakt</a><script type=\"application/json\">{\"url\":\"https:\\/\\/de-linker.com\\/de\\/\"}</script><a href=\"https://www.linkedin.com/shareArticle?url=https%3A%2F%2Fde-linker.com%2Fde%2F\">teilen</a>','Kontakt','','publish','closed','closed','','kontakt','','','2026-10-01 10:00:00','2026-10-01 10:00:00','',0,'https://de-linker.com/?page_id=10',0,'page','',0),
(11,1,'2026-10-01 10:00:00','2026-10-01 10:00:00','Hybrid inverter.','GW10K-ET','','publish','open','closed','','gw10k-et','','','2026-10-01 10:00:00','2026-10-01 10:00:00','',0,'https://de-linker.com/?post_type=product&p=11',0,'product','',0),
(12,1,'2026-10-01 10:00:00','2026-10-01 10:00:00','','logo','','inherit','open','closed','','logo','','','2026-10-01 10:00:00','2026-10-01 10:00:00','',0,'https://de-linker.com/wp-content/uploads/2026/07/logo.webp',0,'attachment','image/webp',0),
(13,18,'2026-10-01 10:00:00','2026-10-01 10:00:00','','Order &ndash; October 1, 2026 @ 10:00 AM','Bitte an Frau Doe übergeben','draft','closed','closed','wc_order_AbCdEf1234567','order','','','2026-10-01 10:00:00','2026-10-01 10:00:00','',0,'https://de-linker.com/?post_type=shop_order_placehold&p=13',0,'shop_order_placehold','',1);
/*!40000 ALTER TABLE `wp_posts` ENABLE KEYS */;
UNLOCK TABLES;
COMMIT;
SET AUTOCOMMIT=@OLD_AUTOCOMMIT;

--
-- Table structure for table `wp_postmeta`
--

DROP TABLE IF EXISTS `wp_postmeta`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `wp_postmeta` (
  `meta_id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `post_id` bigint(20) unsigned NOT NULL DEFAULT 0,
  `meta_key` varchar(255) DEFAULT NULL,
  `meta_value` longtext DEFAULT NULL,
  PRIMARY KEY (`meta_id`),
  KEY `post_id` (`post_id`),
  KEY `meta_key` (`meta_key`(191))
) ENGINE=InnoDB AUTO_INCREMENT=46026 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `wp_postmeta`
--

SET @OLD_AUTOCOMMIT=@@AUTOCOMMIT, @@AUTOCOMMIT=0;
LOCK TABLES `wp_postmeta` WRITE;
/*!40000 ALTER TABLE `wp_postmeta` DISABLE KEYS */;
INSERT INTO `wp_postmeta` VALUES
(1,12,'_wp_attached_file','2026/07/logo.webp'),
(2,13,'_billing_email','jdoe@kunde.example'),
(3,13,'_billing_first_name','Jana'),
(4,13,'_customer_ip_address','203.0.113.5'),
(5,11,'_price','1234.00'),
(6,11,'_dlk_integration','{\"endpoint\": \"https://de-linker.com/api/\", \"api_key\": \"live-0123456789\", \"enabled\": \"yes\"}'),
(7,13,'_order_key','wc_order_AbCdEf1234567');
/*!40000 ALTER TABLE `wp_postmeta` ENABLE KEYS */;
UNLOCK TABLES;
COMMIT;
SET AUTOCOMMIT=@OLD_AUTOCOMMIT;

--
-- Table structure for table `wp_comments`
--

DROP TABLE IF EXISTS `wp_comments`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `wp_comments` (
  `comment_ID` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `comment_post_ID` bigint(20) unsigned NOT NULL DEFAULT 0,
  `comment_author` tinytext NOT NULL,
  `comment_author_email` varchar(100) NOT NULL DEFAULT '',
  `comment_author_url` varchar(200) NOT NULL DEFAULT '',
  `comment_author_IP` varchar(100) NOT NULL DEFAULT '',
  `comment_date` datetime NOT NULL DEFAULT '0000-00-00 00:00:00',
  `comment_date_gmt` datetime NOT NULL DEFAULT '0000-00-00 00:00:00',
  `comment_content` text NOT NULL,
  `comment_karma` int(11) NOT NULL DEFAULT 0,
  `comment_approved` varchar(20) NOT NULL DEFAULT '1',
  `comment_agent` varchar(255) NOT NULL DEFAULT '',
  `comment_type` varchar(20) NOT NULL DEFAULT 'comment',
  `comment_parent` bigint(20) unsigned NOT NULL DEFAULT 0,
  `user_id` bigint(20) unsigned NOT NULL DEFAULT 0,
  PRIMARY KEY (`comment_ID`),
  KEY `comment_post_ID` (`comment_post_ID`),
  KEY `comment_approved_date_gmt` (`comment_approved`,`comment_date_gmt`),
  KEY `comment_date_gmt` (`comment_date_gmt`),
  KEY `comment_parent` (`comment_parent`),
  KEY `comment_author_email` (`comment_author_email`(10)),
  KEY `woo_idx_comment_type` (`comment_type`),
  KEY `woo_idx_comment_date_type` (`comment_date_gmt`,`comment_type`,`comment_approved`,`comment_post_ID`),
  KEY `woo_idx_comment_approved_type` (`comment_approved`,`comment_type`,`comment_post_ID`)
) ENGINE=InnoDB AUTO_INCREMENT=216 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `wp_comments`
--

SET @OLD_AUTOCOMMIT=@@AUTOCOMMIT, @@AUTOCOMMIT=0;
LOCK TABLES `wp_comments` WRITE;
/*!40000 ALTER TABLE `wp_comments` DISABLE KEYS */;
INSERT INTO `wp_comments` VALUES
(1,13,'WooCommerce','woocommerce@de-linker.com','','','2026-10-01 10:00:00','2026-10-01 10:00:00','Status changed from Pending to Processing.',0,'1','WooCommerce','order_note',0,0),
(3,13,'WooCommerce','woocommerce@de-linker.com','','','2026-10-01 10:00:00','2026-10-01 10:00:00','Stripe charge complete (Charge ID: ch_3SAbCdEfGhIjKlMn0pQrStUv). Payment Intent: pi_3SAbCdEfGhIjKlMn0pQrStUv',0,'1','WooCommerce','order_note',0,0),
(4,13,'WooCommerce','woocommerce@de-linker.com','','','2026-10-01 11:00:00','2026-10-01 11:00:00','Refunded 0.01 EUR (Refund ID: pyr_1Q2w3e4r5t6y7u8i9o0p1q2w).',0,'1','WooCommerce','order_note',0,0),
(2,11,'Max Mustermann','max@post.example','https://max.example','203.0.113.9','2026-10-01 10:00:00','2026-10-01 10:00:00','Gut, Rückfragen an max@post.example',0,'1','Mozilla/5.0','review',0,0);
/*!40000 ALTER TABLE `wp_comments` ENABLE KEYS */;
UNLOCK TABLES;
COMMIT;
SET AUTOCOMMIT=@OLD_AUTOCOMMIT;

--
-- Table structure for table `wp_wc_orders`
--

DROP TABLE IF EXISTS `wp_wc_orders`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `wp_wc_orders` (
  `id` bigint(20) unsigned NOT NULL,
  `status` varchar(20) DEFAULT NULL,
  `currency` varchar(10) DEFAULT NULL,
  `type` varchar(20) DEFAULT NULL,
  `tax_amount` decimal(26,8) DEFAULT NULL,
  `total_amount` decimal(26,8) DEFAULT NULL,
  `customer_id` bigint(20) unsigned DEFAULT NULL,
  `billing_email` varchar(320) DEFAULT NULL,
  `date_created_gmt` datetime DEFAULT NULL,
  `date_updated_gmt` datetime DEFAULT NULL,
  `parent_order_id` bigint(20) unsigned DEFAULT NULL,
  `payment_method` varchar(100) DEFAULT NULL,
  `payment_method_title` text DEFAULT NULL,
  `transaction_id` varchar(100) DEFAULT NULL,
  `ip_address` varchar(100) DEFAULT NULL,
  `user_agent` text DEFAULT NULL,
  `customer_note` text DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `status` (`status`),
  KEY `date_created` (`date_created_gmt`),
  KEY `customer_id_billing_email` (`customer_id`,`billing_email`(171)),
  KEY `customer_id_status` (`customer_id`,`status`),
  KEY `billing_email` (`billing_email`(191)),
  KEY `transaction_id` (`transaction_id`(20)),
  KEY `type_status_date` (`type`,`status`,`date_created_gmt`),
  KEY `parent_order_id` (`parent_order_id`),
  KEY `date_updated` (`date_updated_gmt`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `wp_wc_orders`
--

SET @OLD_AUTOCOMMIT=@@AUTOCOMMIT, @@AUTOCOMMIT=0;
LOCK TABLES `wp_wc_orders` WRITE;
/*!40000 ALTER TABLE `wp_wc_orders` DISABLE KEYS */;
INSERT INTO `wp_wc_orders` VALUES
(13,'wc-processing','EUR','shop_order','0.00000000','1234.00000000',18,'jdoe@kunde.example','2026-10-01 10:00:00','2026-10-01 10:00:00',0,'bacs','Bank transfer','pi_3Abc','203.0.113.5','Mozilla/5.0','Bitte an Frau Doe übergeben');
/*!40000 ALTER TABLE `wp_wc_orders` ENABLE KEYS */;
UNLOCK TABLES;
COMMIT;
SET AUTOCOMMIT=@OLD_AUTOCOMMIT;

--
-- Table structure for table `wp_wc_order_addresses`
--

DROP TABLE IF EXISTS `wp_wc_order_addresses`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `wp_wc_order_addresses` (
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `order_id` bigint(20) unsigned NOT NULL,
  `address_type` varchar(20) DEFAULT NULL,
  `first_name` text DEFAULT NULL,
  `last_name` text DEFAULT NULL,
  `company` text DEFAULT NULL,
  `address_1` text DEFAULT NULL,
  `address_2` text DEFAULT NULL,
  `city` text DEFAULT NULL,
  `state` text DEFAULT NULL,
  `postcode` text DEFAULT NULL,
  `country` text DEFAULT NULL,
  `email` varchar(320) DEFAULT NULL,
  `phone` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `address_type_order_id` (`address_type`,`order_id`),
  KEY `order_id` (`order_id`),
  KEY `email` (`email`(191)),
  KEY `phone` (`phone`)
) ENGINE=InnoDB AUTO_INCREMENT=133 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `wp_wc_order_addresses`
--

SET @OLD_AUTOCOMMIT=@@AUTOCOMMIT, @@AUTOCOMMIT=0;
LOCK TABLES `wp_wc_order_addresses` WRITE;
/*!40000 ALTER TABLE `wp_wc_order_addresses` DISABLE KEYS */;
INSERT INTO `wp_wc_order_addresses` VALUES
(1,13,'billing','Jana','Doe','Doe Solar GmbH','Hauptstraße 5','Hinterhaus','Hagen','','58095','DE','jdoe@kunde.example','+49 170 1234567');
/*!40000 ALTER TABLE `wp_wc_order_addresses` ENABLE KEYS */;
UNLOCK TABLES;
COMMIT;
SET AUTOCOMMIT=@OLD_AUTOCOMMIT;

--
-- Table structure for table `wp_wc_orders_meta`
--

DROP TABLE IF EXISTS `wp_wc_orders_meta`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `wp_wc_orders_meta` (
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `order_id` bigint(20) unsigned DEFAULT NULL,
  `meta_key` varchar(255) DEFAULT NULL,
  `meta_value` text DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `meta_key_value` (`meta_key`(50),`meta_value`(20)),
  KEY `order_id_meta_key_meta_value` (`order_id`,`meta_key`(100),`meta_value`(82))
) ENGINE=InnoDB AUTO_INCREMENT=1830 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `wp_wc_orders_meta`
--

SET @OLD_AUTOCOMMIT=@@AUTOCOMMIT, @@AUTOCOMMIT=0;
LOCK TABLES `wp_wc_orders_meta` WRITE;
/*!40000 ALTER TABLE `wp_wc_orders_meta` DISABLE KEYS */;
INSERT INTO `wp_wc_orders_meta` VALUES
(1,13,'_billing_address_index','Jana Doe Doe Solar GmbH Hauptstraße 5 Hagen 58095 DE jdoe@kunde.example +49 170 1234567'),
(2,13,'is_vat_exempt','no'),
(3,13,'tv_b2b_document_ledger_v2','{\"proformas\": [{\"number\": \"PI-2026-0001\", \"snapshot\": {\"seller\": {\"company_name\": \"Linker Technology GmbH\", \"email\": \"sales@de-linker.com\"}, \"buyer\": {\"billing\": {\"first_name\": \"Jana\", \"last_name\": \"Doe\", \"company\": \"Doe Solar GmbH\", \"address_1\": \"Hauptstra\\u00dfe 5\", \"city\": \"Hagen\", \"postcode\": \"58095\", \"phone\": \"+49 170 1234567\", \"email\": \"jdoe@kunde.example\"}, \"account\": {\"vat_id\": \"DE123456789\", \"company_registration_number\": \"HRB 4711\"}}, \"items\": [{\"name\": \"GW10K-ET\", \"qty\": 1}]}}]}'),
(4,13,'tv_b2b_order_vat_snapshot','a:4:{s:6:\"vat_id\";s:11:\"DE123456789\";s:4:\"name\";s:14:\"Doe Solar GmbH\";s:7:\"address\";s:27:\"Hauptstraße 5, 58095 Hagen\";s:5:\"valid\";s:3:\"yes\";}');
/*!40000 ALTER TABLE `wp_wc_orders_meta` ENABLE KEYS */;
UNLOCK TABLES;
COMMIT;
SET AUTOCOMMIT=@OLD_AUTOCOMMIT;

--
-- Table structure for table `wp_wc_order_operational_data`
--

DROP TABLE IF EXISTS `wp_wc_order_operational_data`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `wp_wc_order_operational_data` (
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `order_id` bigint(20) unsigned DEFAULT NULL,
  `created_via` varchar(100) DEFAULT NULL,
  `woocommerce_version` varchar(20) DEFAULT NULL,
  `prices_include_tax` tinyint(1) DEFAULT NULL,
  `coupon_usages_are_counted` tinyint(1) DEFAULT NULL,
  `download_permission_granted` tinyint(1) DEFAULT NULL,
  `cart_hash` varchar(100) DEFAULT NULL,
  `new_order_email_sent` tinyint(1) DEFAULT NULL,
  `order_key` varchar(100) DEFAULT NULL,
  `order_stock_reduced` tinyint(1) DEFAULT NULL,
  `date_paid_gmt` datetime DEFAULT NULL,
  `date_completed_gmt` datetime DEFAULT NULL,
  `shipping_tax_amount` decimal(26,8) DEFAULT NULL,
  `shipping_total_amount` decimal(26,8) DEFAULT NULL,
  `discount_tax_amount` decimal(26,8) DEFAULT NULL,
  `discount_total_amount` decimal(26,8) DEFAULT NULL,
  `recorded_sales` tinyint(1) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `order_id` (`order_id`),
  KEY `order_key` (`order_key`)
) ENGINE=InnoDB AUTO_INCREMENT=457 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `wp_wc_order_operational_data`
--

SET @OLD_AUTOCOMMIT=@@AUTOCOMMIT, @@AUTOCOMMIT=0;
LOCK TABLES `wp_wc_order_operational_data` WRITE;
/*!40000 ALTER TABLE `wp_wc_order_operational_data` DISABLE KEYS */;
INSERT INTO `wp_wc_order_operational_data` VALUES
(1,13,'checkout','11.2.0',0,1,1,'5f4dcc3b',1,'wc_order_AbCdEf1234567',1,NULL,NULL,'0.00000000','0.00000000','0.00000000','0.00000000',1);
/*!40000 ALTER TABLE `wp_wc_order_operational_data` ENABLE KEYS */;
UNLOCK TABLES;
COMMIT;
SET AUTOCOMMIT=@OLD_AUTOCOMMIT;

--
-- Table structure for table `wp_wc_customer_lookup`
--

DROP TABLE IF EXISTS `wp_wc_customer_lookup`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `wp_wc_customer_lookup` (
  `customer_id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `user_id` bigint(20) unsigned DEFAULT NULL,
  `username` varchar(60) NOT NULL DEFAULT '',
  `first_name` varchar(255) NOT NULL,
  `last_name` varchar(255) NOT NULL,
  `email` varchar(100) DEFAULT NULL,
  `date_last_active` timestamp NULL DEFAULT NULL,
  `date_registered` timestamp NULL DEFAULT NULL,
  `country` char(2) NOT NULL DEFAULT '',
  `postcode` varchar(20) NOT NULL DEFAULT '',
  `city` varchar(100) NOT NULL DEFAULT '',
  `state` varchar(100) NOT NULL DEFAULT '',
  `billing_phone` varchar(100) NOT NULL DEFAULT '',
  `shipping_phone` varchar(100) NOT NULL DEFAULT '',
  PRIMARY KEY (`customer_id`),
  UNIQUE KEY `user_id` (`user_id`),
  KEY `email` (`email`)
) ENGINE=InnoDB AUTO_INCREMENT=31 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `wp_wc_customer_lookup`
--

SET @OLD_AUTOCOMMIT=@@AUTOCOMMIT, @@AUTOCOMMIT=0;
LOCK TABLES `wp_wc_customer_lookup` WRITE;
/*!40000 ALTER TABLE `wp_wc_customer_lookup` DISABLE KEYS */;
INSERT INTO `wp_wc_customer_lookup` VALUES
(1,18,'jana.doe','Jana','Doe','jdoe@kunde.example',NULL,'2026-10-01 10:00:00','DE','58095','Hagen','','+49 170 1234567','');
/*!40000 ALTER TABLE `wp_wc_customer_lookup` ENABLE KEYS */;
UNLOCK TABLES;
COMMIT;
SET AUTOCOMMIT=@OLD_AUTOCOMMIT;

--
-- Table structure for table `wp_tv_b2b_contact_request`
--

DROP TABLE IF EXISTS `wp_tv_b2b_contact_request`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `wp_tv_b2b_contact_request` (
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `created_at` datetime NOT NULL,
  `inquiry_type` varchar(80) NOT NULL DEFAULT '',
  `name` varchar(190) NOT NULL DEFAULT '',
  `email` varchar(190) NOT NULL DEFAULT '',
  `phone` varchar(80) NOT NULL DEFAULT '',
  `company` varchar(190) NOT NULL DEFAULT '',
  `message` text NOT NULL,
  `source` varchar(190) NOT NULL DEFAULT '',
  `locale` varchar(5) NOT NULL DEFAULT 'en',
  `consent_at` datetime NOT NULL,
  `user_id` bigint(20) unsigned NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  KEY `idx_created` (`created_at`),
  KEY `idx_email` (`email`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `wp_tv_b2b_contact_request`
--

SET @OLD_AUTOCOMMIT=@@AUTOCOMMIT, @@AUTOCOMMIT=0;
LOCK TABLES `wp_tv_b2b_contact_request` WRITE;
/*!40000 ALTER TABLE `wp_tv_b2b_contact_request` DISABLE KEYS */;
INSERT INTO `wp_tv_b2b_contact_request` VALUES
(1,'2026-10-01 10:00:00','general','Jana Doe','jdoe@kunde.example','+49 170 1234567','Doe Solar GmbH','Bitte rufen Sie mich an.','contact','de','2026-10-01 10:00:00',18);
/*!40000 ALTER TABLE `wp_tv_b2b_contact_request` ENABLE KEYS */;
UNLOCK TABLES;
COMMIT;
SET AUTOCOMMIT=@OLD_AUTOCOMMIT;

--
-- Table structure for table `wp_woocommerce_sessions`
--

DROP TABLE IF EXISTS `wp_woocommerce_sessions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `wp_woocommerce_sessions` (
  `session_id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `session_key` char(32) NOT NULL,
  `session_value` longtext NOT NULL,
  `session_expiry` bigint(20) unsigned NOT NULL,
  PRIMARY KEY (`session_id`),
  UNIQUE KEY `session_key` (`session_key`),
  KEY `session_expiry` (`session_expiry`)
) ENGINE=InnoDB AUTO_INCREMENT=1825 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `wp_woocommerce_sessions`
--

SET @OLD_AUTOCOMMIT=@@AUTOCOMMIT, @@AUTOCOMMIT=0;
LOCK TABLES `wp_woocommerce_sessions` WRITE;
/*!40000 ALTER TABLE `wp_woocommerce_sessions` DISABLE KEYS */;
INSERT INTO `wp_woocommerce_sessions` VALUES
(1,'t_8f3a','a:1:{s:8:\"customer\";s:44:\"a:1:{s:5:\"email\";s:18:\"jdoe@kunde.example\";}\";}',1760100000);
/*!40000 ALTER TABLE `wp_woocommerce_sessions` ENABLE KEYS */;
UNLOCK TABLES;
COMMIT;
SET AUTOCOMMIT=@OLD_AUTOCOMMIT;

--
-- Table structure for table `wp_actionscheduler_actions`
--

DROP TABLE IF EXISTS `wp_actionscheduler_actions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `wp_actionscheduler_actions` (
  `action_id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `hook` varchar(191) NOT NULL,
  `status` varchar(20) NOT NULL,
  `scheduled_date_gmt` datetime DEFAULT '0000-00-00 00:00:00',
  `scheduled_date_local` datetime DEFAULT '0000-00-00 00:00:00',
  `priority` tinyint(3) unsigned NOT NULL DEFAULT 10,
  `args` varchar(191) DEFAULT NULL,
  `schedule` longtext DEFAULT NULL,
  `group_id` bigint(20) unsigned NOT NULL DEFAULT 0,
  `attempts` int(11) NOT NULL DEFAULT 0,
  `last_attempt_gmt` datetime DEFAULT '0000-00-00 00:00:00',
  `last_attempt_local` datetime DEFAULT '0000-00-00 00:00:00',
  `claim_id` bigint(20) unsigned NOT NULL DEFAULT 0,
  `extended_args` varchar(8000) DEFAULT NULL,
  PRIMARY KEY (`action_id`),
  KEY `hook_status_scheduled_date_gmt` (`hook`(163),`status`,`scheduled_date_gmt`),
  KEY `status_scheduled_date_gmt` (`status`,`scheduled_date_gmt`),
  KEY `scheduled_date_gmt` (`scheduled_date_gmt`),
  KEY `args` (`args`),
  KEY `group_id` (`group_id`),
  KEY `last_attempt_gmt` (`last_attempt_gmt`),
  KEY `claim_id_status_priority_scheduled_date_gmt` (`claim_id`,`status`,`priority`,`scheduled_date_gmt`),
  KEY `status_last_attempt_gmt` (`status`,`last_attempt_gmt`),
  KEY `status_claim_id` (`status`,`claim_id`)
) ENGINE=InnoDB AUTO_INCREMENT=8808 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `wp_actionscheduler_actions`
--

SET @OLD_AUTOCOMMIT=@@AUTOCOMMIT, @@AUTOCOMMIT=0;
LOCK TABLES `wp_actionscheduler_actions` WRITE;
/*!40000 ALTER TABLE `wp_actionscheduler_actions` DISABLE KEYS */;
INSERT INTO `wp_actionscheduler_actions` VALUES
(1,'woocommerce_cleanup_sessions','pending','2026-10-01 10:00:00','2026-10-01 10:00:00',10,'[]','O:32:\"ActionScheduler_IntervalSchedule\":0:{}',3,0,'2026-10-01 10:00:00','2026-10-01 10:00:00',0,NULL),
(2,'woocommerce_send_queued_transactional_email','complete','2026-10-01 10:00:00','2026-10-01 10:00:00',10,NULL,'O:30:\"ActionScheduler_SimpleSchedule\":0:{}',13,1,'2026-10-01 10:00:00','2026-10-01 10:00:00',0,'[\"woocommerce_created_customer_notification\", [{\"customer_id\": 18, \"new_customer_data\": {\"user_login\": \"jana.doe\", \"user_pass\": \"Gen3rated!Pass\", \"user_email\": \"jdoe@kunde.example\"}}]]');
/*!40000 ALTER TABLE `wp_actionscheduler_actions` ENABLE KEYS */;
UNLOCK TABLES;
COMMIT;
SET AUTOCOMMIT=@OLD_AUTOCOMMIT;

--
-- Table structure for table `wp_snippets`
--

DROP TABLE IF EXISTS `wp_snippets`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `wp_snippets` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `name` tinytext NOT NULL,
  `description` text NOT NULL,
  `code` longtext NOT NULL,
  `tags` longtext NOT NULL,
  `scope` varchar(15) NOT NULL DEFAULT 'global',
  `condition_id` bigint(20) NOT NULL DEFAULT 0,
  `priority` smallint(6) NOT NULL DEFAULT 10,
  `active` tinyint(1) NOT NULL DEFAULT 0,
  `modified` datetime NOT NULL DEFAULT current_timestamp(),
  `revision` bigint(20) NOT NULL DEFAULT 1,
  `cloud_id` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `scope` (`scope`),
  KEY `active` (`active`)
) ENGINE=InnoDB AUTO_INCREMENT=11126 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `wp_snippets`
--

SET @OLD_AUTOCOMMIT=@@AUTOCOMMIT, @@AUTOCOMMIT=0;
LOCK TABLES `wp_snippets` WRITE;
/*!40000 ALTER TABLE `wp_snippets` DISABLE KEYS */;
INSERT INTO `wp_snippets` VALUES
(27,'Footer year','','add_filter( \'linker_year\', static fn() => gmdate( \'Y\' ) );','','global',0,10,1,'2026-10-01 10:00:00',1,NULL),
(224,'NV probe','','define( \'LINKER_NVAPI_KEY\', \'nvapi-AbCdEfGhIjKlMnOpQrStUvWxYz0123456789AbCdEfGhIjKlMnOpQrStUvWxYz01\' );','','global',0,10,0,'2026-10-01 10:00:00',1,NULL),
(276,'Engine bridge','','$token = \'0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f\'; wp_remote_post( \'https://engine.example/run\', array( \'headers\' => array( \'Authorization\' => \'Bearer \' . $token ) ) );','','single-use',0,10,-1,'2026-10-01 10:00:00',1,NULL);
/*!40000 ALTER TABLE `wp_snippets` ENABLE KEYS */;
UNLOCK TABLES;
COMMIT;
SET AUTOCOMMIT=@OLD_AUTOCOMMIT;

--
-- Table structure for table `wp_linker_ai_conversation`
--

DROP TABLE IF EXISTS `wp_linker_ai_conversation`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `wp_linker_ai_conversation` (
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `user_id` bigint(20) unsigned NOT NULL DEFAULT 0,
  `messages` longtext NOT NULL,
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*M!100616 SET NOTE_VERBOSITY=@OLD_NOTE_VERBOSITY */;

-- Dump completed
