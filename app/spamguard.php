<?php
/**
 * Plugin Name: SpamGuard AI
 * Plugin URI: https://spamguard.ai
 * Description: Sistema inteligente de deteccion de spam con Machine Learning
 * Version: 1.0.0
 * Author: SpamGuard Team
 * License: GPL v2 or later
 * Text Domain: spamguard
 * Requires at least: 5.8
 * Requires PHP: 7.4
 */

if (!defined('ABSPATH')) {
    exit;
}

define('SPAMGUARD_VERSION', '1.0.0');
define('SPAMGUARD_PLUGIN_DIR', plugin_dir_path(__FILE__));
define('SPAMGUARD_PLUGIN_URL', plugin_dir_url(__FILE__));
define('SPAMGUARD_PLUGIN_BASENAME', plugin_basename(__FILE__));
define('SPAMGUARD_API_URL', 'https://spamguard.up.railway.app');

class SpamGuard {
    
    private static $instance = null;
    
    public static function get_instance() {
        if (null === self::$instance) {
            self::$instance = new self();
        }
        return self::$instance;
    }
    
    private function __construct() {
        $this->load_dependencies();
        $this->init_hooks();
    }
    
    private function load_dependencies() {
        require_once SPAMGUARD_PLUGIN_DIR . 'includes/class-spamguard-core.php';
        require_once SPAMGUARD_PLUGIN_DIR . 'includes/class-spamguard-api.php';
        require_once SPAMGUARD_PLUGIN_DIR . 'includes/class-spamguard-admin.php';
        require_once SPAMGUARD_PLUGIN_DIR . 'includes/class-spamguard-filter.php';
        require_once SPAMGUARD_PLUGIN_DIR . 'includes/class-spamguard-stats.php';
    }
    
    private function init_hooks() {
        register_activation_hook(__FILE__, array($this, 'activate'));
        register_deactivation_hook(__FILE__, array($this, 'deactivate'));
        add_action('plugins_loaded', array($this, 'init'));
        add_action('init', array($this, 'load_textdomain'));
    }
    
    public function init() {
        SpamGuard_Core::get_instance();
        SpamGuard_Admin::get_instance();
        SpamGuard_Filter::get_instance();
        SpamGuard_Stats::get_instance();
    }
    
    public function activate() {
        global $wpdb;
        $table_name = $wpdb->prefix . 'spamguard_logs';
        $charset_collate = $wpdb->get_charset_collate();
        
        $sql = "CREATE TABLE IF NOT EXISTS $table_name (
            id bigint(20) NOT NULL AUTO_INCREMENT,
            comment_id bigint(20) NOT NULL,
            is_spam tinyint(1) NOT NULL,
            confidence float NOT NULL,
            reasons text,
            created_at datetime DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY  (id),
            KEY comment_id (comment_id),
            KEY created_at (created_at)
        ) $charset_collate;";
        
        require_once(ABSPATH . 'wp-admin/includes/upgrade.php');
        dbDelta($sql);
        
        add_option('spamguard_api_key', '');
        add_option('spamguard_api_url', SPAMGUARD_API_URL);
        add_option('spamguard_auto_delete', false);
        add_option('spamguard_sensitivity', 0.5);
        add_option('spamguard_learning_enabled', true);
        add_option('spamguard_min_comment_time', 3);
        add_option('spamguard_blacklist_ips', array());
        add_option('spamguard_blacklist_emails', array());
        add_option('spamguard_whitelist_ips', array());
        add_option('spamguard_whitelist_emails', array());
        add_option('spamguard_stats', array(
            'total_analyzed' => 0,
            'spam_blocked' => 0,
            'false_positives' => 0,
            'false_negatives' => 0
        ));
        
        if (!wp_next_scheduled('spamguard_cleanup_logs')) {
            wp_schedule_event(time(), 'daily', 'spamguard_cleanup_logs');
        }
        
        flush_rewrite_rules();
    }
    
    public function deactivate() {
        wp_clear_scheduled_hook('spamguard_cleanup_logs');
        flush_rewrite_rules();
    }
    
    public function load_textdomain() {
        load_plugin_textdomain('spamguard', false, dirname(SPAMGUARD_PLUGIN_BASENAME) . '/languages/');
    }
}

function spamguard() {
    return SpamGuard::get_instance();
}

spamguard();
