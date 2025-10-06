<?php
if (!defined('ABSPATH')) exit;

// Guardar configuración
if (isset($_POST['spamguard_save_settings']) && check_admin_referer('spamguard_settings')) {
    update_option('spamguard_api_key', sanitize_text_field($_POST['spamguard_api_key']));
    update_option('spamguard_api_url', esc_url_raw($_POST['spamguard_api_url']));
    update_option('spamguard_auto_delete', isset($_POST['spamguard_auto_delete']));
    update_option('spamguard_sensitivity', floatval($_POST['spamguard_sensitivity']));
    update_option('spamguard_learning_enabled', isset($_POST['spamguard_learning_enabled']));
    update_option('spamguard_skip_registered_users', isset($_POST['spamguard_skip_registered_users']));
    
    echo '<div class="notice notice-success"><p>' . __('Configuración guardada correctamente.', 'spamguard') . '</p></div>';
}

$api_key = get_option('spamguard_api_key', '');
$api_url = get_option('spamguard_api_url', SPAMGUARD_API_URL);
$auto_delete = get_option('spamguard_auto_delete', false);
$sensitivity = get_option('spamguard_sensitivity', 0.5);
$learning_enabled = get_option('spamguard_learning_enabled', true);
$skip_registered = get_option('spamguard_skip_registered_users', false);
?>

<div class="wrap spamguard-admin">
    <h1>
        <span class="dashicons dashicons-admin-settings"></span>
        <?php _e('SpamGuard AI - Configuración', 'spamguard'); ?>
    </h1>
    
    <div class="spamguard-settings-container">
        <div class="spamguard-settings-main">
            <form method="post" action="">
                <?php wp_nonce_field('spamguard_settings'); ?>
                
                <!-- Configuración de API -->
                <div class="spamguard-card">
                    <h2><?php _e('Configuración de la API', 'spamguard'); ?></h2>
                    
                    <?php if (empty($api_key)): ?>
                    <div class="spamguard-setup-wizard">
                        <h3><?php _e('🚀 ¡Bienvenido a SpamGuard AI!', 'spamguard'); ?></h3>
                        <p><?php _e('Para comenzar, necesitas obtener una API Key. Es gratis y toma solo 30 segundos.', 'spamguard'); ?></p>
                        
                        <button type="button" id="auto-register-btn" class="button button-primary button-hero">
                            <?php _e('Generar API Key Automáticamente', 'spamguard'); ?>
                        </button>
                        
                        <p class="description">
                            <?php _e('O introduce tu API Key manualmente si ya tienes una:', 'spamguard'); ?>
                        </p>
                    </div>
                    <?php endif; ?>
                    
                    <table class="form-table">
                        <tr>
                            <th scope="row">
                                <label for="spamguard_api_key"><?php _e('API Key', 'spamguard'); ?></label>
                            </th>
                            <td>
                                <input type="text" 
                                       id="spamguard_api_key" 
                                       name="spamguard_api_key" 
                                       value="<?php echo esc_attr($api_key); ?>" 
                                       class="regular-text"
                                       placeholder="sg_...">
                                <p class="description">
                                    <?php _e('Tu clave de API única para conectar con SpamGuard AI.', 'spamguard'); ?>
                                </p>
                            </td>
                        </tr>
                        
                        <tr>
                            <th scope="row">
                                <label for="spamguard_api_url"><?php _e('URL de la API', 'spamguard'); ?></label>
                            </th>
                            <td>
                                <input type="text" 
                                       id="spamguard_api_url" 
                                       name="spamguard_api_url" 
                                       value="<?php echo esc_attr($api_url); ?>" 
                                       class="regular-text"
                                       readonly
                                       style="background-color: #f0f0f1; cursor: not-allowed;">
                                <p class="description">
                                    <?php _e('URL del servidor de SpamGuard AI (solo lectura).', 'spamguard'); ?>
                                </p>
                            </td>
                        </tr>
                        
                        <tr>
                            <th scope="row"><?php _e('Estado de la conexión', 'spamguard'); ?></th>
                            <td>
                                <button type="button" id="test-connection-btn" class="button">
                                    <?php _e('Probar Conexión', 'spamguard'); ?>
                                </button>
                                <span id="connection-status"></span>
                            </td>
                        </tr>
                    </table>
                </div>
                
                <!-- Configuración de Filtrado -->
                <div class="spamguard-card">
                    <h2><?php _e('Configuración de Filtrado', 'spamguard'); ?></h2>
                    
                    <table class="form-table">
                        <tr>
                            <th scope="row">
                                <label for="spamguard_sensitivity"><?php _e('Sensibilidad', 'spamguard'); ?></label>
                            </th>
                            <td>
                                <input type="range" 
                                       id="spamguard_sensitivity" 
                                       name="spamguard_sensitivity" 
                                       min="0" 
                                       max="1" 
                                       step="0.1" 
                                       value="<?php echo esc_attr($sensitivity); ?>">
                                <span id="sensitivity-value"><?php echo round($sensitivity * 100); ?>%</span>
                                <p class="description">
                                    <?php _e('Umbral de confianza para marcar como spam. Más alto = más estricto.', 'spamguard'); ?>
                                </p>
                            </td>
                        </tr>
                        
                        <tr>
                            <th scope="row">
                                <label for="spamguard_auto_delete"><?php _e('Eliminar spam automáticamente', 'spamguard'); ?></label>
                            </th>
                            <td>
                                <label>
                                    <input type="checkbox" 
                                           id="spamguard_auto_delete" 
                                           name="spamguard_auto_delete" 
                                           <?php checked($auto_delete); ?>>
                                    <?php _e('Mover automáticamente a spam en lugar de moderación', 'spamguard'); ?>
                                </label>
                                <p class="description">
                                    <?php _e('Si está desactivado, los comentarios spam irán a la cola de moderación.', 'spamguard'); ?>
                                </p>
                            </td>
                        </tr>
                        
                        <tr>
                            <th scope="row">
                                <label for="spamguard_skip_registered_users"><?php _e('Usuarios registrados', 'spamguard'); ?></label>
                            </th>
                            <td>
                                <label>
                                    <input type="checkbox" 
                                           id="spamguard_skip_registered_users" 
                                           name="spamguard_skip_registered_users" 
                                           <?php checked($skip_registered); ?>>
                                    <?php _e('No analizar comentarios de usuarios registrados', 'spamguard'); ?>
                                </label>
                            </td>
                        </tr>
                    </table>
                </div>
                
                <!-- Aprendizaje -->
                <div class="spamguard-card">
                    <h2><?php _e('Aprendizaje Automático', 'spamguard'); ?></h2>
                    
                    <table class="form-table">
                        <tr>
                            <th scope="row">
                                <label for="spamguard_learning_enabled"><?php _e('Aprendizaje activo', 'spamguard'); ?></label>
                            </th>
                            <td>
                                <label>
                                    <input type="checkbox" 
                                           id="spamguard_learning_enabled" 
                                           name="spamguard_learning_enabled" 
                                           <?php checked($learning_enabled); ?>>
                                    <?php _e('Aprender de mis correcciones (recomendado)', 'spamguard'); ?>
                                </label>
                                <p class="description">
                                    <?php _e('Cuando marcas/desmarcas spam manualmente, el sistema aprende y mejora.', 'spamguard'); ?>
                                </p>
                            </td>
                        </tr>
                    </table>
                </div>
                
                <p class="submit">
                    <button type="submit" name="spamguard_save_settings" class="button button-primary button-large">
                        <?php _e('Guardar Cambios', 'spamguard'); ?>
                    </button>
                </p>
            </form>
        </div>
        
        <!-- Sidebar con ayuda -->
        <div class="spamguard-settings-sidebar">
            <div class="spamguard-card">
                <h3><?php _e('💡 Consejos', 'spamguard'); ?></h3>
                <ul>
                    <li><?php _e('Deja el aprendizaje activo habilitado para mejores resultados.', 'spamguard'); ?></li>
                    <li><?php _e('Revisa ocasionalmente la carpeta de spam por falsos positivos.', 'spamguard'); ?></li>
                    <li><?php _e('Cuanto más uses el plugin, más inteligente se vuelve.', 'spamguard'); ?></li>
                </ul>
            </div>
            
            <div class="spamguard-card">
                <h3><?php _e('📚 Recursos', 'spamguard'); ?></h3>
                <ul>
                    <li><a href="https://docs.spamguard.ai" target="_blank"><?php _e('Documentación', 'spamguard'); ?></a></li>
                    <li><a href="https://support.spamguard.ai" target="_blank"><?php _e('Soporte', 'spamguard'); ?></a></li>
                    <li><a href="https://github.com/spamguard/issues" target="_blank"><?php _e('Reportar Bug', 'spamguard'); ?></a></li>
                </ul>
            </div>
        </div>
    </div>
