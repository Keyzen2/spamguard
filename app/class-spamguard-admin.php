<?php
/**
 * Administracion del plugin
 */

if (!defined('ABSPATH')) {
    exit;
}

class SpamGuard_Admin {
    
    private static $instance = null;
    
    public static function get_instance() {
        if (null === self::$instance) {
            self::$instance = new self();
        }
        return self::$instance;
    }
    
    private function __construct() {
        add_action('admin_menu', array($this, 'add_admin_menu'));
        add_action('admin_enqueue_scripts', array($this, 'enqueue_admin_assets'));
        add_filter('comment_row_actions', array($this, 'add_quick_actions'), 10, 2);
        add_action('admin_action_spamguard_blacklist', array($this, 'handle_blacklist'));
        add_action('admin_action_spamguard_whitelist', array($this, 'handle_whitelist'));
        add_action('wp_ajax_spamguard_register', array($this, 'ajax_register_site'));
        add_action('wp_ajax_spamguard_get_stats', array($this, 'ajax_get_stats'));
        add_action('wp_ajax_spamguard_test_connection', array($this, 'ajax_test_connection'));
    }
    
    public function add_admin_menu() {
        add_menu_page(
            'SpamGuard AI',
            'SpamGuard AI',
            'manage_options',
            'spamguard',
            array($this, 'render_dashboard'),
            'dashicons-shield',
            26
        );
        
        add_submenu_page('spamguard', 'Dashboard', 'Dashboard', 'manage_options', 'spamguard', array($this, 'render_dashboard'));
        add_submenu_page('spamguard', 'Configuracion', 'Configuracion', 'manage_options', 'spamguard-settings', array($this, 'render_settings'));
        add_submenu_page('spamguard', 'Logs', 'Logs', 'manage_options', 'spamguard-logs', array($this, 'render_logs'));
    }
    
    public function enqueue_admin_assets($hook) {
        if (strpos($hook, 'spamguard') === false) {
            return;
        }
        
        wp_enqueue_style('spamguard-admin', plugin_dir_url(dirname(__FILE__)) . 'assets/css/admin.css', array(), SPAMGUARD_VERSION);
        wp_enqueue_script('spamguard-admin', plugin_dir_url(dirname(__FILE__)) . 'assets/js/admin.js', array('jquery', 'chart-js'), SPAMGUARD_VERSION, true);
        
        wp_localize_script('spamguard-admin', 'spamguardAdmin', array(
            'ajaxUrl' => admin_url('admin-ajax.php'),
            'nonce' => wp_create_nonce('spamguard_admin')
        ));
    }
    
    public function add_quick_actions($actions, $comment) {
        if (empty($comment->comment_author_email)) {
            return $actions;
        }
        
        $blacklist_emails = SpamGuard_Core::get_option('blacklist_emails', array());
        $whitelist_emails = SpamGuard_Core::get_option('whitelist_emails', array());
        
        if (!in_array($comment->comment_author_email, $blacklist_emails)) {
            $actions['spamguard_blacklist'] = sprintf(
                '<a href="%s" style="color: #d63638;">Bloquear Email</a>',
                wp_nonce_url(admin_url('comment.php?action=spamguard_blacklist&c=' . $comment->comment_ID), 'spamguard_blacklist_' . $comment->comment_ID)
            );
        }
        
        if (!in_array($comment->comment_author_email, $whitelist_emails)) {
            $actions['spamguard_whitelist'] = sprintf(
                '<a href="%s" style="color: #00a32a;">Confiar Email</a>',
                wp_nonce_url(admin_url('comment.php?action=spamguard_whitelist&c=' . $comment->comment_ID), 'spamguard_whitelist_' . $comment->comment_ID)
            );
        }
        
        return $actions;
    }
    
    public function handle_blacklist() {
        $comment_id = isset($_GET['c']) ? intval($_GET['c']) : 0;
        check_admin_referer('spamguard_blacklist_' . $comment_id);
        
        if (!current_user_can('moderate_comments')) {
            wp_die('No tienes permisos');
        }
        
        $comment = get_comment($comment_id);
        if ($comment) {
            $blacklist = SpamGuard_Core::get_option('blacklist_emails', array());
            if (!in_array($comment->comment_author_email, $blacklist)) {
                $blacklist[] = $comment->comment_author_email;
                SpamGuard_Core::update_option('blacklist_emails', $blacklist);
                wp_spam_comment($comment_id);
            }
        }
        
        wp_redirect(admin_url('edit-comments.php'));
        exit;
    }
    
    public function handle_whitelist() {
        $comment_id = isset($_GET['c']) ? intval($_GET['c']) : 0;
        check_admin_referer('spamguard_whitelist_' . $comment_id);
        
        if (!current_user_can('moderate_comments')) {
            wp_die('No tienes permisos');
        }
        
        $comment = get_comment($comment_id);
        if ($comment) {
            $whitelist = SpamGuard_Core::get_option('whitelist_emails', array());
            if (!in_array($comment->comment_author_email, $whitelist)) {
                $whitelist[] = $comment->comment_author_email;
                SpamGuard_Core::update_option('whitelist_emails', $whitelist);
                wp_set_comment_status($comment_id, 'approve');
            }
        }
        
        wp_redirect(admin_url('edit-comments.php'));
        exit;
    }
    
    public function render_dashboard() {
        include SPAMGUARD_PLUGIN_DIR . 'templates/admin-dashboard.php';
    }
    
    public function render_settings() {
        include SPAMGUARD_PLUGIN_DIR . 'templates/admin-settings.php';
    }
    
    public function render_logs() {
        include SPAMGUARD_PLUGIN_DIR . 'templates/admin-logs.php';
    }
    
    public function ajax_register_site() {
        check_ajax_referer('spamguard_admin', 'nonce');
        
        if (!current_user_can('manage_options')) {
            wp_send_json_error('Permisos insuficientes');
        }
        
        $api = SpamGuard_API::get_instance();
        $result = $api->register_site();
        
        if (is_wp_error($result)) {
            wp_send_json_error($result->get_error_message());
        }
        
        wp_send_json_success($result);
    }
    
    public function ajax_get_stats() {
        check_ajax_referer('spamguard_admin', 'nonce');
        
        if (!current_user_can('manage_options')) {
            wp_send_json_error('Permisos insuficientes');
        }
        
        $api = SpamGuard_API::get_instance();
        $stats = $api->get_stats();
        
        if (is_wp_error($stats)) {
            wp_send_json_error($stats->get_error_message());
        }
        
        wp_send_json_success($stats);
    }
    
    public function ajax_test_connection() {
        check_ajax_referer('spamguard_admin', 'nonce');
        
        if (!current_user_can('manage_options')) {
            wp_send_json_error('Permisos insuficientes');
        }
        
        $api = SpamGuard_API::get_instance();
        $test = $api->test_connection();
        
        if (is_wp_error($test)) {
            wp_send_json_error($test->get_error_message());
        }
        
        wp_send_json_success($test);
    }
}
