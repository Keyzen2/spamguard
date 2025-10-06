<?php
if (!defined('ABSPATH')) exit;

// Guardar configuracion
if (isset($_POST['spamguard_save_settings']) && check_admin_referer('spamguard_settings')) {
    SpamGuard_Core::update_option('api_key', sanitize_text_field($_POST['spamguard_api_key']));
    SpamGuard_Core::update_option('api_url', esc_url_raw($_POST['spamguard_api_url']));
    SpamGuard_Core::update_option('auto_delete', isset($_POST['spamguard_auto_delete']));
    SpamGuard_Core::update_option('sensitivity', floatval($_POST['spamguard_sensitivity']));
    SpamGuard_Core::update_option('learning_enabled', isset($_POST['spamguard_learning_enabled']));
    SpamGuard_Core::update_option('skip_registered_users', isset($_POST['spamguard_skip_registered_users']));
    SpamGuard_Core::update_option('min_comment_time', intval($_POST['spamguard_min_comment_time']));
    
    // Procesar listas
    $blacklist_ips = array_filter(array_map('trim', explode("\n", $_POST['spamguard_blacklist_ips'])));
    $blacklist_emails = array_filter(array_map('trim', explode("\n", $_POST['spamguard_blacklist_emails'])));
    $whitelist_ips = array_filter(array_map('trim', explode("\n", $_POST['spamguard_whitelist_ips'])));
    $whitelist_emails = array_filter(array_map('trim', explode("\n", $_POST['spamguard_whitelist_emails'])));
    
    SpamGuard_Core::update_option('blacklist_ips', $blacklist_ips);
    SpamGuard_Core::update_option('blacklist_emails', $blacklist_emails);
    SpamGuard_Core::update_option('whitelist_ips', $whitelist_ips);
    SpamGuard_Core::update_option('whitelist_emails', $whitelist_emails);
    
    echo '<div class="notice notice-success"><p>Configuracion guardada correctamente.</p></div>';
}

$api_key = SpamGuard_Core::get_option('api_key', '');
$api_url = SpamGuard_Core::get_option('api_url', 'https://spamguard.up.railway.app');
$auto_delete = SpamGuard_Core::get_option('auto_delete', false);
$sensitivity = SpamGuard_Core::get_option('sensitivity', 0.5);
$learning_enabled = SpamGuard_Core::get_option('learning_enabled', true);
$skip_registered_users = SpamGuard_Core::get_option('skip_registered_users', false);
$min_comment_time = SpamGuard_Core::get_option('min_comment_time', 3);
?>

