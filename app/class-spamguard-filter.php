<?php
/**
 * Filtro de comentarios - Core del sistema anti-spam
 */

if (!defined('ABSPATH')) {
    exit;
}

class SpamGuard_Filter {
    
    private static $instance = null;
    private $api;
    
    public static function get_instance() {
        if (null === self::$instance) {
            self::$instance = new self();
        }
        return self::$instance;
    }
    
    private function __construct() {
        $this->api = SpamGuard_API::get_instance();
        
        add_filter('pre_comment_approved', array($this, 'check_comment'), 10, 2);
        add_action('spam_comment', array($this, 'learn_spam'));
        add_action('unspam_comment', array($this, 'learn_ham'));
        add_action('wp_set_comment_status', array($this, 'comment_status_changed'), 10, 2);
        add_action('add_meta_boxes_comment', array($this, 'add_comment_metabox'));
        add_action('comment_form', array($this, 'add_honeypot_field'));
    }
    
    public function add_honeypot_field() {
        ?>
        <p style="position: absolute; left: -9999px; width: 1px; height: 1px; overflow: hidden;">
            <input type="text" name="spamguard_website" value="" tabindex="-1" autocomplete="off">
        </p>
        <input type="hidden" name="spamguard_timestamp" value="<?php echo time(); ?>">
        <?php
    }
    
    public function check_comment($approved, $commentdata) {
        if (!SpamGuard_Core::is_configured()) {
            return $approved;
        }
        
        if (is_user_logged_in() && SpamGuard_Core::get_option('skip_registered_users', false)) {
            return $approved;
        }
        
        // Honeypot check
        if (isset($_POST['spamguard_website']) && !empty($_POST['spamguard_website'])) {
            $this->log_blocked_spam(0, 1.0, array('Honeypot triggered'));
            return SpamGuard_Core::get_option('auto_delete', false) ? 'spam' : 0;
        }
        
        // Time check
        if (isset($_POST['spamguard_timestamp'])) {
            $elapsed = time() - intval($_POST['spamguard_timestamp']);
            $min_time = SpamGuard_Core::get_option('min_comment_time', 3);
            
            if ($elapsed < $min_time) {
                $this->log_blocked_spam(0, 0.95, array("Too fast: {$elapsed}s"));
                return SpamGuard_Core::get_option('auto_delete', false) ? 'spam' : 0;
            }
        }
        
        // Blacklist check
        $blacklist_ips = SpamGuard_Core::get_option('blacklist_ips', array());
        $blacklist_emails = SpamGuard_Core::get_option('blacklist_emails', array());
        
        if (in_array($commentdata['comment_author_IP'], $blacklist_ips)) {
            $this->log_blocked_spam(0, 1.0, array('IP blacklisted'));
            return 'spam';
        }
        
        if (in_array($commentdata['comment_author_email'], $blacklist_emails)) {
            $this->log_blocked_spam(0, 1.0, array('Email blacklisted'));
            return 'spam';
        }
        
        // Whitelist check
        $whitelist_ips = SpamGuard_Core::get_option('whitelist_ips', array());
        $whitelist_emails = SpamGuard_Core::get_option('whitelist_emails', array());
        
        if (in_array($commentdata['comment_author_IP'], $whitelist_ips) || 
            in_array($commentdata['comment_author_email'], $whitelist_emails)) {
            return 1;
        }
        
        // API analysis
        $comment_for_api = array(
            'content' => $commentdata['comment_content'],
            'author' => $commentdata['comment_author'],
            'author_email' => $commentdata['comment_author_email'],
            'author_url' => $commentdata['comment_author_url'],
            'author_ip' => $commentdata['comment_author_IP'],
            'post_id' => $commentdata['comment_post_ID'],
            'user_agent' => isset($_SERVER['HTTP_USER_AGENT']) ? $_SERVER['HTTP_USER_AGENT'] : '',
            'referer' => isset($_SERVER['HTTP_REFERER']) ? $_SERVER['HTTP_REFERER'] : ''
        );
        
        $result = $this->api->analyze_comment($comment_for_api);
        
        if (is_wp_error($result)) {
            error_log('SpamGuard API Error: ' . $result->get_error_message());
            return $approved;
        }
        
        $stats = SpamGuard_Core::get_option('stats', array());
        $stats['total_analyzed'] = isset($stats['total_analyzed']) ? $stats['total_analyzed'] + 1 : 1;
        
        add_filter('comment_post', function($comment_id) use ($result) {
            update_comment_meta($comment_id, '_spamguard_analysis', array(
                'is_spam' => $result['is_spam'],
                'confidence' => $result['confidence'],
                'spam_score' => $result['spam_score'],
                'reasons' => $result['reasons'],
                'comment_id' => $result['comment_id'],
                'analyzed_at' => current_time('mysql')
            ));
            
            SpamGuard_Core::log_analysis($comment_id, $result['is_spam'], $result['confidence'], $result['reasons']);
            return $comment_id;
        });
        
        $sensitivity = SpamGuard_Core::get_option('sensitivity', 0.5);
        
        if ($result['is_spam'] && $result['confidence'] >= $sensitivity) {
            $stats['spam_blocked'] = isset($stats['spam_blocked']) ? $stats['spam_blocked'] + 1 : 1;
            SpamGuard_Core::update_option('stats', $stats);
            return SpamGuard_Core::get_option('auto_delete', false) ? 'spam' : 0;
        }
        
        SpamGuard_Core::update_option('stats', $stats);
        return $approved;
    }
    
