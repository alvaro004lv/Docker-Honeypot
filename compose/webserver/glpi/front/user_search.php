<?php
/**
 * Directorio de usuarios
 * Herramienta interna de IT para buscar usuarios GLPI por nombre o login
 * Nota didáctica: esta página es intencionadamente vulnerable a inyección SQL
 */

include ('../inc/includes.php');
Session::checkLoginUser();

global $DB;

$results = [];
$error   = '';

// Leer el parámetro en crudo desde QUERY_STRING para que addslashes_deep
// de Toolbox::sanitize (aplicado en includes.php) no neutralice la inyección
parse_str($_SERVER['QUERY_STRING'] ?? '', $raw);
$search = isset($raw['search']) ? $raw['search'] : '';

if ($search === '' && isset($_GET['search'])) {
    $search = $_GET['search'];
}

    // Vulnerable: entrada del usuario inyectada directamente en la consulta SQL
    // SELECT de 4 columnas para que la inyección UNION encaje: ' UNION SELECT 1,user(),version(),@@datadir-- -
    // La query va en una sola línea a propósito: un comentario "-- " de MySQL
    // solo neutraliza el resto de ESA línea. Si la query tuviera saltos de
    // línea reales entre las cláusulas OR, el payload UNION documentado no
    // comentaría las cláusulas siguientes y la inyección fallaría con un
    // error de sintaxis en vez de devolver el resultado esperado.
    $sql = "SELECT name, realname, firstname, password FROM glpi_users WHERE name LIKE '%$search%' OR realname LIKE '%$search%' OR firstname LIKE '%$search%' ORDER BY name LIMIT 50";

    $result = $DB->query($sql);

    if ($result) {
        while ($row = $DB->fetch_assoc($result)) {
            $results[] = $row;
        }
    } else {
        $error = $DB->error();
    }


Html::header('User Directory Search', $_SERVER['PHP_SELF']);
?>
<div class="center">
  <h2><?php echo __('User Directory Search'); ?></h2>
  <form method="GET" action="">
    <table class="tab_cadre_fixe">
      <tr>
        <th colspan="2"><?php echo __('Search users'); ?></th>
      </tr>
      <tr class="tab_bg_1">
        <td><label for="search"><?php echo __('Name or login'); ?></label></td>
        <td>
          <input type="text" id="search" name="search"
                 value="<?php echo htmlspecialchars($search); ?>"
                 size="40" placeholder="e.g. john" />
          &nbsp;
          <input type="submit" class="submit" value="<?php echo __('Search'); ?>" />
        </td>
      </tr>
    </table>
  </form>

<?php if ($error): ?>
  <div class="red">
    <strong>DB Error:</strong> <?php echo htmlspecialchars($error); ?>
  </div>
<?php endif; ?>

<?php if ($search !== ''): ?>
  <br/>
  <table class="tab_cadre_fixe">
    <tr>
      <th><?php echo __('Login'); ?></th>
      <th><?php echo __('First name'); ?></th>
      <th><?php echo __('Last name'); ?></th>
      <th><?php echo __('Password hash'); ?></th>
    </tr>
    <?php if (empty($results)): ?>
    <tr class="tab_bg_1">
      <td colspan="4"><?php echo __('No results found.'); ?></td>
    </tr>
    <?php else: ?>
      <?php foreach ($results as $row): ?>
      <tr class="tab_bg_1">
        <td><?php echo htmlspecialchars($row['name']); ?></td>
        <td><?php echo htmlspecialchars($row['firstname']); ?></td>
        <td><?php echo htmlspecialchars($row['realname']); ?></td>
        <td><?php echo htmlspecialchars($row['password']); ?></td>
      </tr>
      <?php endforeach; ?>
    <?php endif; ?>
  </table>
<?php endif; ?>
</div>
<?php
Html::footer();