</div>

<script>
jQuery(document).ready(function($) {
    // Actualizar valor de sensibilidad
    $('#spamguard_sensitivity').on('input', function() {
        $('#sensitivity-value').text(Math.round($(this).val() * 100) + '%');
    });
    
    // Probar conexión
    $('#test-connection-btn').on('click', function() {
        const btn = $(this);
        btn.prop('disabled', true).text('<?php _e('Probando...', 'spamguard'); ?>');
        
        $.post(ajaxurl, {
            action: 'spamguard_test_connection',
            nonce: spamguardData.nonce
        }, function(response) {
            btn.prop('disabled', false).text('<?php _e('Probar Conexión', 'spamguard'); ?>');
            
            if (response.success) {
                $('#connection-status').html('<span class="status-badge success">' + response.data.message + '</span>');
            } else {
                $('#connection-status').html('<span class="status-badge error">' + response.data.message + '</span>');
            }
            
            setTimeout(function() {
                $('#connection-status').fadeOut();
            }, 3000);
        });
    });
    
    // Registro automático
    $('#auto-register-btn').on('click', function() {
        if (!confirm('<?php _e('Esto registrará tu sitio y generará una API Key. ¿Continuar?', 'spamguard'); ?>')) {
            return;
        }
        
        const btn = $(this);
        btn.prop('disabled', true).html('<span class="spinner is-active" style="float:none;margin:0 5px 0 0;"></span><?php _e('Registrando...', 'spamguard'); ?>');
        
        $.post(ajaxurl, {
            action: 'spamguard_register_site',
            nonce: spamguardData.nonce
        }, function(response) {
            btn.prop('disabled', false).text('<?php _e('Generar API Key Automáticamente', 'spamguard'); ?>');
            
            if (response.success) {
                $('#spamguard_api_key').val(response.data.api_key);
                alert('✅ ' + response.data.message + '\n\n<?php _e('API Key:', 'spamguard'); ?> ' + response.data.api_key);
                location.reload();
            } else {
                alert('❌ ' + response.data.message);
            }
        });
    });
});
</script>