<div class="wrap spamguard-settings">
    <h1>Configuracion de SpamGuard AI</h1>
    
    <form method="post" action="">
        <?php wp_nonce_field('spamguard_settings'); ?>
        
        <!-- API -->
        <div class="spamguard-card">
            <h2>Conexion API</h2>
            
            <table class="form-table">
                <tr>
                    <th scope="row">
                        <label for="spamguard_api_url">URL de la API</label>
                    </th>
                    <td>
                        <input type="url" 
                               id="spamguard_api_url" 
                               name="spamguard_api_url" 
                               value="<?php echo esc_attr($api_url); ?>" 
                               class="regular-text">
                        <p class="description">URL del servicio SpamGuard AI.</p>
                    </td>
                </tr>
                
                <tr>
                    <th scope="row">
                        <label for="spamguard_api_key">API Key</label>
                    </th>
                    <td>
                        <?php if (empty($api_key)): ?>
                            <button type="button" id="spamguard-register-btn" class="button button-primary">
                                Registrar Sitio Automaticamente
                            </button>
                            <p class="description">Genera una API key gratis con un click.</p>
                        <?php else: ?>
                            <input type="text" 
                                   id="spamguard_api_key" 
                                   name="spamguard_api_key" 
                                   value="<?php echo esc_attr($api_key); ?>" 
                                   class="regular-text code"
                                   readonly>
                            <p class="description">
                                Sitio registrado correctamente
                                <button type="button" id="spamguard-test-connection" class="button button-small">
                                    Probar Conexion
                                </button>
                            </p>
                        <?php endif; ?>
                    </td>
                </tr>
            </table>
        </div>
        
        <!-- Comportamiento -->
        <div class="spamguard-card">
            <h2>Comportamiento</h2>
            
            <table class="form-table">
                <tr>
                    <th scope="row">Sensibilidad</th>
                    <td>
                        <input type="range" 
                               id="spamguard_sensitivity" 
                               name="spamguard_sensitivity" 
                               min="0.1" 
                               max="0.9" 
                               step="0.1" 
                               value="<?php echo esc_attr($sensitivity); ?>">
                        <span id="sensitivity-value"><?php echo round($sensitivity * 100); ?>%</span>
                        <p class="description">Confianza minima para bloquear spam. Menor = mas estricto.</p>
                    </td>
                </tr>
                
                <tr>
                    <th scope="row">Accion con spam</th>
                    <td>
                        <label>
                            <input type="checkbox" 
                                   name="spamguard_auto_delete" 
                                   <?php checked($auto_delete); ?>>
                            Eliminar automaticamente
                        </label>
                    </td>
                </tr>
                
                <tr>
                    <th scope="row">Usuarios registrados</th>
                    <td>
                        <label>
                            <input type="checkbox" 
                                   name="spamguard_skip_registered_users" 
                                   <?php checked($skip_registered_users); ?>>
                            No verificar comentarios de usuarios registrados
                        </label>
                    </td>
                </tr>
            </table>
        </div>
        
        <!-- Aprendizaje -->
        <div class="spamguard-card">
            <h2>Aprendizaje Automatico</h2>
            
            <table class="form-table">
                <tr>
                    <th scope="row">Aprendizaje</th>
                    <td>
                        <label>
                            <input type="checkbox" 
                                   name="spamguard_learning_enabled" 
                                   <?php checked($learning_enabled); ?>>
                            Permitir que el sistema aprenda de mis correcciones
                        </label>
                        <p class="description">El modelo mejora cuando corriges errores.</p>
                    </td>
                </tr>
            </table>
        </div>
        
        <!-- Proteccion Adicional -->
        <div class="spamguard-card">
            <h2>Proteccion Adicional</h2>
            
            <table class="form-table">
                <tr>
                    <th scope="row">
                        <label for="spamguard_min_comment_time">Tiempo minimo (segundos)</label>
                    </th>
                    <td>
                        <input type="number" 
                               id="spamguard_min_comment_time" 
                               name="spamguard_min_comment_time" 
                               value="<?php echo esc_attr($min_comment_time); ?>" 
                               min="0" 
                               max="60"
                               class="small-text">
                        <p class="description">Rechazar comentarios mas rapidos que este tiempo. 0 = desactivado.</p>
                    </td>
                </tr>
                
                <tr>
                    <th scope="row">
                        <label for="spamguard_blacklist_ips">IPs Bloqueadas</label>
                    </th>
                    <td>
                        <textarea id="spamguard_blacklist_ips" 
                                  name="spamguard_blacklist_ips" 
                                  rows="5" 
                                  class="large-text code"
                                  placeholder="192.168.1.100&#10;10.0.0.50"><?php 
                            $blacklist_ips = SpamGuard_Core::get_option('blacklist_ips', array());
                            echo esc_textarea(is_array($blacklist_ips) ? implode("\n", $blacklist_ips) : '');
                        ?></textarea>
                        <p class="description">Una IP por linea.</p>
                    </td>
                </tr>
                
                <tr>
                    <th scope="row">
                        <label for="spamguard_blacklist_emails">Emails Bloqueados</label>
                    </th>
                    <td>
                        <textarea id="spamguard_blacklist_emails" 
                                  name="spamguard_blacklist_emails" 
                                  rows="5" 
                                  class="large-text code"><?php 
                            $blacklist_emails = SpamGuard_Core::get_option('blacklist_emails', array());
                            echo esc_textarea(is_array($blacklist_emails) ? implode("\n", $blacklist_emails) : '');
                        ?></textarea>
                        <p class="description">Un email por linea.</p>
                    </td>
                </tr>
                
                <tr>
                    <th scope="row">
                        <label for="spamguard_whitelist_ips">IPs Confiables</label>
                    </th>
                    <td>
                        <textarea id="spamguard_whitelist_ips" 
                                  name="spamguard_whitelist_ips" 
                                  rows="5" 
                                  class="large-text code"><?php 
                            $whitelist_ips = SpamGuard_Core::get_option('whitelist_ips', array());
                            echo esc_textarea(is_array($whitelist_ips) ? implode("\n", $whitelist_ips) : '');
                        ?></textarea>
                        <p class="description">Una IP por linea.</p>
                    </td>
                </tr>
                
                <tr>
                    <th scope="row">
                        <label for="spamguard_whitelist_emails">Emails Confiables</label>
                    </th>
                    <td>
                        <textarea id="spamguard_whitelist_emails" 
                                  name="spamguard_whitelist_emails" 
                                  rows="5" 
                                  class="large-text code"><?php 
                            $whitelist_emails = SpamGuard_Core::get_option('whitelist_emails', array());
                            echo esc_textarea(is_array($whitelist_emails) ? implode("\n", $whitelist_emails) : '');
                        ?></textarea>
                        <p class="description">Un email por linea.</p>
                    </td>
                </tr>
            </table>
        </div>
        
        <p class="submit">
            <button type="submit" name="spamguard_save_settings" class="button button-primary button-large">
                Guardar Configuracion
            </button>
        </p>
    </form>
</div>

<script>
jQuery(document).ready(function($) {
    $('#spamguard_sensitivity').on('input', function() {
        $('#sensitivity-value').text(Math.round($(this).val() * 100) + '%');
    });
    
    $('#spamguard-register-btn').on('click', function() {
        var btn = $(this);
        btn.prop('disabled', true).text('Registrando...');
        
        $.ajax({
            url: spamguardAdmin.ajaxUrl,
            type: 'POST',
            data: {
                action: 'spamguard_register',
                nonce: spamguardAdmin.nonce
            },
            success: function(response) {
                if (response.success) {
                    location.reload();
                } else {
                    alert('Error: ' + response.data);
                    btn.prop('disabled', false).text('Reintentar');
                }
            },
            error: function() {
                alert('Error de conexion');
                btn.prop('disabled', false).text('Reintentar');
            }
        });
    });
    
    $('#spamguard-test-connection').on('click', function() {
        var btn = $(this);
        btn.prop('disabled', true).text('Probando...');
        
        $.ajax({
            url: spamguardAdmin.ajaxUrl,
            type: 'POST',
            data: {
                action: 'spamguard_test_connection',
                nonce: spamguardAdmin.nonce
            },
            success: function(response) {
                if (response.success) {
                    alert('Conexion exitosa');
                } else {
                    alert('Error: ' + response.data);
                }
                btn.prop('disabled', false).text('Probar Conexion');
            },
            error: function() {
                alert('Error de conexion');
                btn.prop('disabled', false).text('Probar Conexion');
            }
        });
    });
});
</script>