    private function log_blocked_spam($comment_id, $confidence, $reasons) {
        $stats = SpamGuard_Core::get_option('stats', array());
        $stats['total_analyzed'] = isset($stats['total_analyzed']) ? $stats['total_analyzed'] + 1 : 1;
        $stats['spam_blocked'] = isset($stats['spam_blocked']) ? $stats['spam_blocked'] + 1 : 1;
        SpamGuard_Core::update_option('stats', $stats);
        
        if ($comment_id > 0) {
            SpamGuard_Core::log_analysis($comment_id, true, $confidence, $reasons);
        }
    }
    
    public function learn_spam($comment_id) {
        if (!SpamGuard_Core::get_option('learning_enabled', true)) {
            return;
        }
        
        $analysis = get_comment_meta($comment_id, '_spamguard_analysis', true);
        
        if (empty($analysis) || empty($analysis['comment_id'])) {
            return;
        }
        
        $this->api->send_feedback($analysis['comment_id'], true);
        
        $stats = SpamGuard_Core::get_option('stats', array());
        if (!$analysis['is_spam']) {
            $stats['false_negatives'] = isset($stats['false_negatives']) ? $stats['false_negatives'] + 1 : 1;
        }
        SpamGuard_Core::update_option('stats', $stats);
    }
    
    public function learn_ham($comment_id) {
        if (!SpamGuard_Core::get_option('learning_enabled', true)) {
            return;
        }
        
        $analysis = get_comment_meta($comment_id, '_spamguard_analysis', true);
        
        if (empty($analysis) || empty($analysis['comment_id'])) {
            return;
        }
        
        $this->api->send_feedback($analysis['comment_id'], false);
        
        $stats = SpamGuard_Core::get_option('stats', array());
        if ($analysis['is_spam']) {
            $stats['false_positives'] = isset($stats['false_positives']) ? $stats['false_positives'] + 1 : 1;
        }
        SpamGuard_Core::update_option('stats', $stats);
    }
    
    public function comment_status_changed($comment_id, $status) {
        if ($status === 'spam') {
            $this->learn_spam($comment_id);
        } elseif ($status === 'approve') {
            $comment = get_comment($comment_id);
            if ($comment && $comment->comment_approved === 'spam') {
                $this->learn_ham($comment_id);
            }
        }
    }
    
    public function add_comment_metabox() {
        add_meta_box('spamguard-analysis', 'SpamGuard AI - Analisis', array($this, 'render_comment_metabox'), 'comment', 'normal', 'high');
    }
    
    public function render_comment_metabox($comment) {
        $analysis = get_comment_meta($comment->comment_ID, '_spamguard_analysis', true);
        
        if (empty($analysis)) {
            echo '<p>Este comentario no fue analizado por SpamGuard AI.</p>';
            return;
        }
        ?>
        <table class="form-table">
            <tr>
                <th>Clasificacion:</th>
                <td>
                    <strong style="color: <?php echo $analysis['is_spam'] ? '#d63638' : '#00a32a'; ?>">
                        <?php echo $analysis['is_spam'] ? 'SPAM' : 'LEGITIMO'; ?>
                    </strong>
                </td>
            </tr>
            <tr>
                <th>Confianza:</th>
                <td><?php echo round($analysis['confidence'] * 100, 1); ?>%</td>
            </tr>
            <tr>
                <th>Razones:</th>
                <td>
                    <ul>
                        <?php foreach ($analysis['reasons'] as $reason): ?>
                            <li><?php echo esc_html($reason); ?></li>
                        <?php endforeach; ?>
                    </ul>
                </td>
            </tr>
        </table>
        <?php
    }
}
