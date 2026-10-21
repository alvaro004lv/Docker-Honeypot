<?php
/**
 * Subida de adjuntos al helpdesk
 * Permite a los técnicos adjuntar ficheros a los tickets
 * Nota didáctica: esta página es intencionadamente vulnerable a subida sin restricciones de tipo de fichero
 */

include ('../inc/includes.php');
Session::checkLoginUser();

$upload_dir = GLPI_DOC_DIR . '/uploads/';
$message    = '';
$uploaded   = [];

// Crear el directorio de subida si no existe
if (!is_dir($upload_dir)) {
    @mkdir($upload_dir, 0777, true);
}

if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_FILES['attachment'])) {
    $files = $_FILES['attachment'];

    // Normalizar a array para admitir subidas múltiples
    if (!is_array($files['name'])) {
        foreach ($files as $k => $v) {
            $files[$k] = [$v];
        }
    }

    foreach (array_keys($files['name']) as $i) {
        if ($files['error'][$i] !== UPLOAD_ERR_OK) {
            continue;
        }
        $orig = basename($files['name'][$i]);
        // Vulnerable: sin comprobación de extensión ni validación de tipo MIME
        $dest = $upload_dir . $orig;
        if (move_uploaded_file($files['tmp_name'][$i], $dest)) {
            // Dar acceso web al fichero en /files/uploads/<nombre>
            @chmod($dest, 0644);
            $uploaded[] = $orig;
        }
    }

    if ($uploaded) {
        $message = 'Uploaded: ' . implode(', ', $uploaded);
    }
}

Html::header('Upload Attachment', $_SERVER['PHP_SELF']);
?>
<div class="center">
  <h2><?php echo __('Upload Attachment'); ?></h2>
  <p><?php echo __('Attach files to a helpdesk ticket or incident report.'); ?></p>

<?php if ($message): ?>
  <div class="green"><strong><?php echo htmlspecialchars($message); ?></strong></div>
<?php if ($uploaded): ?>
  <ul>
  <?php foreach ($uploaded as $fn): ?>
    <li>
      <a href="<?php echo GLPI_ROOT . '/files/uploads/' . rawurlencode($fn); ?>"
         target="_blank"><?php echo htmlspecialchars($fn); ?></a>
    </li>
  <?php endforeach; ?>
  </ul>
<?php endif; ?>
<?php endif; ?>

  <form method="POST" action="" enctype="multipart/form-data">
    <table class="tab_cadre_fixe">
      <tr>
        <th colspan="2"><?php echo __('Select file(s) to upload'); ?></th>
      </tr>
      <tr class="tab_bg_1">
        <td><?php echo __('File'); ?></td>
        <td>
          <input type="file" name="attachment[]" multiple />
        </td>
      </tr>
      <tr class="tab_bg_1">
        <td colspan="2" class="center">
          <input type="submit" class="submit" value="<?php echo __('Upload'); ?>" />
        </td>
      </tr>
    </table>
  </form>

<?php
// Listar los ficheros ya subidos
if (is_dir($upload_dir)) {
    $files = array_diff(scandir($upload_dir), ['.', '..']);
    if ($files):
?>
  <br/>
  <h3><?php echo __('Previously uploaded files'); ?></h3>
  <table class="tab_cadre_fixe">
    <tr><th><?php echo __('Filename'); ?></th><th><?php echo __('Size'); ?></th></tr>
<?php foreach ($files as $fn): ?>
    <tr class="tab_bg_1">
      <td>
        <a href="<?php echo '/files/uploads/' . rawurlencode($fn); ?>"
           target="_blank"><?php echo htmlspecialchars($fn); ?></a>
      </td>
      <td><?php echo round(filesize($upload_dir . $fn) / 1024, 1); ?> KB</td>
    </tr>
<?php endforeach; ?>
  </table>
<?php endif; } ?>
</div>
<?php
Html::footer();
